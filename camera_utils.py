import csv
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Tuple


def get_run_date() -> str:
    return datetime.now().strftime("%Y_%m_%d")


def get_run_dir(base_dir: Path | None = None) -> Path:
    base = base_dir if base_dir is not None else (Path.home() / "pi_logs")
    run_dir = base / f"Run_{get_run_date()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def get_log_file(run_dir: Path) -> Path:
    run_date = get_run_date()
    return run_dir / f"trigger_log_{run_date}.csv"


def init_log(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        with open(log_file, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["index", "elapsed_s", "enable", "image_file", "capture_ok", "capture_msg"])


def append_log_row(log_file: Path, row: list) -> None:
    with open(log_file, "a", newline="") as f:
        csv.writer(f).writerow(row)


def kill_gvfs_grabbers() -> Tuple[bool, str]:
    """
    Optional helper. Safe to call even if those processes aren't running.
    """
    cmd = ["sudo", "killall", "gvfsd-gphoto2", "gvfs-gphoto2-volume-monitor"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        # killall returns nonzero if nothing was killed; that's fine
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _find_newest_matching(run_dir: Path, stem: str) -> Path | None:
    matches = sorted(
        run_dir.glob(f"{stem}_*.*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def capture_image_gphoto2(run_dir: Path, stem: str) -> tuple[bool, str, str]:
    """
    Canon-stable capture in ONE gphoto2 call:
      - eosremoterelease=Immediate
      - wait-event-and-download
    Returns (ok, saved_filename, message).
    """
    pattern = run_dir / f"{stem}_%03n.%C"  # %C = correct extension, %03n = unique numbering

    cmd = [
        "gphoto2",
        "--set-config", "eosremoterelease=Immediate",
        "--wait-event-and-download=15s",
        "--filename", str(pattern),
        "--force-overwrite",
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip()
            return False, "", (msg[:200] if msg else f"gphoto2 failed rc={r.returncode}")

        newest = _find_newest_matching(run_dir, stem)
        if newest is None:
            return False, "", "gphoto2 returned ok but no file found"

        return True, newest.name, "ok"

    except FileNotFoundError:
        return False, "", "gphoto2 not found (sudo apt install -y gphoto2)"
    except subprocess.TimeoutExpired:
        return False, "", "capture timeout"


# ---- Tiny standalone test you can run independently ----
def test_capture_once() -> None:
    run_dir = get_run_dir()
    log_file = get_log_file(run_dir)
    init_log(log_file)

    ok, saved, msg = capture_image_gphoto2(run_dir, "manual_test")
    print(f"capture ok={ok} saved={saved} msg={msg}")
