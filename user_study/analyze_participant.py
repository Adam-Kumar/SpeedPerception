"""
Automated Analysis Pipeline: Predictive Modeling of Speed Misperception
========================================================================
Project: Predictive Modeling of Speed Misperception and Mitigation Utilizing Dynamic AR Peripheral Cues
Focus: Phase 1 — Problem Identification & Baseline Telemetry Collection

Capabilities:
1. Ingests participant telemetry CSVs ('participant_<ID>_data.csv').
2. Computes zone-by-zone perceptual and motor metrics:
   - Speed Gap (v_actual - v_target): Mean, Median, Std, MAE, RMSE
   - Under-speeding vs. Over-speeding percentage breakdown
   - Control input volatility: Throttle standard deviation & adjustment jerk
   - Brake application rates & Steering stability
3. Aggregates multi-participant cohorts with statistical hypothesis testing (One-way ANOVA / Kruskal-Wallis).
4. Generates publication-ready visualizations:
   - Box plot of Speed Gap by Environmental Zone
   - 20.0 km Longitudinal Speed Profile with shaded Perceptual Stress Zones
   - Control Dynamics & Throttle Oscillation comparison
   - Categorical Misperception Proportion stacked bars
5. Exports structured CSV metrics and an automated Markdown Research Report.
"""

import os
import sys
import glob
import math
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# Master color palette consistent with annotate_route.py
ZONE_COLORS = {
    'Pre-Test': '#6c757d',          # dimgray / muted gray
    'Urban Expressway': '#00d2d3',  # cyan / vibrant teal
    'Tunnel': '#0984e3',            # dodgerblue / deep blue
    'Rural Expressway': '#2ed573',  # limegreen / foliage green
    'Bridge': '#e056fd',            # magenta / purple
    'Urban Road': '#f1c40f',        # gold / amber
    'Unlabeled': '#ffffff'
}

ZONE_ORDER = [
    'Pre-Test',
    'Urban Expressway',
    'Tunnel',
    'Rural Expressway',
    'Bridge',
    'Urban Road'
]


# ==============================================================================
# 1. METRIC EXTRACTION & COMPUTATION
# ==============================================================================

