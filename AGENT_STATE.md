# AGENT STATE & HANDOFF SPECIFICATION

> **Note for AI Agents:** Read this document first when starting a session or resuming work on any environment/device. It contains the active ground truth of the system, completed milestones, technical contracts, file layout, and immediate next actions. Keep this document updated after completing significant milestones.

---

## 1. Project Identity & Research Context

* **Project Title:** Predictive Modeling of Speed Misperception and Mitigation Utilizing Dynamic AR Peripheral Cues
* **Domain:** Perceptual Psychology, Human Factors, Driving Simulation, Augmented Reality (AR) in Virtual Reality (VR).
* **Research Goal:**
  * **Phase 1 (Active Focus):** Identify how visual road environments (tunnels, elevated bridges, rural open areas, dense urban streets) and road curvature (steering angle demand) distort human velocity perception when driving without a speedometer, quantifying the "Speed Gap" ($v_{\mathrm{actual}} - v_{\mathrm{target}}$) and motor control dynamics.
  * **Phase 2 (Upcoming):** Design dynamic AR peripheral visual cues (e.g., optical flow vectors) projected in a VR headset to subconsciously correct the Speed Gap in real time.

---

## 1.1 GitHub Remote Repository
* **Remote URL:** `https://github.com/Adam-Kumar/SpeedPerception.git`
* **Default Branch:** `main`
* **Clone Command for Other Machines:**
  ```bash
  git clone https://github.com/Adam-Kumar/SpeedPerception.git
  ```
* **Note on Large Media:** `route_mapping/mapping_lap_video_fixed.mp4` (2.7 GB) is excluded from git via `.gitignore` due to GitHub's 100 MB per-file upload limit. Transfer the MP4 separately (e.g. via OneDrive/USB) if visual reference playback is needed on the second machine. All code and CSV route datasets are version-controlled in the repository.

---

## 2. Directory Structure

