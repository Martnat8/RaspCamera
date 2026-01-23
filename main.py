import time
import csv
import subprocess
from pathlib import Path
from gpiozero import Button
from datetime import datetime

# BCM numbering
TRIGGER_GPIO = 17
ENABLE_GPIO  = 27

# Date-based run folder
BASE_LOG_DIR = Path.home() / "pi_logs"
RUN_DATE = datetime.now().strftime("%Y_%m_%d")
RUN_DIR = BASE_LOG_DIR / f"Run_{RUN_DATE}"

# Log file inside run folder (one per day)
LOG_FILE = RUN_DIR / f"trigger_log_{RUN_DATE}.csv"

def setup_log():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "elapsed_s", "enable", "image_file", "capture_ok", "capture_msg"])

def capture_image(save_path: Path) -> tuple[bool, str]:
    """
    Canon-stable capture:
      1) trigger shutter via eosremoterelease
      2) wait for file event and download to save_path
    Returns (ok, message).
    """
    # (optional but helps) capture to RAM so download is immediate
    set_target = ["gphoto2", "--quiet", "--set-config", "capturetarget=0"]

    trigger = ["gphoto2", "--quiet", "--set-config", "eosremoterelease=Immediate"]

    download = [
        "gphoto2",
        "--quiet",
        "--wait-event-and-download=10s",
        "--filename", str(save_path),
        "--force-overwrite",
    ]

    try:
        # Don't fail the whole capture if capturetarget isn't supported
        subprocess.run(set_target, capture_output=True, text=True, timeout=10)

        r1 = subprocess.run(trigger, capture_output=True, text=True, timeout=20)
        if r1.returncode != 0:
            msg = (r1.stderr or r1.stdout or "").strip()
            return False, (msg[:200] if msg else f"trigger failed rc={r1.returncode}")

        r2 = subprocess.run(download, capture_output=True, text=True, timeout=30)
        if r2.returncode != 0:
            msg = (r2.stderr or r2.stdout or "").strip()
            return False, (msg[:200] if msg else f"download failed rc={r2.returncode}")

        # sanity: ensure file exists
        if not save_path.exists():
            return False, "download reported ok but file missing"

        return True, "ok"

    except FileNotFoundError:
        return False, "gphoto2 not found (install with: sudo apt install -y gphoto2)"
    except subprocess.TimeoutExpired:
        return False, "capture timeout"


def main():
    setup_log()

    trigger = Button(TRIGGER_GPIO, pull_up=False, bounce_time=0.05)
    enable  = Button(ENABLE_GPIO,  pull_up=False)

    t0 = time.monotonic()
    idx = 0

    print("Pi trigger listener running")
    print(f"Trigger: GPIO {TRIGGER_GPIO}")
    print(f"Enable : GPIO {ENABLE_GPIO}")
    print(f"Run dir: {RUN_DIR}")
    print(f"Log    : {LOG_FILE}")

    while True:
        trigger.wait_for_press()
        trigger.wait_for_release()

        if not enable.is_pressed:
            continue

        idx += 1
        elapsed = time.monotonic() - t0
        en = int(enable.is_pressed)

        image_stem = f"img_{idx:06d}"

        ok, saved_name, msg = capture_image(RUN_DIR, image_stem)

        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([idx, f"{elapsed:.6f}", en, saved_name, int(ok), msg])

        print(f"#{idx}  t={elapsed:.3f}s  enable={en}  file={saved_name}  ok={ok}  msg={msg}")



if __name__ == "__main__":
    main()
