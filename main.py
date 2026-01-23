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


def capture_image(run_dir: Path, stem: str) -> tuple[bool, str, str]:
    """
    One-call Canon capture:
      - trigger shutter
      - wait for file event and download
    Returns (ok, saved_filename, message).
    """
    # %C = camera-chosen extension (jpg/JPG/CR2/etc), %03n = unique numbering
    pattern = run_dir / f"{stem}_%03n.%C"

    cmd = [
        "gphoto2",
        "--set-config", "eosremoterelease=Immediate",
        "--wait-event-and-download=15s",
        "--filename", str(pattern),
        "--force-overwrite",
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip()
            return False, "", (msg[:200] if msg else f"gphoto2 failed rc={r.returncode}")

        # Find newest file matching this stem
        matches = sorted(
            run_dir.glob(f"{stem}_*.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            return False, "", "gphoto2 returned ok but no file found"

        return True, matches[0].name, "ok"

    except FileNotFoundError:
        return False, "", "gphoto2 not found (sudo apt install -y gphoto2)"
    except subprocess.TimeoutExpired:
        return False, "", "capture timeout"


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

        # If capture failed, still log the intended pattern for traceability
        image_label = saved_name if ok else f"{image_stem}_%03n.%C"

        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([idx, f"{elapsed:.6f}", en, image_label, int(ok), msg])

        print(f"#{idx}  t={elapsed:.3f}s  enable={en}  file={image_label}  ok={ok}  msg={msg}")


if __name__ == "__main__":
    main()