```text
Research/
├── README.md                          # Human-facing project guide & workflow
├── AGENT_STATE.md                     # Agent state & technical handoff document
│
├── levels/c1/                         # Custom BeamNG level configuration & assets for Tokyo C1
├── lua/vehicle/protocols/             # Native 10Hz UDP telemetry protocol (userStudy.lua)
├── vehicles/bastion/                  # Bruckell Bastion live gauge hider & keybind toggle ('G' key)
│   ├── bastion_interior.jbeam         # Hooks studyGaugeToggle controller & study_hide_gauges electrics
│   ├── input_actions.json             # Registers 'toggle_study_gauges' vehicle action
│   ├── inputmaps/keyboard.json        # Binds 'G' key to toggle gauges ON/OFF in real time
│   ├── lua/controller/
│   │   └── studyGaugeToggle.lua       # Toggles 3D Speedometer & RPM needles + digital speed flag
│   └── gauges_screen/
│       └── gauge_standard.js          # Dynamically hides/shows center LCD digital speed readout
│
├── route_mapping/                     # Track ground-truth mapping & spatial annotation
│   ├── mapping_lap.py                 # Centerline logging & video recorder
│   ├── mapping_lap.csv                # Raw ground-truth trajectory position log
│   ├── mapping_lap_video_fixed.mp4    # Real-time duration reference video
│   ├── annotate_route.py              # Distance calculation, 20.0km cutoff, & zone labeling
│   └── annotated_route.csv            # Master spatial lookup table (4,410 points)
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

---

## 3. Environment & Simulation Specs

* **Host OS:** Windows (PowerShell)
* **Python Runtime:** Python 3.11+ / 3.15
* **Core Libraries:** `pandas`, `numpy`, `scipy` (KDTree), `matplotlib`, `mss`, `cv2`
* **Simulator:** BeamNG.drive (v0.3x – v0.40+ Steam edition)
* **Default Game Directory:** `C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive`
* **Telemetry Interface:** Native 10Hz UDP stream via `lua/vehicle/protocols/userStudy.lua` listening on `127.0.0.1:64256` (11-float packet: `time, pos(3), vel(3), speed_kmh, throttle, brake, steering`)
* **Active Track:** Tokyo Shuto Expressway C1 Loop (custom barrier configuration in `levels/c1/`)
* **Course Cutoff Length:** Exactly 20.00 km (Start: $X=3819.65, Y=-5113.19$ | Finish: $X=-8782.59, Y=-16208.17$)
* **Target Baseline Speed:** 80.0 km/h baseline

---

## 4. Data Contracts & Schemas

### A. Master Spatial Reference: `route_mapping/annotated_route.csv` (4,410 rows)
Pre-loaded into a 2D `scipy.spatial.KDTree` by `user_study.py` for sub-millisecond route snapping:
* `Timestamp` — Elapsed seconds from mapping lap (0.02s to 440.90s)
* `X`, `Y`, `Z` — Ground-truth centerline Cartesian coordinates
* `Distance_km` — Cumulative centerline 3D/2D distance (0.0000 km to 19.9985 km)
* `is_pre_test`, `is_urban_expressway`, `in_tunnel`, `is_rural_expressway`, `is_bridge`, `is_urban_road` — Binary flags
* `environment_zone` — String categorical label:
  * `Pre-Test` (0–25s, 0.00–0.77 km)
  * `Urban Expressway` (25–40s, 82–93s, 145–190s, 282–320s)
  * `Tunnel` (40–82s, 93–145s, 1.57–3.70 km, 4.16–6.25 km)
  * `Rural Expressway` (190–255s, 8.70–12.28 km)
  * `Bridge` (255–282s, 320–356s, 12.28–13.76 km, 15.62–17.44 km)
  * `Urban Road` (356s to end / 20.00 km)

### B. Participant Telemetry Log: `user_study/results/participant_<ID>_data.csv`
Sampled at a strict 10Hz synchronized loop during human driving trials:
1. `timestamp` — Elapsed seconds
2. `x`, `y`, `z` — Current vehicle coordinates
3. `speed_kmh` — Velocity magnitude $\sqrt{v_x^2 + v_y^2 + v_z^2} \times 3.6$
4. `target_speed_kmh` — Prescribed target speed (default 80.0 km/h)
5. `speed_gap_kmh` — $v_{\mathrm{actual}} - v_{\mathrm{target}}$ (+ = over-speeding, - = under-speeding)
6. `throttle` — Driver throttle input (0.0 to 1.0 from vehicle `electrics` sensor)
7. `brake` — Driver brake input (0.0 to 1.0)
8. `steering` — Driver steering wheel angle in degrees (from vehicle `electrics` sensor)
9. `Distance_km` — Centerline course position snapped via KDTree
10. `environment_zone` — Active spatial zone label
11. `is_pre_test` to `is_urban_road` — One-hot binary flags

---

## 5. Completed Milestones

- [x] **Centerline Mapping Lap:** Recorded 10Hz trajectory along Tokyo C1 centerline (`route_mapping/mapping_lap.py` -> `mapping_lap.csv`).
- [x] **Video Calibration:** Synchronized video capture for visual confirmation (`route_mapping/mapping_lap_video_fixed.mp4`).
- [x] **Spatial Annotation & Cutoff:** Computed cumulative distance, clipped course at exactly 20.0 km, tagged 6 environmental zones (`route_mapping/annotate_route.py` -> `annotated_route.csv`).
- [x] **Participant Testing Runner (`user_study/user_study.py`):**
  - Connects to BeamNG vehicle via native 10Hz UDP telemetry protocol (`userStudy.lua` on `127.0.0.1:64256`).
  - Auto-resolves route lookup path (`route_mapping/annotated_route.csv`).
  - Saves all session telemetry directly into `user_study/results/`.
  - Tightened finish proximity detection radius to 8.0m and threshold to 19.995 km, clamping completed lap distance to 20.00 km.
  - Removed obsolete HUD-hiding prompts/code (`Alt+U` does not hide 3D cockpit gauges).
  - Supports optional screen recording (`--record-video`).
- [x] **Multi-Participant & Individual Analysis Pipeline (`user_study/analyze_participant.py`):**
  - Automatically discovers all participant logs in `user_study/results/`.
  - Generates 4 focused visual figures for each individual participant in `user_study/analysis_outputs/individual/` (`individual_<ID>_*.png`) and spatially-averaged cohort figures in `user_study/analysis_outputs/averaged/` (`averaged_*.png`):
    1. `longitudinal_speed_profile.png` (scaled dynamically to top speed recorded, with zone shading)
    2. `longitudinal_throttle_profile.png` (dedicated 20.0 km throttle % profile with zone shading)
    3. `longitudinal_steering_profile.png` (dedicated 20.0 km steering angle ° profile with 0° reference line and zone shading)
    4. `speed_gap_by_zone_boxplot.png` (speed gap box plot with dynamic Y limits)
- [x] **Standardized Study Vehicle & Live In-Cabin Gauge Toggle (`vehicles/bastion/`):**
  - Standardized study vehicle: **Bruckell Bastion** (`bastion`).
  - Preparation & Familiarization Phase documented: participants first drive for a few minutes in a separate practice location with gauges toggled **ON** (**`G`** key) to acclimate to vehicle controls and calibrate their visual perception of **80 km/h**, before toggling gauges **OFF** (**`G`** key) for the 20.0 km Tokyo C1 test session.
  - Deployed VFS overrides into `%LOCALAPPDATA%\BeamNG\BeamNG.drive\current\vehicles\bastion\` and version-controlled in `vehicles/bastion/`:
    - `lua/controller/studyGaugeToggle.lua`: Custom auxiliary vehicle controller that toggles `prop.hidden` on both `bastion_speedometer_needle` and `bastion_tachometer_needle` in `v.data.props` and sets `electrics.values.study_hide_gauges` (1 = hidden, 0 = visible) in real time without vehicle reload.
    - `input_actions.json` & `inputmaps/keyboard.json`: Binds the **`G`** key to `toggle_study_gauges`.
    - `bastion_interior.jbeam`: Loads `studyGaugeToggle`, exposes `study_hide_gauges` to the HTML gauge cluster, and enables `toggle_study_gauges`.
    - `gauges_screen/gauge_standard.js`: Dynamically hides/shows `#speedometer` (`speedoDisplay.rootspeedo`) and `speedometerText` in sync with `data.electrics.study_hide_gauges`.

