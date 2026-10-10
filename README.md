# Predictive Modeling of Speed Misperception and Mitigation Utilizing Dynamic AR Peripheral Cues

A driving simulation research project investigating human speed misperception across varied road environments without a speedometer, and evaluating subconscious mitigation using dynamic Augmented Reality (AR) peripheral visual cues.

---

## 1. Research Overview

* **Objective:**
  1. **Phase 1 (Current Focus):** Quantify how distinct road environments (tunnels, elevated bridges, high-density urban corridors, and open rural expressways) distort human perception of vehicle speed in the absence of a speedometer ($v_{\mathrm{actual}} - v_{\mathrm{target}}$).
  2. **Phase 2 (Mitigation):** Design and evaluate dynamic peripheral visual cues (e.g., optical flow arrows and peripheral pacing) projected inside a VR headset to subconsciously guide the driver back toward the target speed.
* **Simulation Platform:** BeamNG.drive (v0.3x+) connected via `beamngpy` at `127.0.0.1:64256`.
* **Track:** Tokyo Shuto Expressway C1 Loop (20.0 km total course length), fitted with custom barriers, environmental backdrops, and an overhead finish line at 20.0 km.
* **Target Baseline Speed:** Constant 80.0 km/h (or zone-specific speed profiles).

### Environmental Zones (Tokyo C1 Loop)
| Zone | Course Time Range | Distance Range | Visual & Optical Flow Characteristics |
| :--- | :---: | :---: | :--- |
| **Pre-Test** | 0 – 25s | 0.00 – 0.77 km | Familiarization / adaptation zone at start |
| **Urban Expressway** | 25–40s, 82–93s, 145–190s, 282–320s | Intermittent segments | Elevated concrete structures, balanced peripheral cues |
| **Tunnel** | 40–82s, 93–145s | 1.57–3.70 km, 4.16–6.25 km | Constrained cross-section, repetitive artificial lighting, high optical flow |
| **Rural Expressway** | 190 – 255s | 8.70 – 12.28 km | Open factory backdrops, foliage, lower peripheral optical flow |
| **Bridge** | 255–282s, 320–356s | 12.28–13.76 km, 15.62–17.44 km | Open horizons, elevated water crossings, minimal roadside clutter |
| **Urban Road** | 356s to end (20.0 km) | 17.44 – 20.00 km | Surface street density, buildings, narrow field of view |

---

## 2. Directory Structure & File Inventory

The repository is organized into dedicated functional folders:

```text
Research/
├── README.md                          # Project documentation & operational workflow
├── AGENT_STATE.md                     # AI agent state & technical handoff document
│
├── route_mapping/                     # Track ground-truth mapping & spatial annotation
│   ├── mapping_lap.py                 # 10Hz centerline telemetry & video recorder script
│   ├── mapping_lap.csv                # Raw ground-truth trajectory position log (X, Y, Z)
│   ├── mapping_lap_video_fixed.mp4    # Real-time duration reference video
│   ├── annotate_route.py              # Cumulative distance, 20.0km cutoff, & zone tagging script
│   └── annotated_route.csv            # Master spatial lookup table (4,410 points with zone flags)
│
└── user_study/                        # Participant experimental testing & analysis
    ├── user_study.py                  # Live study runner (HUD hidden, 10Hz logging, auto-finish)
    ├── analyze_participant.py         # Post-study analysis & statistical plotting pipeline
    ├── participant_<ID>_data.csv      # (Generated upon testing) 10Hz participant telemetry logs
    ├── participant_<ID>_meta.json     # (Generated upon testing) Session metadata
    └── analysis_outputs/              # (Generated upon analysis) Plots, CSV metrics, and Markdown reports
```

### Detailed File Roles

