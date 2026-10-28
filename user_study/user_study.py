"""
User Study Testing Script: Predictive Modeling of Speed Misperception
======================================================================
Course: Tokyo Shuto Expressway C1 Loop (20.0 km)
Platform: BeamNG.drive via beamngpy

Protocol:
1. Connects to BeamNG.drive and attaches the participant's vehicle.
2. Disables the in-game HUD and digital speedometer (Alt+U equivalent via bng.ui.hide_hud()).
3. Samples 10Hz synchronized telemetry:
   - Position (X, Y, Z)
   - Actual Speed (km/h derived from 3D velocity vector)
   - Target Speed (km/h)
   - Speed Gap (v_actual - v_target)
   - Driver Control Inputs (Throttle, Brake, Steering)
4. Uses KDTree loaded from 'annotated_route.csv' to query the nearest course center-line point,
   logging 'Distance_km', 'environment_zone', and binary zone flags in real time.
5. Automatically detects the 20.0 km finish threshold to terminate cleanly and save
   'participant_<ID>_data.csv'.
6. Safely restores HUD on exit/completion.
"""

import os
import sys
import time
import math
import csv
import json
import argparse
import threading
import numpy as np
import pandas as pd
from scipy.spatial import KDTree

# BeamNGpy imports
try:
    from beamngpy import BeamNGpy, Vehicle
    from beamngpy.sensors import Electrics
except ImportError:
    print("Error: 'beamngpy' is not installed in this Python environment.")
    print("Install via: pip install beamngpy")
    sys.exit(1)

# Screen recorder dependencies
try:
    import cv2
    import mss
    HAS_SCREEN_RECORDER = True
except ImportError:
    HAS_SCREEN_RECORDER = False


# ==============================================================================
# SCREEN RECORDER THREAD (OPTIONAL)
# ==============================================================================

class ScreenRecorder:
    """Threaded screen capture recorder targeting the simulator monitor."""

    def __init__(self, filename='recording.mp4', fps=20.0, monitor_index=2):
        self.filename = filename
        self.fps = fps
        self.monitor_index = monitor_index
        self.recording = False
        self.thread = None

    def record(self):
        with mss.mss() as sct:
            if self.monitor_index < len(sct.monitors):
                monitor = sct.monitors[self.monitor_index]
            else:
                print(f"[Recorder] Monitor {self.monitor_index} not found. Defaulting to Monitor 1.")
                monitor = sct.monitors[1]

            fourcc = cv2.VideoWriter.fourcc(*'mp4v')
            out = cv2.VideoWriter(self.filename, fourcc, self.fps, (monitor['width'], monitor['height']))
            next_frame_time = time.time()

            while self.recording:
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                out.write(frame)

                next_frame_time += 1.0 / self.fps
                sleep_time = next_frame_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)

            out.release()

    def start(self):
        self.recording = True
        self.thread = threading.Thread(target=self.record, daemon=True)
        self.thread.start()

    def stop(self):
        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)


# ==============================================================================
# ROUTE MATCHER CLASS
# ==============================================================================

