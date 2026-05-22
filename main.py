#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

from gpiozero import DigitalInputDevice

from camera_utils import _run, ensure_dir, GPhotoError
from experiment_store import ExperimentStore

TRIGGER_GPIO = 17
ENABLE_GPIO  = 27
POLL_S = 0.005  # 5 ms polling


def capture_to_path(out_path: Path, retries: int = 6) -> None:
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


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Base experiment folder (run folder will be created inside)")
    ap.add_argument("--mode", choices=["resume", "restart"], default="resume")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    store = ExperimentStore(args.base, mode=args.mode)
    print(f"Run folder: {store.run_dir}")
    print(f"Photos:     {store.photos_dir}")
    print(f"Log:        {store.log_csv}")
    print(f"State:      {store.state_json}")

    enable = DigitalInputDevice(ENABLE_GPIO, pull_up=False)
    trigger = DigitalInputDevice(TRIGGER_GPIO, pull_up=False)

    armed = True
    prev_trigger = trigger.value

    print(f"READY. Enable=GPIO{ENABLE_GPIO}, Trigger=GPIO{TRIGGER_GPIO}")

    try:
        while True:
            en = bool(enable.value)
            tr = bool(trigger.value)
            rising = (not prev_trigger) and tr

            if armed and rising:
                trigger_index, en_int = store.allocate_trigger(en)

                if en:
                    out_path, img_idx = store.next_image_path()
                    try:
                        capture_to_path(out_path)
                        store.commit_capture_success()
                        store.log_trigger_result(
                            trigger_index=trigger_index,
                            enable_state_int=en_int,
                            captured=True,
                            filename=out_path.name,
                        )
                        print(f"Trig {trigger_index}: Captured {out_path.name}")
                    except GPhotoError as e:
                        store.log_trigger_result(
                            trigger_index=trigger_index,
                            enable_state_int=en_int,
                            captured=False,
                            filename="",
                        )
                        print(f"[ERROR] Trig {trigger_index}: capture failed: {e}")
                else:
                    store.log_trigger_result(
                        trigger_index=trigger_index,
                        enable_state_int=en_int,
                        captured=False,
                        filename="",
                    )
                    print(f"Trig {trigger_index}: ignored (ENABLE low)")

                # require trigger to fall low before accepting another
                armed = False

            if not armed and (not tr):
                armed = True

            prev_trigger = tr
            time.sleep(POLL_S)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