def compute_zone_metrics(df: pd.DataFrame, participant_id: str = "Unknown") -> pd.DataFrame:
    """
    Computes perceptual speed metrics and driver control dynamics across
    each distinct environmental zone for a single participant run.
    """
    records = []

    # Ensure required columns
    required = ['speed_kmh', 'target_speed_kmh', 'speed_gap_kmh', 'environment_zone']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Telemetry missing required column: '{col}'")

    # Group by zone
    grouped = df.groupby('environment_zone')

    for zone, group in grouped:
        n_samples = len(group)
        if n_samples == 0:
            continue

        duration_sec = n_samples * 0.1  # 10Hz sampling
        speed = np.asarray(group['speed_kmh'], dtype=float)
        target = np.asarray(group['target_speed_kmh'], dtype=float)
        gap = np.asarray(group['speed_gap_kmh'], dtype=float)

        # Speed gap statistics
        mean_gap = float(np.mean(gap))
        median_gap = float(np.median(gap))
        std_gap = float(np.std(gap))
        min_gap = float(np.min(gap))
        max_gap = float(np.max(gap))
        mae = float(np.mean(np.abs(gap)))
        rmse = float(np.sqrt(np.mean(gap**2)))

        # Actual speed statistics
        mean_speed = float(np.mean(speed))
        std_speed = float(np.std(speed))
        mean_target = float(np.mean(target))

        # Direction of misperception (% time)
        # Tolerance window: +- 5 km/h
        pct_underspeed_5 = float(np.mean(gap < -5.0) * 100.0)
        pct_ontarget_5 = float(np.mean(np.abs(gap) <= 5.0) * 100.0)
        pct_overspeed_5 = float(np.mean(gap > 5.0) * 100.0)

        # Strict sign breakdown
        pct_underspeed_strict = float(np.mean(gap < 0.0) * 100.0)
        pct_overspeed_strict = float(np.mean(gap > 0.0) * 100.0)

        # Control dynamics (throttle & brake)
        throttle = np.asarray(group['throttle'], dtype=float) if 'throttle' in group.columns else np.zeros(n_samples)
        brake = np.asarray(group['brake'], dtype=float) if 'brake' in group.columns else np.zeros(n_samples)
        steering = np.asarray(group['steering'], dtype=float) if 'steering' in group.columns else np.zeros(n_samples)

        mean_throttle = float(np.mean(throttle))
        std_throttle = float(np.std(throttle))  # Throttle oscillation / hunting

        # Throttle jerk / rate of adjustment (reversals per second)
        if len(throttle) > 1:
            d_throttle = np.abs(np.diff(throttle)) / 0.1  # dt = 0.1s
            throttle_jerk = float(np.mean(d_throttle))
        else:
            throttle_jerk = 0.0

        mean_brake = float(np.mean(brake))
        pct_brake_active = float(np.mean(brake > 0.05) * 100.0)
        std_steering = float(np.std(steering))

        # Primary perceptual classification
        if mean_gap < -3.0:
            dominant_bias = "Under-Speeding"
        elif mean_gap > 3.0:
            dominant_bias = "Over-Speeding"
        else:
            dominant_bias = "Calibrated"

        records.append({
            'participant_id': participant_id,
            'zone': zone,
            'samples': n_samples,
            'duration_sec': round(duration_sec, 1),
            'actual_speed_mean': round(mean_speed, 2),
            'actual_speed_std': round(std_speed, 2),
            'target_speed_mean': round(mean_target, 2),
            'speed_gap_mean': round(mean_gap, 2),
            'speed_gap_median': round(median_gap, 2),
            'speed_gap_std': round(std_gap, 2),
            'speed_gap_min': round(min_gap, 2),
            'speed_gap_max': round(max_gap, 2),
            'mae_kmh': round(mae, 2),
            'rmse_kmh': round(rmse, 2),
            'pct_underspeed_5kmh': round(pct_underspeed_5, 1),
            'pct_ontarget_5kmh': round(pct_ontarget_5, 1),
            'pct_overspeed_5kmh': round(pct_overspeed_5, 1),
            'pct_underspeed_strict': round(pct_underspeed_strict, 1),
            'pct_overspeed_strict': round(pct_overspeed_strict, 1),
            'mean_throttle': round(mean_throttle, 3),
            'throttle_std_oscillation': round(std_throttle, 3),
            'throttle_jerk_per_sec': round(throttle_jerk, 3),
            'mean_brake': round(mean_brake, 3),
            'pct_brake_active': round(pct_brake_active, 1),
            'steering_std': round(std_steering, 3),
            'dominant_bias': dominant_bias
        })

    result_df = pd.DataFrame(records)

    # Sort according to standard course zone order if available
    result_df['zone_order'] = result_df['zone'].apply(
        lambda z: ZONE_ORDER.index(z) if z in ZONE_ORDER else 99
    )
    result_df = result_df.sort_values('zone_order').drop(columns=['zone_order']).reset_index(drop=True)
    return result_df


# ==============================================================================
# 2. STATISTICAL COHORT ANALYSIS
# ==============================================================================

def analyze_cohort_statistics(combined_df: pd.DataFrame) -> dict:
    """
    Performs one-way ANOVA and Kruskal-Wallis non-parametric tests across
    environmental zones to evaluate the statistical significance of speed misperception.
    """
    stats_report = {}
    zone_groups = [np.asarray(group['speed_gap_kmh'], dtype=float) for _, group in combined_df.groupby('environment_zone')]
    zone_names = list(combined_df['environment_zone'].unique())

    if len(zone_groups) > 1:
        # One-way ANOVA
        f_stat, p_val_anova = stats.f_oneway(*zone_groups)
        # Kruskal-Wallis
        kw_stat, p_val_kw = stats.kruskal(*zone_groups)

        stats_report['anova_f'] = float(f_stat)
        stats_report['anova_p'] = float(p_val_anova)
        stats_report['kruskal_stat'] = float(kw_stat)
        stats_report['kruskal_p'] = float(p_val_kw)
        stats_report['is_significant'] = bool(p_val_anova < 0.05)
    else:
        stats_report['is_significant'] = False

    return stats_report


