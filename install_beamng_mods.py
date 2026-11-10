"""
One-Click BeamNG Study Installer / Sync Script
===============================================
Copies the repository's custom BeamNG files into the local BeamNG user folder
(%LOCALAPPDATA%\\BeamNG\\BeamNG.drive\\current\\):
  1. levels/c1/                        -> Custom Tokyo C1 course barriers & finish line
  2. vehicles/bastion/                 -> Bruckell Bastion live gauge toggle ('G' key)
  3. lua/vehicle/protocols/userStudy.lua -> 10Hz UDP telemetry sender (port 64256)
  4. Enables "protocols_others_enabled": true in settings/settings.json
"""

import os
import json
import shutil
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parent
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        print("[Error] LOCALAPPDATA environment variable not found.")
        return

    beamng_user_dir = Path(local_appdata) / "BeamNG" / "BeamNG.drive" / "current"
    if not beamng_user_dir.exists():
        print(f"[Warning] BeamNG user folder not found at: {beamng_user_dir}")
        print("Creating directory structure...")
        beamng_user_dir.mkdir(parents=True, exist_ok=True)

    folders_to_sync = ["levels", "vehicles", "lua"]
    for folder in folders_to_sync:
        src = repo_root / folder
        dst = beamng_user_dir / folder
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"[OK] Synced '{folder}/' -> {dst}")

    # Ensure protocols_others_enabled is true in settings/settings.json
    settings_path = beamng_user_dir / "settings" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_data = {}
    if settings_path.exists():
        try:
            settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            settings_data = {}

    if not settings_data.get("protocols_others_enabled"):
        settings_data["protocols_others_enabled"] = True
        settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")
        print(f"[OK] Enabled 'protocols_others_enabled' in {settings_path}")
    else:
        print(f"[OK] 'protocols_others_enabled' already enabled in {settings_path}")

    print("\nAll BeamNG study files are installed! If BeamNG is currently running, press Ctrl+L then Ctrl+R in-game.")


if __name__ == "__main__":
    main()
