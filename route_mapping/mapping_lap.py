from beamngpy import BeamNGpy
import time
import csv
import os
import cv2
import mss
import numpy as np
import threading

# --- SCREEN RECORDER CLASS ---
class ScreenRecorder:

  def __init__(
      self, filename='mapping_lap_video.mp4', fps=20.0, monitor_index=2
  ):
    self.filename = filename
    self.fps = fps
    self.monitor_index = monitor_index  # Set to 2 for external monitor
    self.recording = False
    self.thread = None

  def record(self):
    with mss.mss() as sct:
      # Select the specified monitor index safely
      if self.monitor_index < len(sct.monitors):
        monitor = sct.monitors[self.monitor_index]
      else:
        print(
            f"Warning: Monitor index {self.monitor_index} not found. Falling"
            " back to Monitor 1."
        )
        monitor = sct.monitors[1]

      fourcc = cv2.VideoWriter.fourcc(*'mp4v')
      out = cv2.VideoWriter(
          self.filename, fourcc, self.fps, (monitor['width'], monitor['height'])
      )

      next_frame_time = time.time()

      while self.recording:
        img = sct.grab(monitor)
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        out.write(frame)

        # Dynamically calculate sleep to prevent video drift
        next_frame_time += 1.0 / self.fps
        sleep_time = next_frame_time - time.time()
        if sleep_time > 0:
          time.sleep(sleep_time)

      out.release()

  def start(self):
    self.recording = True
    self.thread = threading.Thread(target=self.record)
    self.thread.start()

  def stop(self):
    self.recording = False
    if self.thread:
      self.thread.join()

# --- MAIN SCRIPT ---

# Provide your exact BeamNG.drive installation path
BEAMNG_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive"

if not os.path.exists(BEAMNG_DIR):
    print(f"Error: Could not find BeamNG at {BEAMNG_DIR}")
    exit()

print("Python is launching BeamNG.drive...")
bng = BeamNGpy('127.0.0.1', 64256, home=BEAMNG_DIR)
bng.open(launch=True)

print("\n--- GAME CONNECTED ---")
print("1. Use your mouse in-game to click 'Freeroam'.")
print("2. Load the Tokyo Expressway map.")
print("3. Wait for your car to spawn at your start line.")
print("\nWaiting for you to load in... (Script will pause here)")

vehicles = {}
while not vehicles:
    try:
        vehicles = bng.get_current_vehicles()
    except Exception:
        pass
    time.sleep(2)

vid = list(vehicles.keys())[0]
vehicle = vehicles[vid]
vehicle.connect(bng)

print(f"\nCar found! (ID: {vid})")
print("Put your hands on the wheel! Recording starts in 5 seconds...")
time.sleep(5)

# Initialize the screen recorder and file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
video_file = os.path.join(SCRIPT_DIR, 'mapping_lap_video.mp4')
filename = os.path.join(SCRIPT_DIR, 'mapping_lap.csv')
video_recorder = ScreenRecorder(video_file, fps=20.0)

with open(filename, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp', 'X', 'Y', 'Z']) 

    print(f"\n--- RECORDING STARTED ---")
    print("Start driving! Drive slowly and stay in the exact center of the lane.")
    print("Press Ctrl+C in this terminal when you finish the lap to stop recording.")
    
    start_time = time.time()
    next_log_time = start_time
    
    # START THE VIDEO RECORDING THREAD
    video_recorder.start()
    
    try:
        while True:
            vehicle.sensors.poll() 
            pos = vehicle.state['pos'] 
            current_time = round(time.time() - start_time, 2)
            
            writer.writerow([current_time, pos[0], pos[1], pos[2]])
            file.flush() 
            
            print(f"\rRecording... Time: {current_time}s | Pos: X:{pos[0]:.1f}, Y:{pos[1]:.1f}", end="")
            
            # Precision 10Hz timing to prevent CSV drift
            next_log_time += 0.1
            sleep_time = next_log_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        # STOP THE VIDEO RECORDING THREAD
        print("\nSaving video file... Please wait a moment.")
        video_recorder.stop()
        
        print(f"\n--- RECORDING STOPPED ---")
        print(f"Data saved to {filename}")
        print(f"Video saved to mapping_lap_video.mp4")

bng.close()