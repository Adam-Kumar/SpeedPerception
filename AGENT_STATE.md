# AGENT STATE & HANDOFF SPECIFICATION

> **Note for AI Agents:** Read this document first when starting a session or resuming work on any environment/device. It contains the active ground truth of the system, completed milestones, technical contracts, file layout, and immediate next actions. Keep this document updated after completing significant milestones.

---

## 1. Project Identity & Research Context

* **Project Title:** Predictive Modeling of Speed Misperception and Mitigation Utilizing Dynamic AR Peripheral Cues
* **Domain:** Perceptual Psychology, Human Factors, Driving Simulation, Augmented Reality (AR) in Virtual Reality (VR).
* **Research Goal:**
  * **Phase 1 (Active Focus):** Identify how visual road environments (tunnels, elevated bridges, rural open areas, dense urban streets) distort human velocity perception when driving without a speedometer, quantifying the "Speed Gap" ($v_{\mathrm{actual}} - v_{\mathrm{target}}$) and motor control instability (throttle hunting).
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

## 2. Directory Structure

```text
Research/
├── README.md                          # Human-facing project guide & workflow
├── AGENT_STATE.md                     # Agent state & technical handoff document
│
├── route_mapping/                     # Track ground-truth mapping & spatial annotation
│   ├── mapping_lap.py                 # Centerline logging & video recorder
│   ├── mapping_lap.csv                # Raw ground-truth trajectory position log
│   ├── mapping_lap_video_fixed.mp4    # Real-time duration reference video
│   ├── annotate_route.py              # Distance calculation, 20.0km cutoff, & zone labeling
│   └── annotated_route.csv            # Master spatial lookup table (4,410 points)
│
└── user_study/                        # Participant experimental testing & analysis
    ├── user_study.py                  # Live study runner (HUD hidden, 10Hz logging, auto-finish)
    ├── analyze_participant.py         # Post-study analysis & statistical plotting pipeline
    ├── participant_<ID>_data.csv      # (Generated upon testing) 10Hz participant telemetry
    ├── participant_<ID>_meta.json     # (Generated upon testing) Session metadata
    └── analysis_outputs/              # (Generated upon analysis) Plots, CSVs, Markdown reports
```

---

## 3. Environment & Simulation Specs

* **Host OS:** Windows (PowerShell)
* **Python Runtime:** Python 3.11 (`C:/Users/xadam/AppData/Local/Programs/Python/Python311/python.exe`)
* **Core Libraries:** `beamngpy`, `pandas`, `numpy`, `scipy` (KDTree), `matplotlib`, `seaborn`, `mss`, `cv2`
* **Simulator:** BeamNG.drive (v0.3x+)
* **Default Game Directory:** `C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive`
* **BeamNG API Interface:** `beamngpy.BeamNGpy('127.0.0.1', 64256)`
* **Active Track:** Tokyo Shuto Expressway C1 Loop (custom barrier configuration)
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

### B. Participant Telemetry Log: `user_study/participant_<ID>_data.csv`
Sampled at a strict 10Hz synchronized loop during human driving trials:
1. `timestamp` — Elapsed seconds
2. `x`, `y`, `z` — Current vehicle coordinates
3. `speed_kmh` — Velocity magnitude $\sqrt{v_x^2 + v_y^2 + v_z^2} \times 3.6$
4. `target_speed_kmh` — Prescribed target speed (default 80.0 km/h)
5. `speed_gap_kmh` — $v_{\mathrm{actual}} - v_{\mathrm{target}}$ (+ = over-speeding, - = under-speeding)
6. `throttle` — Driver throttle input (0.0 to 1.0 from vehicle `electrics` sensor)
7. `brake` — Driver brake input (0.0 to 1.0)
8. `steering` — Driver steering input
9. `Distance_km` — Centerline course position snapped via KDTree
10. `environment_zone` — Active spatial zone label
11. `is_pre_test` to `is_urban_road` — One-hot binary flags

---

## 5. Completed Milestones

