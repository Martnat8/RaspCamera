#!/usr/bin/env python3
"""
Minimal gphoto2 helpers for Canon EOS (e.g., T3i) on headless Linux/RPi.

Assumes:
- gphoto2 is installed and in PATH
- camera is connected via USB and powered on
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence


class GPhotoError(RuntimeError):
    pass


def find_canon_usb_path() -> Optional[Path]:
    """
    Search /sys/bus/usb/devices/ for a device with Canon's Vendor ID (04a9).
    Returns the Path to the raw device file, e.g. /dev/bus/usb/001/004, or None.
    """
    base_sys_path = Path("/sys/bus/usb/devices")
    if not base_sys_path.exists():
        return None

    for dev_dir in base_sys_path.iterdir():
        vendor_file = dev_dir / "idVendor"
        if not vendor_file.exists():
            continue
        try:
            vendor_id = vendor_file.read_text(encoding="utf-8").strip()
            if vendor_id.lower() == "04a9":
                bus_file = dev_dir / "busnum"
                dev_file = dev_dir / "devnum"
                if bus_file.exists() and dev_file.exists():
                    bus_num = int(bus_file.read_text(encoding="utf-8").strip())
                    dev_num = int(dev_file.read_text(encoding="utf-8").strip())
                    dev_path = Path(f"/dev/bus/usb/{bus_num:03d}/{dev_num:03d}")
                    if dev_path.exists():
                        return dev_path
        except Exception:
            pass
    return None


def reset_canon_usb() -> bool:
    """
    Locates the connected Canon camera on the USB bus and sends a low-level
    reset signal (USBDEVFS_RESET) to reboot its USB interface.
    Returns True if reset was successfully sent, False otherwise.
    """
    try:
        import fcntl
    except ImportError:
        return False

    dev_path = find_canon_usb_path()
    if not dev_path:
        return False

    try:
        USBDEVFS_RESET = 21780
        with open(dev_path, "wb") as f:
            fcntl.ioctl(f.fileno(), USBDEVFS_RESET, 0)
        return True
    except Exception:
        return False


def _run(
    cmd: Sequence[str],
    *,
    retries: int = 6,
    base_delay_s: float = 0.25,
    timeout_s: int = 60,
) -> str:
    """
    Run a command with retries for common transient camera errors.
    Returns stdout on success, raises GPhotoError on failure.
    """
    last_err = ""
    for i in range(retries):
        try:
            p = subprocess.run(
                list(cmd),
                text=True,
                capture_output=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as e:
            last_err = f"TimeoutExpired: {e}"
            # If command keeps timing out, attempt low-level USB reset
            if i >= 1:
                print(f"[WARN] Command timeout (attempt {i+1}/{retries}). Attempting automated low-level Canon USB reset...")
                if reset_canon_usb():
                    print("[INFO] USB reset signal sent successfully. Waiting 2.0 seconds for camera to re-handshake...")
                    time.sleep(2.0)
            time.sleep(base_delay_s * (i + 1))
            continue

        if p.returncode == 0:
            return p.stdout

        stderr = (p.stderr or "").strip()
        stdout = (p.stdout or "").strip()
        last_err = f"rc={p.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

        # Heuristics: retry on common transient errors
        transient_markers = (
            "Camera busy",
            "PTP I/O error",
            "Could not claim the USB device",
            "Resource busy",
            "I/O in progress",
            "Device Busy",
        )
        combined_output = (stderr + "\n" + stdout).lower()
        if any(m.lower() in combined_output for m in transient_markers):
            # If on the 2nd attempt or later (i >= 1) and the error contains hard disconnect signals,
            # or if on the 3rd attempt or later (i >= 2) for any transient error, try resetting USB.
            is_hard_error = any(m in combined_output for m in ("ptp i/o error", "could not claim"))
            if (is_hard_error and i >= 1) or (i >= 2):
                print(f"[WARN] Connection issue detected (attempt {i+1}/{retries}). Attempting automated low-level Canon USB reset...")
                if reset_canon_usb():
                    print("[INFO] USB reset signal sent successfully. Waiting 2.0 seconds for camera to re-handshake...")
                    time.sleep(2.0)
                else:
                    print("[WARN] Could not reset Canon USB device (may not be connected or permission denied).")

            time.sleep(base_delay_s * (i + 1))
            continue

        # Non-transient error -> fail fast
        raise GPhotoError(f"Command failed: {' '.join(cmd)}\n{last_err}")

    raise GPhotoError(f"Command failed after retries: {' '.join(cmd)}\n{last_err}")


def ensure_dir(path: str | os.PathLike) -> Path:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def capture_image_and_download(
    *,
    out_dir: str | os.PathLike = "./photos",
    prefix: str = "img",
    extension: str = "jpg",
    retries: int = 6,
) -> Path:
    """
    Captures an image and downloads it directly to out_dir.

    Returns the saved file path.
    """
    out_dir_p = ensure_dir(out_dir)

    # Use a concrete filename so Python knows exactly where the file will land.
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{prefix}-{ts}.{extension}"
    out_path = out_dir_p / filename

    # Canon EOS capture path (works even though summary says "No Image Capture").
    _run(
        [
            "gphoto2",
            "--capture-image-and-download",
            "--force-overwrite",
            "--filename",
            str(out_path),
        ],
        retries=retries,
    )

    if not out_path.exists():
        raise GPhotoError(f"gphoto2 reported success but file not found: {out_path}")

    return out_path


def camera_summary() -> str:
    """Convenience helper to confirm camera connectivity."""
    return _run(["gphoto2", "--summary"], retries=2, timeout_s=30)
