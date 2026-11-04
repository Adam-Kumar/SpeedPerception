# Predictive Modeling of Speed Misperception and Mitigation Utilizing Dynamic AR Peripheral Cues

Investigating human speed misperception across varied road environments without a speedometer, and evaluating subconscious mitigation using dynamic Augmented Reality (AR) peripheral visual cues.

---

## 1. Research Overview

* **Objective:**
  1. **Phase 1 (Current Focus):** Quantify how distinct road environments (tunnels, elevated bridges, high-density urban corridors, and open rural expressways) and road curvature (steering angle demand) distort human perception of vehicle speed in the absence of a speedometer ($v_{\mathrm{actual}} - v_{\mathrm{target}}$).
  2. **Phase 2 (Mitigation):** Design and evaluate dynamic peripheral visual cues (e.g., optical flow arrows and peripheral pacing) simulated in a driving simulator.
* **Simulation Platform:** BeamNG.drive (v0.3x – v0.40+) streaming 10Hz telemetry via a native UDP protocol extension (`lua/vehicle/protocols/userStudy.lua`) on `127.0.0.1:64256`.
* **Track:** Tokyo Shuto Expressway C1 Loop (a cut segment of 20.0 km of total course length), fitted with custom barriers, environmental backdrops, and an overhead finish line at 20.0 km.
* **Target Baseline Speed:** Constant 80.0 km/h (or zone-specific speed profiles).

### Environmental Zones (Tokyo C1 Loop)
| Zone | Course Time Range | Distance Range | Visual & Optical Flow Characteristics |
| :--- | :---: | :---: | :--- |
| **Pre-Test** | 0 – 25s | 0.00 – 0.77 km | Familiarization / adaptation zone at start |
| **Urban Expressway** | 25–40s, 82–93s, 145–190s, 282–320s | Intermittent segments | Elevated concrete structures, balanced peripheral cues |
| **Tunnel** | 40–82s, 93–145s | 1.57–3.70 km, 4.16–6.25 km | Constrained cross-section, repetitive artificial lighting, high optical flow |
| **Rural Expressway** | 190 – 255s | 8.70 – 12.28 km | Open factory backdrops, foliage, lower peripheral optical flow |
| **Bridge** | 255–282s, 320–356s | 12.28–13.76 km, 15.62–17.44 km | Open horizons, elevated water crossings, minimal roadside clutter |
| **Urban Road** | 356s to end (20.0 km) | 17.44 – 20.00 km | Surface street density, tighter turns, buildings, narrow field of view |

---

## 2. Directory Structure & File Inventory

The repository is organized into dedicated functional folders:

```text
Research/
├── README.md                          # Project documentation & operational workflow
├── AGENT_STATE.md                     # AI agent state & technical handoff document
│
├── levels/c1/                         # Custom BeamNG level configuration & assets for Tokyo C1
│
├── route_mapping/                     # Track ground-truth mapping & spatial annotation
│   ├── mapping_lap.py                 # 10Hz centerline telemetry & video recorder script
│   ├── mapping_lap.csv                # Raw ground-truth trajectory position log (X, Y, Z)
│   ├── mapping_lap_video_fixed.mp4    # Real-time duration reference video
│   ├── annotate_route.py              # Cumulative distance, 20.0km cutoff, & zone tagging script
│   └── annotated_route.csv            # Master spatial lookup table (4,410 points with zone flags)
│
└── user_study/                        # Participant experimental testing & analysis
    ├── user_study.py                  # Live 10Hz UDP study runner & 20.0km auto-finish logger
    ├── analyze_participant.py         # Multi-participant & individual plotting pipeline
    ├── results/                       # Participant 10Hz telemetry CSVs & session metadata JSONs
    │   ├── participant_<ID>_data.csv
    │   └── participant_<ID>_meta.json
    └── analysis_outputs/              # Generated visualization subfolders
        ├── individual/                # Individual plots per participant (individual_<ID>_*.png)
        └── averaged/                  # Spatially-averaged cohort plots (averaged_*.png)
```

### Detailed File Roles

#### `route_mapping/`
* **`mapping_lap.py`**: Connects to BeamNG.drive and records the initial baseline center-line trajectory $(X, Y, Z)$ at 10Hz while capturing synchronized screen video via `mss`. *(Run once to establish ground truth).*
* **`mapping_lap.csv`**: Raw 10Hz ground-truth position log (`Timestamp`, `X`, `Y`, `Z`) recorded along the course center-line.
* **`mapping_lap_video_fixed.mp4`**: Screen recording of the mapping lap adjusted to match real-time duration for visual zone verification.
* **`annotate_route.py`**: Processes `mapping_lap.csv`: computes cumulative 3D distance (`Distance_km`), applies the 20.0 km course cutoff, tags environmental zone labels, and provides an interactive Matplotlib inspection GUI with KDTree snapping.
* **`annotated_route.csv`**: Master spatial reference table containing 4,410 centerline points with `['Timestamp', 'X', 'Y', 'Z', 'Distance_km', 'environment_zone']` plus one-hot binary zone flags (`in_tunnel`, `is_bridge`, etc.). Pre-loaded by testing scripts for sub-millisecond route snapping.