# ==============================================================================
# 3. VISUALIZATION GENERATORS
# ==============================================================================

def plot_speed_gap_boxplot(
    combined_df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 1: Distribution of Speed Gap (v_actual - v_target) by Environmental Zone.
    Includes zero reference line, under/over-speeding background zones, and boxplots.
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

    # Filter to known zones in specified order
    ordered_zones = [z for z in ZONE_ORDER if z in combined_df['environment_zone'].unique()]
    data_by_zone = [np.asarray(combined_df[combined_df['environment_zone'] == z]['speed_gap_kmh'], dtype=float) for z in ordered_zones]

    # Background color bands for Under-speeding vs Over-speeding
    y_min = math.floor(combined_df['speed_gap_kmh'].min() / 5) * 5 - 5
    y_max = math.ceil(combined_df['speed_gap_kmh'].max() / 5) * 5 + 5
    y_min = max(y_min, -30)
    y_max = min(y_max, 35)

    ax.axhspan(0, y_max, color='#e74c3c', alpha=0.08, label='Over-Speeding Region (v_act > v_tgt)')
    ax.axhspan(y_min, 0, color='#3498db', alpha=0.08, label='Under-Speeding Region (v_act < v_tgt)')
    ax.axhline(0, color='#f1c40f', linestyle='--', linewidth=2, alpha=0.9, label='Target Speed (Gap = 0 km/h)')
    ax.axhline(5, color='#e74c3c', linestyle=':', linewidth=1, alpha=0.5)
    ax.axhline(-5, color='#3498db', linestyle=':', linewidth=1, alpha=0.5)

    # Create box plots
    bp = ax.boxplot(
        data_by_zone,
        positions=range(len(ordered_zones)),
        patch_artist=True,
        widths=0.5,
        notch=True,
        showmeans=True,
        meanprops=dict(marker='o', markerfacecolor='white', markeredgecolor='black', markersize=6),
        flierprops=dict(marker='.', markerfacecolor='gray', markersize=3, alpha=0.3)
    )

    # Custom box coloring based on ZONE_COLORS
    for patch, zone_name in zip(bp['boxes'], ordered_zones):
        color = ZONE_COLORS.get(zone_name, '#95a5a6')
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
        patch.set_edgecolor('white')

    for median in bp['medians']:
        median.set_color('white')
        median.set_linewidth(2)

    ax.set_xticks(range(len(ordered_zones)))
    ax.set_xticklabels(ordered_zones, fontsize=11, fontweight='bold')
    ax.set_ylabel("Speed Gap: $v_{\\mathrm{actual}} - v_{\\mathrm{target}}$ (km/h)", fontsize=12)
    ax.set_ylim(y_min, y_max)
    ax.set_title(f"Speed Misperception Gap Across Environmental Zones {title_suffix}", fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, linestyle='--', alpha=0.2, axis='y')
    ax.legend(loc='upper right', framealpha=0.8)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[Plot Saved] Box Plot -> {output_path}")


def plot_longitudinal_profile(
    df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 2: Longitudinal Course Speed Profile across 20.0 km.
    Features participant actual speed vs target speed, annotated with
    environmental zone background shading according to ZONE_COLORS.
    """
    plt.style.use('dark_background')
    fig, (ax_speed, ax_thr) = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]}, dpi=300)

    # Sort by Distance_km
    df_sorted = df.sort_values('Distance_km').reset_index(drop=True)
    dist = np.asarray(df_sorted['Distance_km'], dtype=float)
    speed = np.asarray(df_sorted['speed_kmh'], dtype=float)
    target = np.asarray(df_sorted['target_speed_kmh'], dtype=float)
    thr = np.asarray(df_sorted['throttle'], dtype=float) if 'throttle' in df_sorted.columns else np.zeros_like(speed)

    # Identify continuous contiguous zone segments for background shading
    zone_series = df_sorted['environment_zone']
    change_indices = np.where(zone_series != zone_series.shift())[0]
    segment_starts = list(change_indices) + [len(df_sorted)]

    legend_patches = {}
    for i in range(len(segment_starts) - 1):
        idx_start = segment_starts[i]
        idx_end = segment_starts[i+1] - 1
        d_start = dist[idx_start]
        d_end = dist[idx_end]
        zone_name = zone_series.iloc[idx_start]
        color = ZONE_COLORS.get(zone_name, '#555555')

        ax_speed.axvspan(d_start, d_end, color=color, alpha=0.18)
        ax_thr.axvspan(d_start, d_end, color=color, alpha=0.18)

        if zone_name not in legend_patches:
            legend_patches[zone_name] = mpatches.Patch(color=color, alpha=0.6, label=zone_name)

    # Speed trace
    ax_speed.plot(dist, speed, color='#00f2fe', linewidth=1.5, label='Actual Speed (km/h)', alpha=0.95)
    ax_speed.plot(dist, target, color='#ff4757', linestyle='--', linewidth=2, label='Target Speed (km/h)', alpha=0.9)

    ax_speed.set_ylabel("Speed (km/h)", fontsize=12, fontweight='bold')
    ax_speed.set_title(f"20.0 km Longitudinal Speed & Perception Profile {title_suffix}", fontsize=14, fontweight='bold', pad=12)
    ax_speed.grid(True, linestyle='--', alpha=0.25)
    ax_speed.set_ylim(20, 130)

    # Combine line handles with zone patches
    handles, labels = ax_speed.get_legend_handles_labels()
    handles += list(legend_patches.values())
    labels += list(legend_patches.keys())
    ax_speed.legend(handles=handles, labels=labels, loc='upper right', ncol=3, framealpha=0.85, fontsize=9)

    # Throttle trace
    ax_thr.plot(dist, thr * 100, color='#2ed573', linewidth=1.2, label='Throttle (%)')
    ax_thr.set_ylabel("Throttle (%)", fontsize=11, fontweight='bold')
    ax_thr.set_xlabel("Course Distance (km)", fontsize=12, fontweight='bold')
    ax_thr.set_ylim(0, 105)
    ax_thr.grid(True, linestyle='--', alpha=0.25)
    ax_thr.set_xlim(0, max(20.0, dist.max()))

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[Plot Saved] Longitudinal Profile -> {output_path}")


def plot_control_dynamics(
    summary_df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 3: Driver Control Volatility & Hunting behavior across zones.
    Compares Throttle Standard Deviation (hunting) and Speed Standard Deviation.
    """
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    zones = np.asarray(summary_df['zone'])
    colors = [ZONE_COLORS.get(z, '#95a5a6') for z in zones]
    x = np.arange(len(zones))

    # Throttle Volatility (Std Dev)
    bars1 = ax1.bar(x, summary_df['throttle_std_oscillation'], color=colors, alpha=0.8, edgecolor='white')
    ax1.set_xticks(x)
    ax1.set_xticklabels(zones, rotation=25, ha='right', fontsize=10)
    ax1.set_ylabel("Throttle Volatility (Std Dev)", fontsize=11)
    ax1.set_title("Throttle Hunting & Instability by Zone", fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.2, axis='y')
    ax1.set_ylim(0, max(summary_df['throttle_std_oscillation']) * 1.25)

    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.003, f"{yval:.2f}", ha='center', va='bottom', fontsize=9, color='white')

    # Speed Variability (Std Dev)
    bars2 = ax2.bar(x, summary_df['actual_speed_std'], color=colors, alpha=0.8, edgecolor='white')
    ax2.set_xticks(x)
    ax2.set_xticklabels(zones, rotation=25, ha='right', fontsize=10)
    ax2.set_ylabel("Speed Variability: $\\sigma_{v}$ (km/h)", fontsize=11)
    ax2.set_title("Speed Variance by Environmental Zone", fontsize=12, fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.2, axis='y')
    ax2.set_ylim(0, max(summary_df['actual_speed_std']) * 1.25)

    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.05, f"{yval:.1f}", ha='center', va='bottom', fontsize=9, color='white')

    fig.suptitle(f"Driver Control Dynamics & Perceptual Stress {title_suffix}", fontsize=14, fontweight='bold')
    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[Plot Saved] Control Dynamics -> {output_path}")


