#!/usr/bin/env python3
import time
from camera_utils import capture_image_and_download, camera_summary, GPhotoError


def main():
    # Optional: prints summary once so you know it’s connected
    print(camera_summary())

    while True:
        try:
            path = capture_image_and_download(out_dir="./photos", prefix="img", extension="jpg")
            print(f"Saved: {path}")
        except GPhotoError as e:
            print(f"[ERROR] {e}")

        time.sleep(3)


if __name__ == "__main__":
    main()
