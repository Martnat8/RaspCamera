#!/usr/bin/env python3
from __future__ import annotations

import signal
import sys
import argparse
import time
from pathlib import Path

from gpiozero import DigitalInputDevice

from camera_utils import _run, ensure_dir, GPhotoError
from experiment_store import ExperimentStore

TRIGGER_GPIO = 17
ENABLE_GPIO  = 27
POLL_S = 0.005  # 5 ms polling

def cleanup_and_exit(signum=None, frame=None):
    print("\nStopping capture system...")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

def capture_to_path(out_path: Path, retries: int = 6) -> None:
    ensure_dir(out_path.parent)
    
    # 1. Use a unique, safe temporary filename that contains no risky characters
    tmp_path = out_path.with_name(f"gphoto_tmp_{int(time.time())}.jpg")
    
    try:
        _run(
            [
                "gphoto2",
                "--capture-image-and-download",
                "--force-overwrite",
                "--filename",
                str(tmp_path),  # Safe, controlled string passed to gphoto2
            ],
            retries=retries,
            timeout_s=90,
        )
        if not tmp_path.exists():
            raise GPhotoError(f"Capture reported success but temp file not found: {tmp_path}")
            
        # 2. Let Python safely rename it to your target DDMMYYYY_xxxxx.jpg format
        tmp_path.replace(out_path)
        
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise e

    if not out_path.exists():
        raise GPhotoError(f"Capture reported success but final file not found: {out_path}")


def get_interactive_inputs() -> tuple[str, str]:
    """Interactively prompts the user via the terminal for configuration settings."""
    print("\n" + "="*45)
    print("      CAMERA EXPERIMENT ENGINE CONFIG")
    print("="*45)
    
    # 1. Ask for Experiment Run Name
    exp_name = input("Enter Experiment Run Name [Default: ExpA]: ").strip()
    if not exp_name:
        exp_name = "ExpA"
        
    # 2. Ask for Run Mode (Resume or Restart)
    print("\nSelect Execution Mode:")
    print("  1) Resume (Continue tracking your latest run folder - DEFAULT)")
    print("  2) Restart (Wipe counters and establish a brand-new run folder)")
    
    choice = input("Choose option (1 or 2) [Default: 1]: ").strip()
    
    if choice == "2":
        run_mode = "restart"
    else:
        run_mode = "resume"
        
    # Construct the final base directory folder path mapping string
    base_directory = f"./experiments/{exp_name}"
    
    print("-"*45)
    print(f"Target Base Path: {base_directory}")
    print(f"Selected Mode:    {run_mode.upper()}")
    print("="*45 + "\n")
    
    return base_directory, run_mode


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    # Arguments changed to optional (default to None) to detect if CLI flags were skipped
    ap.add_argument("--base", default=None, help="Base experiment folder")
    ap.add_argument("--mode", choices=["resume", "restart"], default=None)
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    # If flags are omitted in the terminal, initiate the text menu prompts
    if args.base is None or args.mode is None:
        base_dir, run_mode = get_interactive_inputs()
    else:
        base_dir = args.base
        run_mode = args.mode

    store = ExperimentStore(base_dir, mode=run_mode)

    if run_mode == "resume":
        print(f"Current trigger count: {store.next_trigger_index}")
        update_ans = input("Do you need to update it? (y/n) [Default: n]: ").strip().lower()
        if update_ans in ("y", "yes"):
            while True:
                try:
                    new_count_str = input("Enter the trigger count number: ").strip()
                    if not new_count_str:
                        print("Invalid input: Cannot be empty.")
                        continue
                    new_count = int(new_count_str)
                    if new_count < 1:
                        print("Trigger count must be at least 1.")
                        continue
                    store.set_trigger_index(new_count)
                    print(f"Trigger count updated to: {store.next_trigger_index}")
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid integer number.")

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