#### `route_mapping/`
* **`mapping_lap.py`**: Connects to BeamNG.drive and records the initial baseline center-line trajectory $(X, Y, Z)$ at 10Hz while capturing synchronized screen video via `mss`. *(Run once to establish ground truth).*
* **`mapping_lap.csv`**: Raw 10Hz ground-truth position log (`Timestamp`, `X`, `Y`, `Z`) recorded along the course center-line.
* **`mapping_lap_video_fixed.mp4`**: Screen recording of the mapping lap adjusted to match real-time duration for visual zone verification.
* **`annotate_route.py`**: Processes `mapping_lap.csv`: computes cumulative 3D distance (`Distance_km`), applies the 20.0 km course cutoff, tags environmental zone labels, and provides an interactive Matplotlib inspection GUI with KDTree snapping.
* **`annotated_route.csv`**: Master spatial reference table containing 4,410 centerline points with `['Timestamp', 'X', 'Y', 'Z', 'Distance_km', 'environment_zone']` plus one-hot binary zone flags (`in_tunnel`, `is_bridge`, etc.). Pre-loaded by testing scripts for sub-millisecond route snapping.

#### `user_study/`
* **`user_study.py`**: **Active participant experiment runner.** Connects to the participant vehicle in BeamNG, suppresses the in-game HUD/speedometer (`Alt+U`), logs 10Hz telemetry, snaps vehicle position to the nearest route point via KDTree, auto-terminates at the 20.0 km finish line, and saves all participant logs directly inside `user_study/`.
* **`analyze_participant.py`**: **Post-processing analysis pipeline.** Ingests participant CSVs from `user_study/`, computes zone-by-zone speed errors, variance, and throttle hunting, runs ANOVA statistical tests, and exports publication figures to `user_study/analysis_outputs/`.

---

## 3. Step-by-Step Experiment Workflow

### Step 1: Track Preparation *(Completed)*
Ground-truth centerline mapping and environmental zone classification have been finalized in `route_mapping/annotated_route.csv`.

### Step 2: Running a Participant Session
1. Launch BeamNG.drive and load the **Tokyo Expressway C1** map in Freeroam.
2. Place the participant vehicle at the start line.
3. In terminal, navigate to `user_study/` (or run directly from root):
   ```powershell
   cd user_study

   # Basic run (prompts interactively for Participant ID):
   python user_study.py

   # Explicit run specifying Participant ID and Target Speed:
   python user_study.py --participant-id P01 --target-speed 80.0

   # Optional: Enable simultaneous screen recording on Monitor 2:
   python user_study.py --participant-id P01 --record-video --monitor 2
   ```
4. The script automatically:
   * Disables the in-game HUD and speedometer so the driver drives purely by perception.
   * Prompts the driver through a 5-second countdown.
   * Logs 10Hz telemetry: vehicle coordinates, actual speed, target speed, speed gap, throttle, brake, steering, course distance, and active environmental zone.
   * Auto-detects the 20.0 km finish line, displays an on-screen completion notice, restores the in-game HUD, and saves `participant_P01_data.csv` and `participant_P01_meta.json` inside `user_study/`.

### Step 3: Analyzing Participant Data
Once one or more participant runs have been collected:
```powershell
cd user_study

# Analyze all participant files in user_study/ (default):
python analyze_participant.py

# Or analyze a single specific participant file:
python analyze_participant.py -f participant_P01_data.csv
```
The analysis pipeline outputs:
* **Terminal Summary Table:** Mean speed, Speed Gap ($v_{\mathrm{actual}} - v_{\mathrm{target}}$), RMSE, % under-speeding, % over-speeding, and throttle hunting per zone.
* **Statistical Tests:** One-way ANOVA and Kruskal-Wallis tests across environmental zones.
* **Publication Figures (`user_study/analysis_outputs/`):**
  1. `speed_gap_by_zone_boxplot.png` — Speed Gap boxplots across zones with under/over-speeding regions.
  2. `longitudinal_speed_profile.png` — 20.0 km speed trajectory with color-shaded environmental zones.
  3. `control_dynamics_comparison.png` — Throttle hunting and speed variance by zone.
  4. `misperception_proportions.png` — 100% stacked bar chart of perceptual states.
* **Reports:** `cohort_zone_metrics_summary.csv` and Markdown research summary.
