#!/usr/bin/env python3
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from gpiozero import DigitalInputDevice

from camera_utils import _run, ensure_dir, GPhotoError

TRIGGER_GPIO = 17
ENABLE_GPIO  = 27

PHOTOS_DIR = Path("./photos").resolve()
POLL_S = 0.005  # 5 ms polling


def capture_to_filename(out_path: Path, retries: int = 6) -> None:
    """
    Capture + download directly to out_path using gphoto2, with retries via camera_utils._run().
    """
    ensure_dir(out_path.parent)

    _run(
        [
            "gphoto2",
            "--capture-image-and-download",
            "--force-overwrite",
            "--filename",
            str(out_path),
        ],
        retries=retries,
        timeout_s=90,
    )

    if not out_path.exists():
        raise GPhotoError(f"Capture reported success but file not found: {out_path}")


def main() -> None:
    ensure_dir(PHOTOS_DIR)

    # Inputs with pull-downs: OFF=0, ON=1.
    # If your wiring already has external pull resistors, set pull_up=None.
    enable = DigitalInputDevice(ENABLE_GPIO, pull_up=False)
    trigger = DigitalInputDevice(TRIGGER_GPIO, pull_up=False)

    # Counter starts at 1 each run (simple). If you want persistence across reboots,
    # tell me and I'll add a tiny counter file.
    count = 1

    # Edge/re-arm logic
    armed = True
    prev_trigger = trigger.value

    print(f"READY. Enable=GPIO{ENABLE_GPIO}, Trigger=GPIO{TRIGGER_GPIO}")
    print(f"Saving to: {PHOTOS_DIR}")

    try:
        while True:
            en = enable.value
            tr = trigger.value

            # Rising edge detection: prev 0 -> current 1
            rising = (not prev_trigger) and tr

            if armed and rising:
                if en:
                    date_str = datetime.now().strftime("%d%m%Y")
                    filename = f"{date_str}_{count:05d}.jpg"
                    out_path = PHOTOS_DIR / filename

                    try:
                        capture_to_filename(out_path)
                        print(f"Captured: {out_path}")
                        count += 1
                    except GPhotoError as e:
                        print(f"[ERROR] capture failed: {e}")
                        # Do NOT increment count on failure
                else:
                    # Enable is off: ignore this trigger, do not increment
                    print("Trigger ignored (ENABLE low)")

                # Regardless of enable, require trigger to go LOW before re-arming
                armed = False

            # Re-arm only after we see the falling edge / trigger low again
            if not armed and (not tr):
                armed = True

            prev_trigger = tr
            time.sleep(POLL_S)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
