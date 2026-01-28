#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

PHOTOS_DIR = Path("./photos").resolve()
MIN_FREE_GB = 2.0  # change if you want


def run(cmd: list[str], *, check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def pkill(pattern: str) -> None:
    # pkill returns nonzero if nothing matched; that's fine
    subprocess.run(["pkill", "-f", pattern], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def free_gb(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)


def main() -> int:
    print("== Camera startup prep ==")

    # 1) Ensure output directory exists
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Photos dir: {PHOTOS_DIR}")

    # 2) Disk space check
    gb = free_gb(PHOTOS_DIR)
    print(f"[OK] Free disk: {gb:.2f} GB")
    if gb < MIN_FREE_GB:
        print(f"[FAIL] Not enough free space (< {MIN_FREE_GB} GB).")
        return 2

    # 3) Kill common grabbers that steal USB interface 0
    # (safe to run even if they aren't present)
    for pat in ("gvfsd-gphoto2", "gvfs-gphoto2-volume-monitor", "gphoto2"):
        pkill(pat)

    # Give USB a moment to settle after killing processes
    time.sleep(0.3)

    # 4) Verify camera is claimable and responsive
    try:
        p = run(["gphoto2", "--summary"], check=False, timeout=30)
    except FileNotFoundError:
        print("[FAIL] gphoto2 not found. Install with: sudo apt install -y gphoto2")
        return 3
    except subprocess.TimeoutExpired:
        print("[FAIL] gphoto2 --summary timed out. Camera may be asleep/busy/disconnected.")
        return 4

    if p.returncode != 0:
        err = (p.stderr or "").strip()
        print("[FAIL] gphoto2 --summary failed:")
        print(err if err else p.stdout)
        print("\nCommon fixes:")
        print("- Ensure camera is ON and USB cable is good")
        print("- Kill grabbers again: pkill -f gvfsd-gphoto2 ; pkill -f gvfs-gphoto2-volume-monitor")
        print("- Unplug/replug USB or power-cycle camera")
        return 5

    print("[OK] gphoto2 --summary succeeded")
    # Optional: print a short snippet so you can see it’s the right camera
    summary_lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    for ln in summary_lines[:8]:
        print("   " + ln)

    print("\nREADY: safe to start long run (e.g., python3 test.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