#### `user_study/`
* **`user_study.py`**: **Active participant experiment runner.** Listens to the participant vehicle's native 10Hz UDP telemetry stream in BeamNG, snaps vehicle position to the nearest route point via KDTree, auto-terminates at the 20.0 km finish line, and saves all participant logs directly inside `user_study/results/`.
* **`analyze_participant.py`**: **Post-processing analysis pipeline.** Automatically ingests all participant CSVs from `user_study/results/`, generates individual 4-plot suites in `user_study/analysis_outputs/individual/`, and computes spatially-aligned averages across all participants in `user_study/analysis_outputs/averaged/`.
* **`results/`**: Storage directory for all participant telemetry data (`participant_<ID>_data.csv`) and session metadata (`participant_<ID>_meta.json`).
* **`analysis_outputs/`**: Dedicated directory containing `individual/` and `averaged/` visualization subfolders.

---

## 3. Step-by-Step Experiment Workflow

### Step 1: Track Preparation *(Completed)*
Ground-truth centerline mapping and environmental zone classification have been finalized in `route_mapping/annotated_route.csv`.

### Step 2: Running a Participant Session
1. Launch BeamNG.drive normally through Steam.
2. In the main menu, click **Freeroam** and load the **Tokyo Expressway C1** map.
3. Position your car at the start line and ensure the camera is in **Driver Cockpit POV** at a normal driving angle.
4. In terminal, navigate to `user_study/` (or run directly from root):
   ```powershell
   cd user_study

   # Basic run (prompts interactively for Participant ID):
   python user_study.py

   # Explicit run specifying Participant ID and Target Speed:
   python user_study.py --participant-id P01 --target-speed 80.0

   # Optional: Enable simultaneous screen recording on Monitor 2:
   python user_study.py --participant-id P01 --record-video --monitor 2
   ```
5. The script automatically:
   * Connects to the vehicle's native 10Hz UDP telemetry stream.
   * Prompts the driver through a 5-second countdown.
   * Logs 10Hz telemetry: vehicle coordinates, actual speed, target speed, speed gap, throttle, brake, steering angle, course distance, and active environmental zone.
   * Auto-detects the 20.0 km finish line, sounds a completion alert, and saves `participant_<ID>_data.csv` and `participant_<ID>_meta.json` into `user_study/results/`.

### Step 3: Analyzing Participant Data
Once one or more participant runs have been collected:
```powershell
cd user_study

# Automatically analyzes all participant files in results/ (generates both individual and averaged graphs):
python analyze_participant.py

# Or analyze a single specific participant file:
python analyze_participant.py -f results/participant_p01_data.csv
```
The analysis pipeline outputs:
* **Terminal Summary Tables:** Individual and cohort-averaged tables showing Mean speed, Target speed, Speed Gap ($v_{\mathrm{actual}} - v_{\mathrm{target}}$), RMSE, Mean Absolute Steering Angle ($|\text{Steer}|$), % under-speeding, % over-speeding, and dominant bias per zone.
* **Individual Participant Figures (`user_study/analysis_outputs/individual/`):**
  1. `individual_<ID>_longitudinal_speed_profile.png` — 20.0 km speed trajectory scaled dynamically to top recorded speed, with color-shaded environmental zones and target speed line.
  2. `individual_<ID>_longitudinal_throttle_profile.png` — Dedicated 20.0 km driver throttle input (0–100%) profile with environmental zone shading.
  3. `individual_<ID>_longitudinal_steering_profile.png` — Dedicated 20.0 km driver steering angle (°) profile with 0° neutral line and environmental zone shading.
  4. `individual_<ID>_speed_gap_by_zone_boxplot.png` — Speed Gap boxplots across zones with under/over-speeding regions and dynamic Y-axis.
* **Averaged Cohort Figures (`user_study/analysis_outputs/averaged/`):**
  1. `averaged_longitudinal_speed_profile.png` — Spatially-aligned mean speed trajectory across all participants over the 20.0 km course.
  2. `averaged_longitudinal_throttle_profile.png` — Spatially-aligned mean throttle input (%) across all participants over the 20.0 km course.
  3. `averaged_longitudinal_steering_profile.png` — Spatially-aligned mean steering angle (°) across all participants over the 20.0 km course.
  4. `averaged_speed_gap_by_zone_boxplot.png` — Aggregated Speed Gap boxplots across all participants by environmental zone.

---

### Edited Map Assets (`levels/c1/`)
The `levels/c1/` folder contains customized BeamNG level mission items, triggers, lighting, and markers for the Tokyo Shuto Expressway C1 loop. When migrating to a new machine, copy these contents into your BeamNG user folder under `levels/c1/` to load the exact experimental course setup.