def plot_misperception_breakdown(
    summary_df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 4: 100% Stacked Bar Chart showing proportion of time spent
    Under-speeding (< -5 km/h), On-Target (+- 5 km/h), and Over-speeding (> +5 km/h).
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)

    zones = np.asarray(summary_df['zone'])
    under = np.asarray(summary_df['pct_underspeed_5kmh'], dtype=float)
    ontarget = np.asarray(summary_df['pct_ontarget_5kmh'], dtype=float)
    over = np.asarray(summary_df['pct_overspeed_5kmh'], dtype=float)
    x = np.arange(len(zones))

    # Stacked bars
    p1 = ax.bar(x, under, label='Under-Speeding (Gap < -5 km/h)', color='#3498db', alpha=0.85, width=0.55)
    p2 = ax.bar(x, ontarget, bottom=under, label='On-Target (±5 km/h Window)', color='#2ecc71', alpha=0.85, width=0.55)
    p3 = ax.bar(x, over, bottom=under + ontarget, label='Over-Speeding (Gap > +5 km/h)', color='#e74c3c', alpha=0.85, width=0.55)

    ax.set_xticks(x)
    ax.set_xticklabels(zones, rotation=20, ha='right', fontsize=11, fontweight='bold')
    ax.set_ylabel("% Time in Perceptual State", fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_title(f"Perceptual Misperception Proportions by Zone {title_suffix}", fontsize=14, fontweight='bold', pad=32)
    ax.grid(True, linestyle='--', alpha=0.2, axis='y')
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3, framealpha=0.9, fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[Plot Saved] Misperception Breakdown -> {output_path}")


# ==============================================================================
# 4. REPORT EXPORTER (MARKDOWN & CONSOLE)
# ==============================================================================

def print_summary_table(summary_df: pd.DataFrame):
    """Prints a structured ASCII summary table to terminal."""
    header = (
        f"{'Zone':<18} | {'Samples':<7} | {'Mean v':<7} | {'Tgt v':<6} | "
        f"{'Speed Gap':<12} | {'RMSE':<6} | {'% Under':<8} | {'% Over':<8} | {'Bias Classification':<18}"
    )
    divider = "-" * len(header)
    print("\n" + divider)
    print(header)
    print(divider)

    for _, row in summary_df.iterrows():
        gap_str = f"{row['speed_gap_mean']:+5.1f} +/- {row['speed_gap_std']:3.1f}"
        print(
            f"{row['zone']:<18} | {row['samples']:<7} | {row['actual_speed_mean']:<7.1f} | "
            f"{row['target_speed_mean']:<6.0f} | {gap_str:<12} | {row['rmse_kmh']:<6.1f} | "
            f"{row['pct_underspeed_5kmh']:<7.1f}% | {row['pct_overspeed_5kmh']:<7.1f}% | "
            f"{row['dominant_bias']:<18}"
        )
    print(divider + "\n")


def export_markdown_report(
    summary_df: pd.DataFrame,
    stats_dict: dict,
    output_path: str,
    cohort_mode: bool = False
):
    """Generates an executive research briefing in Markdown format."""
    md = []
    title = "Cohort Aggregation Report" if cohort_mode else f"Participant Report: {summary_df['participant_id'].iloc[0]}"
    md.append(f"# Speed Misperception Research Report: {title}\n")
    md.append(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    md.append(f"**Focus:** Phase 1 — Problem Identification & Baseline Telemetry Across Perceptual Stress Zones\n")

    md.append("## 1. Executive Summary & Zone Breakdown\n")
    md.append("| Zone | Duration (s) | Mean Speed (km/h) | Target (km/h) | Speed Gap (km/h) | RMSE | % Under (< -5) | % Over (> +5) | Dominant Perceptual Bias |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")

    for _, row in summary_df.iterrows():
        md.append(
            f"| **{row['zone']}** | {row['duration_sec']}s | {row['actual_speed_mean']:.1f} | "
            f"{row['target_speed_mean']:.0f} | **{row['speed_gap_mean']:+.2f} ± {row['speed_gap_std']:.2f}** | "
            f"{row['rmse_kmh']:.1f} | {row['pct_underspeed_5kmh']:.1f}% | {row['pct_overspeed_5kmh']:.1f}% | "
            f"`{row['dominant_bias']}` |"
        )

    md.append("\n## 2. Statistical Hypothesis Testing\n")
    if stats_dict.get('is_significant', False):
        md.append(f"- **One-way ANOVA:** $F = {stats_dict['anova_f']:.2f}$, $p = {stats_dict['anova_p']:.4e}$ (Statistically Significant, $p < 0.05$).")
        md.append(f"- **Kruskal-Wallis Test:** $H = {stats_dict['kruskal_stat']:.2f}$, $p = {stats_dict['kruskal_p']:.4e}$.")
        md.append("- **Inference:** Environmental geometry and peripheral optical flow significantly alter participant speed perception in the absence of a speedometer.")
    else:
        md.append("- Single run or insufficient cohort variance for inferential testing.")

    md.append("\n## 3. Key Behavioral Triggers & Perceptual Observations\n")
    for _, row in summary_df.iterrows():
        zone = row['zone']
        bias = row['dominant_bias']
        gap = row['speed_gap_mean']
        osc = row['throttle_std_oscillation']

        if 'Tunnel' in zone:
            md.append(f"- **Tunnel Environments ({gap:+.1f} km/h):** High spatial frequency and compressed peripheral optical flow induce an illusion of higher velocity. Drivers systematically under-speed to compensate, accompanied by elevated throttle hunting ($\sigma={osc:.2f}$).")
        elif 'Bridge' in zone:
            md.append(f"- **Bridge Sections ({gap:+.1f} km/h):** Open horizons and sparse roadside objects reduce peripheral optical flow cues. Drivers experience speed underestimation, triggering substantial over-speeding.")
        elif 'Rural' in zone:
            md.append(f"- **Rural Expressway ({gap:+.1f} km/h):** Reduced building density and open factory backdrops prompt moderate over-speeding due to subdued peripheral flow.")
        elif 'Urban Expressway' in zone:
            md.append(f"- **Urban Expressway ({gap:+.1f} km/h):** Balanced vertical barrier structures provide sufficient optical cues, resulting in closer target tracking.")

    md.append("\n## 4. Phase 2 Dynamic AR Peripheral Cue Recommendations\n")
    md.append("1. **Negative Gap Mitigation (Tunnels):** Project forward-flowing optical cues or subtle peripheral pulse dampeners to counteract artificial speed inflation.")
    md.append("2. **Positive Gap Mitigation (Bridges/Open Roads):** Project dynamic backward optical flow arrows inside VR headset periphery to induce subconscious deceleration toward the target speed ($v_{\\mathrm{target}}$).")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))

    print(f"[Report Exported] Research Report -> {output_path}")


