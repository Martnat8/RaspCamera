import time
import csv
from pathlib import Path
from gpiozero import Button
from datetime import datetime

# BCM numbering
TRIGGER_GPIO = 17
ENABLE_GPIO  = 27

BASE_LOG_DIR = Path.home() / "pi_logs"
RUN_DATE = datetime.now().strftime("%Y_%m_%d")

RUN_DIR = BASE_LOG_DIR / f"Run_{RUN_DATE}"
LOG_FILE = RUN_DIR / f"trigger_log_{RUN_DATE}.csv"


def setup_log():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "elapsed_s", "enable"])


def main():
    setup_log()

    trigger = Button(TRIGGER_GPIO, pull_up=False, bounce_time=0.05)
    enable  = Button(ENABLE_GPIO,  pull_up=False)

    t0 = time.monotonic()
    idx = 0

    print("Pi trigger listener running")
    print(f"Trigger: GPIO {TRIGGER_GPIO}")
    print(f"Enable : GPIO {ENABLE_GPIO}")

    while True:
        trigger.wait_for_press()   # rising edge
        trigger.wait_for_release()

        if not enable.is_pressed:
            continue

        idx += 1
        elapsed = time.monotonic() - t0
        en = int(enable.is_pressed)

        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([idx, f"{elapsed:.6f}", en])

        print(f"#{idx}  t={elapsed:.3f}s  enable={en}")

if __name__ == "__main__":
    main()