- [x] **Centerline Mapping Lap:** Recorded 10Hz trajectory along Tokyo C1 centerline (`route_mapping/mapping_lap.py` -> `mapping_lap.csv`).
- [x] **Video Calibration:** Synchronized video capture for visual confirmation (`route_mapping/mapping_lap_video_fixed.mp4`).
- [x] **Spatial Annotation & Cutoff:** Computed cumulative distance, clipped course at exactly 20.0 km, tagged 6 environmental zones (`route_mapping/annotate_route.py` -> `annotated_route.csv`).
- [x] **Participant Testing Runner (`user_study/user_study.py`):**
  - Connects to BeamNG vehicle via `beamngpy`.
  - Disables in-game HUD & digital speedometer (`bng.ui.hide_hud()`).
  - Restores HUD reliably on exit or interrupt (`bng.ui.show_hud()`).
  - Auto-resolves route lookup path (`route_mapping/annotated_route.csv`).
  - Saves all session telemetry directly into `user_study/`.
  - Automatically detects 20.0 km finish threshold to stop cleanly.
  - Supports optional screen recording (`--record-video`).
- [x] **Automated Analysis Pipeline (`user_study/analyze_participant.py`):**
  - Computes zone-by-zone Speed Gap ($\mu, \sigma$, median, min, max, RMSE).
  - Quantifies throttle hunting ($\sigma_{\mathrm{throttle}}$) and adjustment jerk ($|\Delta \mathrm{thr}/\Delta t|$).
  - Performs one-way ANOVA and Kruskal-Wallis hypothesis tests across zones.
  - Generates 4 publication figures: Box plot, 20km Longitudinal Profile with shaded zones, Control Dynamics, and Stacked Misperception Proportions.
  - Generates summary CSVs and Markdown report into `user_study/analysis_outputs/`.
- [x] **Modular Directory Organization:** Separated into `route_mapping/` and `user_study/`, cleaned all demo test files, made all script paths self-resolving, and documented in `README.md`.

---

## 6. Immediate Next Tasks

1. **Conduct First Human Participant Pilot Session:**
   - Launch BeamNG with Tokyo Expressway scenario.
   - Run: `cd user_study; python user_study.py --participant-id P01 --target-speed 80.0`
   - Verify participant completes the 20.0 km lap and that `user_study/participant_P01_data.csv` is produced.
2. **Execute Analysis on Real Participant Data:**
   - Run: `cd user_study; python analyze_participant.py -f participant_P01_data.csv`
   - Review output metrics and figures in `user_study/analysis_outputs/` to verify empirical trends (e.g., under-speeding in tunnels, over-speeding on bridges).
3. **Cohort Aggregation (Once $N \ge 3$ participants collected):**
   - Run: `cd user_study; python analyze_participant.py`
   - Examine ANOVA $p$-values and cross-participant consistency.
4. **Transition to Phase 2 (AR Peripheral Visual Cues):**
   - Specify VR headset integration requirements (OpenXR / SteamVR / BeamNG camera overlay).
   - Design dynamic optical flow cues that modulate in response to real-time `speed_gap_kmh`.

---

## 7. Critical Technical Rules for AI Agents

* **Preserve In-Game HUD Safety:** Always wrap `bng.ui.hide_hud()` inside `try...finally` with `bng.ui.show_hud()`. Leaving HUD disabled permanently breaks standard BeamNG gameplay.
* **Keep KDTree 2D:** Querying 2D $(X, Y)$ is sufficient because Tokyo C1 course centerline points have no self-overlaps within 30 meters.
* **Velocity Calculation:** In `beamngpy`, `vehicle.state['vel']` is a 3D vector $[v_x, v_y, v_z]$ in m/s. Always compute magnitude $\sqrt{v_x^2 + v_y^2 + v_z^2} \times 3.6$ for true scalar speed in km/h.
* **Master Zone Color Palette:** Maintain strict palette consistency across all visual tools:
  * `Pre-Test`: `#6c757d` (dimgray)
  * `Urban Expressway`: `#00d2d3` (cyan)
  * `Tunnel`: `#0984e3` (dodgerblue)
  * `Rural Expressway`: `#2ed573` (limegreen)
  * `Bridge`: `#e056fd` (magenta)
  * `Urban Road`: `#f1c40f` (gold)


### Edited Level Configuration (`c1/`)
* **Purpose:** Custom BeamNG mission group data, triggers, lighting, decals, and barriers for the Tokyo C1 track.
* **Deployment on New Machine:** Copy `c1/` into `%LOCALAPPDATA%\BeamNG.drive\<version>\levels\c1\` or inside the level package to replicate course triggers and visual conditions.