# ==============================================================================
# 5. PIPELINE CONTROLLER
# ==============================================================================

def run_analysis_pipeline(
    input_files: list,
    output_dir: str = "analysis_outputs"
):
    """Runs end-to-end analysis across single or aggregated participant datasets."""
    if not input_files:
        print("\n[Notice] No participant data files provided or found.")
        print("To collect participant data, run:")
        print("  python user_study.py --participant-id P01\n")
        print("Once data is collected, analyze it with:")
        print("  python analyze_participant.py -d .\n")
        return

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[Pipeline] Ingesting {len(input_files)} participant file(s)...")
    for f in input_files:
        print(f"  - {f}")

    all_dfs = []
    zone_summaries = []

    for filepath in input_files:
        filename = os.path.basename(filepath)
        pid = filename.replace('participant_', '').replace('_data.csv', '')

        df = pd.read_csv(filepath)
        df['participant_id'] = pid
        all_dfs.append(df)

        # Single participant summary
        summary = compute_zone_metrics(df, participant_id=pid)
        zone_summaries.append(summary)

        # Individual participant CSV
        single_csv_out = os.path.join(output_dir, f"participant_{pid}_summary.csv")
        summary.to_csv(single_csv_out, index=False)

    # Combined dataset
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_summary = compute_zone_metrics(combined_df, participant_id="Cohort")

    # Export overall metrics CSV
    cohort_csv_out = os.path.join(output_dir, "cohort_zone_metrics_summary.csv")
    combined_summary.to_csv(cohort_csv_out, index=False)

    # Statistical hypothesis tests
    stats_dict = analyze_cohort_statistics(combined_df)

    # Print summary to terminal
    print("\n" + "="*80)
    print("  COHORT AGGREGATED METRICS SUMMARY")
    print("="*80)
    print_summary_table(combined_summary)

    # Generate Figures
    print("[Pipeline] Rendering publication-ready figures...")
    boxplot_file = os.path.join(output_dir, "speed_gap_by_zone_boxplot.png")
    profile_file = os.path.join(output_dir, "longitudinal_speed_profile.png")
    dynamics_file = os.path.join(output_dir, "control_dynamics_comparison.png")
    breakdown_file = os.path.join(output_dir, "misperception_proportions.png")

    plot_speed_gap_boxplot(combined_df, boxplot_file, title_suffix="(Cohort)")
    plot_longitudinal_profile(all_dfs[0], profile_file, title_suffix=f"({all_dfs[0]['participant_id'].iloc[0]})")
    plot_control_dynamics(combined_summary, dynamics_file, title_suffix="(Cohort)")
    plot_misperception_breakdown(combined_summary, breakdown_file, title_suffix="(Cohort)")

    # Export Markdown Report
    report_file = os.path.join(output_dir, "speed_misperception_report.md")
    export_markdown_report(combined_summary, stats_dict, report_file, cohort_mode=len(input_files) > 1)

    print("\n" + "="*80)
    print(f"  ANALYSIS PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"  All outputs saved to: '{os.path.abspath(output_dir)}'")
    print("="*80 + "\n")


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Automated Analysis Pipeline: Predictive Modeling of Speed Misperception",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        default=None,
        help="Path to a single participant CSV file to analyze"
    )
    parser.add_argument(
        '-d', '--dir',
        type=str,
        default=None,
        help="Directory to search for 'participant_*_data.csv' files (default: user_study folder)"
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default=None,
        help="Directory to store summary tables, plots, and markdown reports (default: user_study/analysis_outputs)"
    )

    args = parser.parse_args()

    # Resolve search and output directories
    search_dir = args.dir if args.dir else script_dir
    out_dir = args.output_dir if args.output_dir else os.path.join(script_dir, 'analysis_outputs')

    # Collect files
    if args.file:
        if not os.path.exists(args.file):
            print(f"[Error] File not found: {args.file}")
            sys.exit(1)
        files = [args.file]
    else:
        files = glob.glob(os.path.join(search_dir, "participant_*_data.csv"))
        if not files and args.dir is None and search_dir != os.getcwd():
            files = glob.glob(os.path.join(os.getcwd(), "participant_*_data.csv"))
        # Exclude summary files if any
        files = [f for f in files if not f.endswith('_summary.csv')]

    run_analysis_pipeline(
        input_files=files,
        output_dir=out_dir
    )


if __name__ == '__main__':
    main()
