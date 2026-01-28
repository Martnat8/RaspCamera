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
            # backoff and retry
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
        if any(m.lower() in stderr.lower() for m in transient_markers) or any(
            m.lower() in stdout.lower() for m in transient_markers
        ):
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
