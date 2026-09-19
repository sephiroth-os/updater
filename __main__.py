import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import psutil
import requests

INSTALL_DIR = Path(sys.executable).parent
APP_EXE = INSTALL_DIR / "SephirothOS.exe"

ROAMING_PATH = Path(os.getenv("APPDATA"))
UPDATE_JSON = ROAMING_PATH / "Oxygen" / "SephirothOS" / "config.json"

GITHUB_RELEASE = "https://api.github.com/repos/sephiroth-os/sephirothos/releases/latest"

def wait_for_process(pid):
    try:
        print("[updater]: Waiting for main app...")
        psutil.Process(pid).wait()
    except Exception:
        pass


def get_latest_zip_url():
    print("[updater]: Checking latest release...")

    r = requests.get(GITHUB_RELEASE)
    r.raise_for_status()

    release = r.json()

    assets = release.get("assets", [])

    for asset in assets:
        if asset["name"].lower().endswith(".zip"):
            print(f"[updater]: Found {asset['name']}")
            return asset["browser_download_url"]

    raise RuntimeError("No ZIP asset found in latest release.")


def download_update(url, output_file):
    print("[updater]: Downloading update...")

    r = requests.get(url, stream=True)
    r.raise_for_status()

    with open(output_file, "wb") as f:
        for chunk in r.iter_content(1024 * 64):
            if chunk:
                f.write(chunk)

    print("[updater]: Download complete.")


def extract_update(zip_path, destination):
    print("[updater]: Extracting...")

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destination)

    print("[updater]: Extraction complete.")


def copy_contents(src, dst):
    print("[updater]: Installing update...")

    src = Path(src)
    dst = Path(dst)

    for item in src.iterdir():

        target_name = item.name

        if item.name.lower() == "Updater.exe":
            target_name = "Updater.new.exe"

        target = dst / target_name

        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

    print("[updater]: Installation complete.")


def set_update_flag():
    if UPDATE_JSON.exists():
        with open(UPDATE_JSON, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data["update_in_progress"] = True

    with open(UPDATE_JSON, "w") as f:
        json.dump(data, f, indent=4)


def launch_app():
    print("[updater]: Launching application...")
    subprocess.Popen([str(APP_EXE)])

def main():

    if "--pid" not in sys.argv:
        print("[updater]: Missing --pid argument.")
        return

    try:
        pid = int(sys.argv[sys.argv.index("--pid") + 1])
    except Exception:
        print("[updater]: Invalid PID.")
        return

    wait_for_process(pid)

    try:
        with tempfile.TemporaryDirectory() as temp:

            temp = Path(temp)

            zip_file = temp / "update.zip"
            extract_dir = temp / "extract"

            url = get_latest_zip_url()

            download_update(url, zip_file)

            extract_update(zip_file, extract_dir)

            copy_contents(extract_dir, INSTALL_DIR)

        set_update_flag()

        print(APP_EXE.exists())
        print(APP_EXE.stat().st_mtime)

        launch_app()

        print("[updater]: Update completed successfully.")

    except Exception as e:
        print(f"[updater]: Update failed: {e}")

        if APP_EXE.exists():
            launch_app()


if __name__ == "__main__":
    main()