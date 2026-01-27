# test.py
#
# Run from the same folder as camera_utils.py:
#   python3 test.py
#
# This uses your shared helpers in camera_utils.py to:
#   - create today's Run_YYYY_MM_DD folder under ~/pi_logs
#   - (optionally) kill gvfs camera grabbers
#   - trigger one capture via gphoto2
#   - print the saved filename (or error)

from camera_utils import (
    get_run_dir,
    capture_image_gphoto2,
    kill_gvfs_grabbers,
)


def main():
    run_dir = get_run_dir()
    stem = "test_capture"

    print(f"Run dir: {run_dir}")

    # Optional but helpful if the desktop keeps grabbing the camera
    ok, msg = kill_gvfs_grabbers()
    if not ok:
        print(f"(warn) gvfs kill failed: {msg}")

    print("Triggering capture...")
    ok, saved, msg = capture_image_gphoto2(run_dir, stem)

    print(f"ok={ok}")
    print(f"saved={saved}")
    print(f"msg={msg}")

    if ok and saved:
        print(f"Saved to: {run_dir / saved}")


if __name__ == "__main__":
    main()
