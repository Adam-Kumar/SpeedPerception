import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import KDTree
import numpy as np

# Script directory resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
csv_in = os.path.join(SCRIPT_DIR, 'mapping_lap.csv') if not os.path.exists('mapping_lap.csv') else 'mapping_lap.csv'
csv_out = os.path.join(SCRIPT_DIR, 'annotated_route.csv')

# 1. Load recorded mapping lap
print(f"Loading {csv_in}...")
df = pd.read_csv(csv_in)

# --- CALCULATE DISTANCE COVERED ---
df['dx'] = df['X'].diff()
df['dy'] = df['Y'].diff()

if 'Z' in df.columns:
    df['dz'] = df['Z'].diff()
    step_distances = np.sqrt(df['dx']**2 + df['dy']**2 + df['dz']**2)
else:
    step_distances = np.sqrt(df['dx']**2 + df['dy']**2)

step_distances = pd.Series(step_distances).fillna(0)
df['Distance_km'] = step_distances.cumsum() / 1000.0
df = df.drop(columns=['dx', 'dy', 'dz'], errors='ignore')

# Initialize binary indicator columns and environment zone string
zones = [
    'is_pre_test', 'is_urban_expressway', 'in_tunnel', 
    'is_rural_expressway', 'is_bridge', 'is_urban_road'
]
for zone in zones:
    df[zone] = 0
df['environment_zone'] = 'Unlabeled'

def apply_zone(df, start_t, end_t, col_name, label_name):
    if end_t is None:
        mask = (df['Timestamp'] >= start_t)
    else:
        mask = (df['Timestamp'] >= start_t) & (df['Timestamp'] <= end_t)
    df.loc[mask, col_name] = 1
    df.loc[mask, 'environment_zone'] = label_name

# --- APPLY SPECIFIED TIMESTAMPS ---
apply_zone(df, 0, 25, 'is_pre_test', 'Pre-Test')
apply_zone(df, 25, 40, 'is_urban_expressway', 'Urban Expressway')
apply_zone(df, 40, 82, 'in_tunnel', 'Tunnel')
apply_zone(df, 82, 93, 'is_urban_expressway', 'Urban Expressway')
apply_zone(df, 93, 145, 'in_tunnel', 'Tunnel')
apply_zone(df, 145, 190, 'is_urban_expressway', 'Urban Expressway')
apply_zone(df, 190, 255, 'is_rural_expressway', 'Rural Expressway')
apply_zone(df, 255, 282, 'is_bridge', 'Bridge')
apply_zone(df, 282, 320, 'is_urban_expressway', 'Urban Expressway')
apply_zone(df, 320, 356, 'is_bridge', 'Bridge')
apply_zone(df, 356, None, 'is_urban_road', 'Urban Road')

# Save master annotated CSV

# Trim the dataframe to cap the track at exactly 20.0 km
df = df[df['Distance_km'] <= 20.0]
df.to_csv(csv_out, index=False)
print(f"Success! Saved '{csv_out}' with {len(df)} logged points.")

# ==========================================
# INTERACTIVE VISUALIZATION WITH PROXIMITY SNAPPING
# ==========================================

xy_coords = df[['X', 'Y']].to_numpy()
kdtree = KDTree(xy_coords)

plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(14, 9))

color_map = {
    'Pre-Test': 'dimgray',
    'Urban Expressway': 'cyan',
    'Tunnel': 'dodgerblue',
    'Rural Expressway': 'limegreen',
    'Bridge': 'magenta',
    'Urban Road': 'gold',
    'Unlabeled': 'white'
}

for zone_name, color in color_map.items():
    subset = df[df['environment_zone'] == zone_name]
    if not subset.empty:
        ax.scatter(subset['X'], subset['Y'], color=color, s=20, label=zone_name)

ax.set_title("Tokyo Expressway C1 - Interactive Map")
ax.set_xlabel("X Coordinate")
ax.set_ylabel("Y Coordinate")
ax.grid(True, alpha=0.2)
ax.legend(loc='upper right')

# --- INITIALIZE AT START LINE (t = 0s) ---
first_row = df.iloc[0]
car_marker, = ax.plot([first_row['X']], [first_row['Y']], 'ro', markersize=12, markeredgecolor='white', zorder=10)

initial_text = (f"Timestamp: {first_row['Timestamp']:.1f}s\n"
                f"Distance: {first_row['Distance_km']:.2f} km\n"
                f"Coords: X: {first_row['X']:.1f}, Y: {first_row['Y']:.1f}\n"
                f"Zone: {first_row['environment_zone']}")

info_box = ax.text(0.37, 0.98, initial_text, transform=ax.transAxes, 
                   color='white', fontsize=12, verticalalignment='top', 
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8, edgecolor='gray'))

is_dragging = False

def snap_to_route(mouse_x, mouse_y):
    dist, idx = kdtree.query([mouse_x, mouse_y])
    row = df.iloc[idx]
    
    car_marker.set_data([row['X']], [row['Y']])
    info_box.set_text(f"Timestamp: {row['Timestamp']:.1f}s\n"
                      f"Distance: {row['Distance_km']:.2f} km\n"
                      f"Coords: X: {row['X']:.1f}, Y: {row['Y']:.1f}\n"
                      f"Zone: {row['environment_zone']}")
    fig.canvas.draw_idle()

def on_press(event):
    global is_dragging
    if event.inaxes == ax:
        is_dragging = True
        snap_to_route(event.xdata, event.ydata)

def on_motion(event):
    if is_dragging and event.inaxes == ax:
        snap_to_route(event.xdata, event.ydata)

def on_release(event):
    global is_dragging
    is_dragging = False

fig.canvas.mpl_connect('button_press_event', on_press)
fig.canvas.mpl_connect('motion_notify_event', on_motion)
fig.canvas.mpl_connect('button_release_event', on_release)

plt.gca().invert_xaxis()
plt.show()