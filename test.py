#!/usr/bin/env python3
import time
from camera_utils import capture_image_and_download, camera_summary, GPhotoError

def main():
    print(camera_summary())
    try:
        while True:
            try:
                path = capture_image_and_download(out_dir="./photos", prefix="img", extension="jpg")
                print(f"Saved: {path}")
            except GPhotoError as e:
                print(f"[ERROR] {e}")
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