class RouteMatcher:
    """Pre-loads annotated_route.csv into a 2D KDTree for sub-millisecond spatial queries."""

    ZONE_COLUMNS = [
        'is_pre_test', 'is_urban_expressway', 'in_tunnel',
        'is_rural_expressway', 'is_bridge', 'is_urban_road'
    ]

    def __init__(self, route_csv_path=None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if route_csv_path is None or not os.path.exists(route_csv_path):
            candidates = [
                route_csv_path if route_csv_path else '',
                os.path.join(script_dir, '..', 'route_mapping', 'annotated_route.csv'),
                os.path.join(script_dir, 'annotated_route.csv'),
                os.path.join('route_mapping', 'annotated_route.csv'),
                'annotated_route.csv'
            ]
            found = False
            for c in candidates:
                if c and os.path.exists(c):
                    route_csv_path = os.path.abspath(c)
                    found = True
                    break
            if not found:
                raise FileNotFoundError(
                    f"Master route file '{route_csv_path}' not found.\n"
                    f"Please ensure 'route_mapping/annotated_route.csv' exists."
                )

        print(f"[RouteMatcher] Loading route lookup table: {route_csv_path}...")
        self.df = pd.read_csv(route_csv_path)

        # Validate essential columns
        required_cols = ['X', 'Y', 'Distance_km', 'environment_zone']
        for col in required_cols:
            if col not in self.df.columns:
                raise ValueError(f"Route file missing required column: '{col}'")

        # Ensure binary columns exist
        for col in self.ZONE_COLUMNS:
            if col not in self.df.columns:
                self.df[col] = 0

        self.coords_2d = self.df[['X', 'Y']].to_numpy()
        self.kdtree = KDTree(self.coords_2d)

        # Track course properties
        self.total_points = len(self.df)
        self.finish_distance_km = float(self.df['Distance_km'].max())
        self.finish_coord = (float(self.df.iloc[-1]['X']), float(self.df.iloc[-1]['Y']))

        print(f"[RouteMatcher] Ready! Loaded {self.total_points} centerline points.")
        print(f"[RouteMatcher] Course length: {self.finish_distance_km:.2f} km | Finish: X={self.finish_coord[0]:.1f}, Y={self.finish_coord[1]:.1f}")

    def query(self, x: float, y: float):
        """Finds nearest point on the route center-line. Returns (dist_to_route, row_dict)."""
        dist_to_route, idx = self.kdtree.query([x, y])
        row = self.df.iloc[idx]
        return dist_to_route, row


# ==============================================================================
# MAIN USER STUDY CONTROLLER
# ==============================================================================

def run_study(
    participant_id: str,
    target_speed_kmh: float = 80.0,
    target_profile: dict | None = None,
    output_dir: str | None = None,
    route_csv_path: str | None = None,
    beamng_dir: str = r"C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive",
    launch_game: bool = True,
    record_video: bool = False,
    monitor_index: int = 2,
    finish_dist_threshold_km: float = 19.995,
    countdown_sec: int = 5
):
    """
    Executes the participant testing session:
    - Launches/connects to BeamNG
    - Hides HUD
    - 10Hz telemetry capture & spatial matching
    - Auto-stop on 20.0 km finish
    - Clean exit and data export
    """

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if output_dir is None:
        output_dir = os.path.join(script_dir, 'results')

    os.makedirs(output_dir, exist_ok=True)
    out_csv = os.path.join(output_dir, f"participant_{participant_id}_data.csv")
    out_meta = os.path.join(output_dir, f"participant_{participant_id}_meta.json")
    out_video = os.path.join(output_dir, f"participant_{participant_id}_video.mp4")

    # 1. Initialize Route Matcher
    matcher = RouteMatcher(route_csv_path)

    import socket
    import struct
    PACKET_FORMAT = '<11f'
    PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

    print("\n" + "="*70)
    print(f"  PARTICIPANT STUDY SESSION: {participant_id}")
    print(f"  Target Speed: {target_speed_kmh:.1f} km/h (Constant baseline)" if not target_profile else "  Target Speed: Dynamic Zone Profile")
    print(f"  Output CSV: {out_csv}")
    print("="*70 + "\n")

    # Set up UDP socket listener for BeamNG telemetry
    telemetry_port = 64256
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('127.0.0.1', telemetry_port))
    except Exception as e:
        print(f"[Error] Could not bind UDP socket on 127.0.0.1:{telemetry_port}: {e}")
        return

    sock.settimeout(1.0)
    video_recorder = None
    csv_file = None
    points_logged = 0
    max_dist_reached = 0.0

    try:
        # Prompt experimenter / participant
        print("--- EXPERIMENT PREPARATION ---")
        print("1. In BeamNG: Click 'Freeroam' and load Tokyo Expressway C1.")
        print("2. Ensure your vehicle is spawned at the starting grid line.")
        print("3. Press '1' (or 'C') in-game for Driver Cockpit POV.")
        print("4. Press 'Alt + U' in-game to hide the speedometer / HUD.")
        print(f"\nWaiting for vehicle telemetry from BeamNG on port {telemetry_port}...")

        # Wait for vehicle telemetry stream from BeamNG
        connected = False
        while not connected:
            try:
                data, addr = sock.recvfrom(1024)
                if len(data) >= PACKET_SIZE:
                    connected = True
                    print(f"\n[BeamNG] Vehicle connected! Live 10Hz telemetry received from {addr[0]}.")
            except socket.timeout:
                pass

        # Start Video Recorder if requested
        if record_video:
            if HAS_SCREEN_RECORDER:
                print(f"[Recorder] Starting video recording on monitor {monitor_index} -> {out_video}")
                video_recorder = ScreenRecorder(out_video, fps=20.0, monitor_index=monitor_index)
                video_recorder.start()
            else:
                print("[Warning] 'opencv-python' or 'mss' not installed. Video recording disabled.")

        # Countdown
        print(f"\n[Ready] Driver, prepare! Session starts in {countdown_sec} seconds...")
        for c in range(countdown_sec, 0, -1):
            print(f"Starting in {c}...", end="\r", flush=True)
            time.sleep(1.0)
        print("\n>>> GO! Drive at target speed without speedometer. <<<\n")

        # Prepare CSV Writer
        csv_headers = [
            'timestamp', 'x', 'y', 'z',
            'speed_kmh', 'target_speed_kmh', 'speed_gap_kmh',
            'throttle', 'brake', 'steering',
            'Distance_km', 'environment_zone',
            'is_pre_test', 'is_urban_expressway', 'in_tunnel',
            'is_rural_expressway', 'is_bridge', 'is_urban_road'
        ]

        csv_file = open(out_csv, 'w', newline='')
        writer = csv.writer(csv_file)
        writer.writerow(csv_headers)

        start_time = time.time()
        max_dist_reached = 0.0
        points_logged = 0
        finish_triggered = False

        # Drain any stale packets before starting telemetry loop
        sock.settimeout(0.01)
        while True:
            try:
                sock.recvfrom(1024)
            except Exception:
                break
        sock.settimeout(0.5)

        # Telemetry Loop (10 Hz Synchronized from BeamNG stream)
        while not finish_triggered:
            try:
                data, _ = sock.recvfrom(1024)
                if len(data) < PACKET_SIZE:
                    continue
            except socket.timeout:
                continue

            sim_time, pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, speed_kmh, throttle_val, brake_val, steering_val = struct.unpack(
                PACKET_FORMAT, data[:PACKET_SIZE]
            )

            actual_speed_kmh = round(float(speed_kmh), 2)
            throttle_val = round(float(throttle_val), 3)
            brake_val = round(float(brake_val), 3)
            steering_val = round(float(steering_val), 3)
            pos = [float(pos_x), float(pos_y), float(pos_z)]

            # Spatial matching via KDTree
            _, matched = matcher.query(pos[0], pos[1])
            dist_km = round(float(matched['Distance_km']), 4)
            env_zone = str(matched['environment_zone'])
            max_dist_reached = max(max_dist_reached, dist_km)

            # Determine Target Speed
            if target_profile and env_zone in target_profile:
                target_v = float(target_profile[env_zone])
            else:
                target_v = float(target_speed_kmh)

            speed_gap_kmh = round(actual_speed_kmh - target_v, 2)
            current_elapsed = round(time.time() - start_time, 2)

            # Write row to CSV
            row_data = [
                current_elapsed,
                round(pos[0], 3), round(pos[1], 3), round(pos[2], 3),
                actual_speed_kmh, target_v, speed_gap_kmh,
                throttle_val, brake_val, steering_val,
                dist_km, env_zone,
                int(matched.get('is_pre_test', 0)),
                int(matched.get('is_urban_expressway', 0)),
                int(matched.get('in_tunnel', 0)),
                int(matched.get('is_rural_expressway', 0)),
                int(matched.get('is_bridge', 0)),
                int(matched.get('is_urban_road', 0))
            ]
            writer.writerow(row_data)
            csv_file.flush()
            points_logged += 1

            # Format live dashboard indicator
            if speed_gap_kmh > 3.0:
                gap_tag = f"\033[91m[OVER  +{speed_gap_kmh:4.1f}]\033[0m"
            elif speed_gap_kmh < -3.0:
                gap_tag = f"\033[94m[UNDER {speed_gap_kmh:4.1f}]\033[0m"
            else:
                gap_tag = f"\033[92m[ON-TGT {speed_gap_kmh:+4.1f}]\033[0m"

            sys.stdout.write(
                f"\r[{current_elapsed:6.1f}s | {dist_km:5.2f}/20.0 km] "
                f"Zone: {env_zone:<16} | "
                f"v: {actual_speed_kmh:5.1f} km/h (tgt:{target_v:4.0f}) {gap_tag} | "
                f"Thr: {int(throttle_val*100):2d}% Brk: {int(brake_val*100):2d}%"
            )
            sys.stdout.flush()

            # FINISH THRESHOLD DETECTION
            dist_to_finish = math.hypot(pos[0] - matcher.finish_coord[0], pos[1] - matcher.finish_coord[1])
            if dist_km >= finish_dist_threshold_km or (max_dist_reached >= 19.95 and dist_to_finish < 8.0):
                finish_triggered = True
                completed_dist = 20.00 if max_dist_reached >= 19.95 else round(max_dist_reached, 2)
                print("\n\n" + "*"*70)
                print(f"  >>> FINISH LINE REACHED AT {completed_dist:.2f} KM! STUDY COMPLETED <<<")
                print("*"*70)
                try:
                    import winsound
                    winsound.Beep(1200, 600)
                except Exception:
                    pass
                break

    except KeyboardInterrupt:
        print("\n\n[Study] Session manually terminated by experimenter (Ctrl+C).")
    finally:
        # Close UDP socket
        try:
            sock.close()
        except Exception:
            pass

        # Close CSV
        if csv_file is not None:
            try:
                csv_file.close()
            except Exception:
                pass

        # Stop video recording
        if video_recorder:
            print("[Recorder] Finalizing video recording...")
            video_recorder.stop()

        # Save session metadata
        completed_dist = 20.00 if max_dist_reached >= 19.95 else round(max_dist_reached, 3)
        meta = {
            "participant_id": participant_id,
            "session_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_speed_kmh": target_speed_kmh,
            "target_profile": target_profile,
            "points_logged": points_logged,
            "course_distance_logged_km": completed_dist,
            "data_file": out_csv,
            "video_file": out_video if record_video else None
        }
        with open(out_meta, 'w') as mf:
            json.dump(meta, mf, indent=4)

        print(f"\n[Complete] Session data saved successfully:")
        print(f"  - Telemetry CSV: {out_csv} ({points_logged} points)")
        print(f"  - Session Meta:  {out_meta}")
        if record_video:
            print(f"  - Screen Video:  {out_video}")
        print("\nPress 'Alt + U' in BeamNG to restore HUD.")
        print(f"To analyze this session, run:\n  python analyze_participant.py -f {out_csv}\n")


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="BeamNG User Study Runner: Predictive Modeling of Speed Misperception",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-p', '--participant-id',
        type=str,
        default=None,
        help="Unique identifier for the participant (e.g., 'P01', 'pilot_01')"
    )
    parser.add_argument(
        '-s', '--target-speed',
        type=float,
        default=80.0,
        help="Baseline target speed in km/h for the participant"
    )
    parser.add_argument(
        '--target-profile',
        type=str,
        default=None,
        help="Optional path to JSON file specifying zone-specific target speeds"
    )
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_results_dir = os.path.join(script_dir, 'results')
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default=default_results_dir,
        help="Directory where CSV telemetry and video recordings will be saved (default: user_study/results)"
    )
    parser.add_argument(
        '--route-csv',
        type=str,
        default=None,
        help="Path to master annotated route CSV (default: auto-detected in route_mapping/)"
    )
    parser.add_argument(
        '--beamng-dir',
        type=str,
        default=r"C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive",
        help="BeamNG.drive installation path"
    )
    parser.add_argument(
        '--no-launch',
        action='store_true',
        help="Do not launch BeamNG executable, connect to an existing running instance"
    )
    parser.add_argument(
        '--record-video',
        action='store_true',
        help="Enable simultaneous screen recording of the participant lap"
    )
    parser.add_argument(
        '--monitor',
        type=int,
        default=2,
        help="Monitor index to record if screen recording is enabled (default 2, external monitor)"
    )
    parser.add_argument(
        '--finish-dist',
        type=float,
        default=19.995,
        help="Distance threshold in km to trigger automatic lap completion"
    )
    parser.add_argument(
        '--countdown',
        type=int,
        default=5,
        help="Countdown seconds before recording starts"
    )

    args = parser.parse_args()

    # Prompt interactively if participant ID is omitted
    pid = args.participant_id
    if not pid:
        try:
            pid = input("Enter Participant ID (e.g. P01): ").strip()
        except EOFError:
            pid = "P01"
        if not pid:
            pid = f"P_{int(time.time())}"

    # Load zone-specific target speeds if provided
    profile = None
    if args.target_profile:
        if os.path.exists(args.target_profile):
            with open(args.target_profile, 'r') as f:
                profile = json.load(f)
            print(f"[Config] Loaded zone target profile: {profile}")
        else:
            print(f"[Warning] Target profile JSON '{args.target_profile}' not found. Using constant {args.target_speed} km/h.")

    run_study(
        participant_id=pid,
        target_speed_kmh=args.target_speed,
        target_profile=profile,
        output_dir=args.output_dir,
        route_csv_path=args.route_csv,
        beamng_dir=args.beamng_dir,
        launch_game=not args.no_launch,
        record_video=args.record_video,
        monitor_index=args.monitor,
        finish_dist_threshold_km=args.finish_dist,
        countdown_sec=args.countdown
    )


if __name__ == '__main__':
    main()
