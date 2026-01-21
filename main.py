import time
import csv
from pathlib import Path
from gpiozero import Button

# BCM numbering
TRIGGER_GPIO = 17
ENABLE_GPIO  = 27

LOG_DIR = Path.home() / "pi_logs"
LOG_FILE = LOG_DIR / "trigger_log.csv"

def setup_log():
    LOG_DIR.mkdir(exist_ok=True)
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
        idx += 1
        elapsed = time.monotonic() - t0
        en = int(enable.is_pressed)

        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([idx, f"{elapsed:.6f}", en])

        print(f"#{idx}  t={elapsed:.3f}s  enable={en}")

if __name__ == "__main__":
    main()
