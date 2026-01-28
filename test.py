from camera_utils import get_run_dir, capture_image_gphoto2, kill_gvfs_grabbers


def main():
    run_dir = get_run_dir()
    stem = "test"

    print(f"Run dir: {run_dir}")

    ok, msg = kill_gvfs_grabbers()
    if not ok:
        print(f"(warn) gvfs kill failed: {msg}")

    print("Triggering capture...")
    ok, saved, msg = capture_image_gphoto2(run_dir, stem)

    print(f"ok={ok}")
    print(f"saved={saved}")
    print(f"msg={msg}")

    if ok:
        print(f"Saved to: {run_dir / saved}")


if __name__ == "__main__":
    main()
