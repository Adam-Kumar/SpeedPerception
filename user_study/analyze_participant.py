"""
Automated Analysis Pipeline: Predictive Modeling of Speed Misperception
========================================================================
Project: Predictive Modeling of Speed Misperception and Mitigation Utilizing Dynamic AR Peripheral Cues
Focus: Phase 1 — Problem Identification & Baseline Telemetry Collection

Focused Visualization Suite:
1. Longitudinal Speed Profile (scaled to top recorded speed with zone shading)
2. Longitudinal Throttle Profile (driver throttle % across 20.0 km with zone shading)
3. Speed Misperception Gap Box Plot by Environmental Zone
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

# Master color palette consistent with route annotation
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
    """Computes speed gap metrics across environmental zones for console summary."""
    records = []
    required = ['speed_kmh', 'target_speed_kmh', 'speed_gap_kmh', 'environment_zone']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Telemetry missing required column: '{col}'")

    grouped = df.groupby('environment_zone')

    for zone, group in grouped:
        n_samples = len(group)
        if n_samples == 0:
            continue

        speed = np.asarray(group['speed_kmh'], dtype=float)
        target = np.asarray(group['target_speed_kmh'], dtype=float)
        gap = np.asarray(group['speed_gap_kmh'], dtype=float)

        mean_gap = float(np.mean(gap))
        std_gap = float(np.std(gap))
        rmse = float(np.sqrt(np.mean(gap**2)))

        mean_speed = float(np.mean(speed))
        mean_target = float(np.mean(target))

        under_pct = float(np.mean(gap < -5.0) * 100.0)
        over_pct = float(np.mean(gap > 5.0) * 100.0)
        ontarget_pct = float(np.mean(np.abs(gap) <= 5.0) * 100.0)

        if mean_gap < -5.0:
            bias = "Under-Speeding"
        elif mean_gap > 5.0:
            bias = "Over-Speeding"
        else:
            bias = "Calibrated (On-Target)"

        records.append({
            'participant_id': participant_id,
            'zone': zone,
            'samples': n_samples,
            'actual_speed_mean': mean_speed,
            'target_speed_mean': mean_target,
            'speed_gap_mean': mean_gap,
            'speed_gap_std': std_gap,
            'rmse_kmh': rmse,
            'pct_underspeed_5kmh': under_pct,
            'pct_ontarget_5kmh': ontarget_pct,
            'pct_overspeed_5kmh': over_pct,
            'dominant_bias': bias
        })

    summary_df = pd.DataFrame(records)
    if not summary_df.empty:
        summary_df['zone_order'] = summary_df['zone'].apply(lambda z: ZONE_ORDER.index(z) if z in ZONE_ORDER else 99)
        summary_df = summary_df.sort_values('zone_order').drop(columns=['zone_order']).reset_index(drop=True)

    return summary_df


def print_summary_table(summary_df: pd.DataFrame):
    """Prints a structured ASCII summary table to terminal."""
    header = (
        f"{'Zone':<18} | {'Samples':<7} | {'Mean v':<7} | {'Tgt v':<6} | "
        f"{'Speed Gap':<15} | {'RMSE':<6} | {'% Under':<8} | {'% Over':<8} | {'Bias Classification':<18}"
    )
    divider = "-" * len(header)
    print("\n" + divider)
    print(header)
    print(divider)

    for _, row in summary_df.iterrows():
        gap_str = f"{row['speed_gap_mean']:+5.1f} +/- {row['speed_gap_std']:3.1f}"
        print(
            f"{row['zone']:<18} | {row['samples']:<7} | {row['actual_speed_mean']:<7.1f} | "
            f"{row['target_speed_mean']:<6.0f} | {gap_str:<15} | {row['rmse_kmh']:<6.1f} | "
            f"{row['pct_underspeed_5kmh']:<7.1f}% | {row['pct_overspeed_5kmh']:<7.1f}% | "
            f"{row['dominant_bias']:<18}"
        )
    print(divider + "\n")


# ==============================================================================
# 2. FOCUSED VISUALIZATION SUITE
# ==============================================================================

def plot_speed_gap_boxplot(
    combined_df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 1: Distribution of Speed Gap (v_actual - v_target) by Environmental Zone.
    Y-axis dynamically adapts to fit all recorded data without clipping.
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

    ordered_zones = [z for z in ZONE_ORDER if z in combined_df['environment_zone'].unique()]
    data_by_zone = [np.asarray(combined_df[combined_df['environment_zone'] == z]['speed_gap_kmh'], dtype=float) for z in ordered_zones]

    # Dynamic Y limits to fit all recorded data comfortably
    raw_min = float(combined_df['speed_gap_kmh'].min())
    raw_max = float(combined_df['speed_gap_kmh'].max())
    y_min = math.floor(min(-10.0, raw_min) / 10.0) * 10.0 - 5.0
    y_max = math.ceil(max(10.0, raw_max) / 10.0) * 10.0 + 5.0

    ax.axhspan(0, y_max, color='#e74c3c', alpha=0.08, label='Over-Speeding Region (v_act > v_tgt)')
    ax.axhspan(y_min, 0, color='#3498db', alpha=0.08, label='Under-Speeding Region (v_act < v_tgt)')
    ax.axhline(0, color='#f1c40f', linestyle='--', linewidth=2, alpha=0.9, label='Target Speed (Gap = 0 km/h)')
    ax.axhline(5, color='#e74c3c', linestyle=':', linewidth=1, alpha=0.5)
    ax.axhline(-5, color='#3498db', linestyle=':', linewidth=1, alpha=0.5)

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
    print(f"[Plot Saved] Speed Gap Box Plot -> {output_path}")


def plot_longitudinal_speed_profile(
    df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 2: Longitudinal Course Speed Profile across 20.0 km.
    Y-axis dynamically scales up to the top speed recorded.
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 6.5), dpi=300)

    df_sorted = df.sort_values('Distance_km').reset_index(drop=True)
    dist = np.asarray(df_sorted['Distance_km'], dtype=float)
    speed = np.asarray(df_sorted['speed_kmh'], dtype=float)
    target = np.asarray(df_sorted['target_speed_kmh'], dtype=float)

    # Zone background shading
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

        ax.axvspan(d_start, d_end, color=color, alpha=0.18)
        if zone_name not in legend_patches:
            legend_patches[zone_name] = mpatches.Patch(color=color, alpha=0.6, label=zone_name)

    # Actual and Target Speed traces
    ax.plot(dist, speed, color='#00f2fe', linewidth=1.5, label='Actual Speed (km/h)', alpha=0.95)
    ax.plot(dist, target, color='#ff4757', linestyle='--', linewidth=2, label='Target Speed (km/h)', alpha=0.9)

    # Dynamic Y limits to scale up to top speed recorded
    top_speed = max(float(speed.max()), float(target.max()))
    y_top = math.ceil(top_speed / 20.0) * 20.0 + 10.0
    ax.set_ylim(0, y_top)
    ax.set_xlim(0, max(20.0, float(dist.max())))

    ax.set_ylabel("Speed (km/h)", fontsize=12, fontweight='bold')
    ax.set_xlabel("Course Distance (km)", fontsize=12, fontweight='bold')
    ax.set_title(f"20.0 km Longitudinal Speed Profile {title_suffix}", fontsize=14, fontweight='bold', pad=12)
    ax.grid(True, linestyle='--', alpha=0.25)

    handles, labels = ax.get_legend_handles_labels()
    handles += list(legend_patches.values())
    labels += list(legend_patches.keys())
    ax.legend(handles=handles, labels=labels, loc='upper right', ncol=3, framealpha=0.85, fontsize=9)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[Plot Saved] Longitudinal Speed Profile -> {output_path}")


def plot_longitudinal_throttle_profile(
    df: pd.DataFrame,
    output_path: str,
    title_suffix: str = ""
):
    """
    Figure 3: Longitudinal Throttle Input Profile across 20.0 km.
    Shows driver throttle application (0-100%) across environmental zones.
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 5), dpi=300)

    df_sorted = df.sort_values('Distance_km').reset_index(drop=True)
    dist = np.asarray(df_sorted['Distance_km'], dtype=float)
    thr = np.asarray(df_sorted['throttle'], dtype=float) if 'throttle' in df_sorted.columns else np.zeros_like(dist)

    # Zone background shading
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

        ax.axvspan(d_start, d_end, color=color, alpha=0.18)
        if zone_name not in legend_patches:
            legend_patches[zone_name] = mpatches.Patch(color=color, alpha=0.6, label=zone_name)

    # Throttle trace
    ax.plot(dist, thr * 100.0, color='#2ed573', linewidth=1.2, label='Throttle (%)')

    ax.set_ylabel("Throttle (%)", fontsize=12, fontweight='bold')
    ax.set_xlabel("Course Distance (km)", fontsize=12, fontweight='bold')
    ax.set_ylim(0, 105)
    ax.set_xlim(0, max(20.0, float(dist.max())))
    ax.set_title(f"20.0 km Longitudinal Throttle Profile {title_suffix}", fontsize=14, fontweight='bold', pad=12)
    ax.grid(True, linestyle='--', alpha=0.25)

    handles, labels = ax.get_legend_handles_labels()
    handles += list(legend_patches.values())
    labels += list(legend_patches.keys())
    ax.legend(handles=handles, labels=labels, loc='upper right', ncol=3, framealpha=0.85, fontsize=9)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[Plot Saved] Longitudinal Throttle Profile -> {output_path}")


