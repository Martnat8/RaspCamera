#!/usr/bin/env python3
import subprocess
import time
from pathlib import Path
from camera_utils import _run, GPhotoError

def main():
    target_path = Path("./latest_focus.jpg").resolve()
    print("📸 Initializing focus check capture...")
    print("Please ensure main.py is paused so the USB port is free.")
    
    # 1. Capture a crisp, full-res image to a fixed location
    try:
        _run([
            "gphoto2",
            "--capture-image-and-download",
            "--force-overwrite",
            "--filename",
            str(target_path)
        ], retries=3, timeout_s=30)
        
        print(f"✅ Photo captured successfully to: {target_path}")
        print("\n🌐 Starting temporary image server...")
        print(f"Open your browser and go to: http://<your-pi-ip>:8000/latest_focus.jpg")
        print("Press Ctrl+C to close the server when you are done focusing.")
        
        # 2. Host a quick local server to view the exact file immediately
        subprocess.run(["python3", "-m", "http.server", "8000"])
        
    except GPhotoError as e:
        print(f"❌ Failed to capture check image: {e}")
    except KeyboardInterrupt:
        print("\nFocus check server stopped.")

if __name__ == "__main__":
    main()