---

## 6. Immediate Next Tasks

1. **Conduct Experimental Participant Sessions:**
   - Spawn the **Bruckell Bastion** on the Tokyo C1 loop in Driver Cockpit POV.
   - Run: `python user_study/user_study.py --participant-id <PID> --target-speed 80.0`
   - Telemetry automatically archives into `user_study/results/`.
2. **Analyze Participant Results:**
   - Run: `python user_study/analyze_participant.py`
   - Updates individual plots in `user_study/analysis_outputs/individual/` and cohort-averaged plots in `user_study/analysis_outputs/averaged/`.

---

## 7. Critical Technical Rules for AI Agents

* **Keep KDTree 2D:** Querying 2D $(X, Y)$ is sufficient because Tokyo C1 course centerline points have no self-overlaps within 30 meters.
* **Velocity Calculation:** Always compute magnitude $\sqrt{v_x^2 + v_y^2 + v_z^2} \times 3.6$ for true scalar speed in km/h.
* **Master Zone Color Palette:** Maintain strict palette consistency across all visual tools:
  * `Pre-Test`: `#6c757d` (dimgray)
  * `Urban Expressway`: `#00d2d3` (cyan)
  * `Tunnel`: `#0984e3` (dodgerblue)
  * `Rural Expressway`: `#2ed573` (limegreen)
  * `Bridge`: `#e056fd` (magenta)
  * `Urban Road`: `#f1c40f` (gold)

### Edited Level Configuration (`levels/c1/`)
* **Purpose:** Custom BeamNG mission group data, triggers, lighting, decals, and barriers for the Tokyo C1 track.
* **Deployment on New Machine:** Copy `levels/c1/` into `%LOCALAPPDATA%\BeamNG\BeamNG.drive\current\levels\c1\` to replicate course triggers and visual conditions.