# ==============================================================================
# 3. PIPELINE CONTROLLER
# ==============================================================================

def run_analysis_pipeline(
    input_files: list,
    output_dir: str = "analysis_outputs"
):
    """Executes the focused visualization pipeline for speed, throttle, and speed gap."""
    if not input_files:
        print("\n[Notice] No participant data files provided or found.")
        print("To collect participant data, run:")
        print("  python user_study.py --participant-id P01\n")
        print("Once data is collected, analyze it with:")
        print("  python analyze_participant.py\n")
        return

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[Pipeline] Ingesting {len(input_files)} participant file(s)...")
    for f in input_files:
        print(f"  - {f}")

    all_dfs = []
    for filepath in input_files:
        filename = os.path.basename(filepath)
        pid = filename.replace('participant_', '').replace('_data.csv', '')
        df = pd.read_csv(filepath)
        df['participant_id'] = pid
        all_dfs.append(df)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_summary = compute_zone_metrics(combined_df, participant_id="Cohort")

    # Print summary table to terminal
    print("\n" + "="*80)
    print("  COHORT AGGREGATED METRICS SUMMARY")
    print("="*80)
    print_summary_table(combined_summary)

    # Generate the 3 requested figures
    print("[Pipeline] Rendering focused visualization outputs...")
    title_suffix = f"({all_dfs[0]['participant_id'].iloc[0]})" if len(all_dfs) == 1 else "(Cohort)"

    speed_profile_file = os.path.join(output_dir, "longitudinal_speed_profile.png")
    throttle_profile_file = os.path.join(output_dir, "longitudinal_throttle_profile.png")
    boxplot_file = os.path.join(output_dir, "speed_gap_by_zone_boxplot.png")

    plot_longitudinal_speed_profile(all_dfs[0], speed_profile_file, title_suffix=title_suffix)
    plot_longitudinal_throttle_profile(all_dfs[0], throttle_profile_file, title_suffix=title_suffix)
    plot_speed_gap_boxplot(combined_df, boxplot_file, title_suffix=title_suffix)

    print("\n" + "="*80)
    print(f"  ANALYSIS PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"  Visualizations saved to: '{os.path.abspath(output_dir)}'")
    print("="*80 + "\n")


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(script_dir, 'results')

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
        help="Directory to search for 'participant_*_data.csv' files (default: auto-detected in results/)"
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default=None,
        help="Directory to store visualization plots (default: user_study/analysis_outputs)"
    )

    args = parser.parse_args()

    # Resolve search directory
    if args.dir:
        search_dir = args.dir
    elif os.path.exists(results_dir):
        search_dir = results_dir
    else:
        search_dir = script_dir

    out_dir = args.output_dir if args.output_dir else os.path.join(script_dir, 'analysis_outputs')

    # Collect files
    if args.file:
        if not os.path.exists(args.file):
            print(f"[Error] File not found: {args.file}")
            sys.exit(1)
        files = [args.file]
    else:
        files = glob.glob(os.path.join(search_dir, "participant_*_data.csv"))
        if not files:
            files = glob.glob(os.path.join(script_dir, "participant_*_data.csv"))
        if not files:
            files = glob.glob(os.path.join(os.getcwd(), "participant_*_data.csv"))
        files = [f for f in files if not f.endswith('_summary.csv')]

    run_analysis_pipeline(
        input_files=files,
        output_dir=out_dir
    )


if __name__ == '__main__':
    main()
