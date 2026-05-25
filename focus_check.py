#!/usr/bin/env python3
import os
import time
import threading
import subprocess
from pathlib import Path

def capture_loop(target_path):
    print("📸 Automated Focus Loop Started!")
    print("--------------------------------------------------")
    print(f"🌐 Server is live. Go to: http://10.0.0.158:8000/latest_focus.jpg")
    print("Stand at your camera, adjust your lens, and refresh your browser.")
    print("Press Ctrl+C in this terminal window to stop the loop.")
    print("--------------------------------------------------\n")
    
    try:
        while True:
            print(f"[{time.strftime('%H:%M:%S')}] Capturing frame...")
            # Capture and force overwrite latest_focus.jpg
            res = os.system(f"gphoto2 --capture-image-and-download --force-overwrite --filename {target_path} > /dev/null 2>&1")
            
            if res == 0:
                print(f"[{time.strftime('%H:%M:%S')}] ✅ Frame updated. (Ready to refresh browser)")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Capture failed. (Camera busy or disconnected)")
            
            # 2 second cooldown
            time.sleep(2)
            
    except KeyboardInterrupt:
        pass

def main():
    target_path = Path("./latest_focus.jpg").resolve()
    
    # Start the HTTP server in a background thread so it doesn't block our loop
    server = subprocess.Popen(["python3", "-m", "http.server", "8000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    try:
        # Start the repeating capture sequence
        capture_loop(target_path)
    except KeyboardInterrupt:
        print("\nStopping focus loop...")
    finally:
        # Clean up and shut down the background web server when done
        server.terminate()
        print("Focus check server stopped.")

if __name__ == "__main__":
    main()
