import subprocess
from pathlib import Path
from datetime import datetime


def get_run_dir() -> Path:
    base = Path.home() / "pi_logs"
    run_date = datetime.now().strftime("%Y_%m_%d")
    run_dir = base / f"Run_{run_date}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def kill_gvfs_grabbers() -> tuple[bool, str]:
    try:
        subprocess.run(
            ["sudo", "killall", "gvfsd-gphoto2", "gvfs-gphoto2-volume-monitor"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True, "ok"
    except Exception as e:
        return False, str(e)


def capture_image_gphoto2(run_dir: Path, stem: str) -> tuple[bool, str, str]:
    """
    Canon EOS T3i known-good flow:
      - set capturetarget=0 (RAM)
      - set eosremoterelease=Immediate
      - wait for event and download in the SAME gphoto2 session
    Returns (ok, saved_filename, message).
    """
    # Do per-session setup (fast, and avoids state issues)
    subprocess.run(
        ["gphoto2", "--quiet", "--set-config", "capturetarget=0"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    subprocess.run(
        ["gphoto2", "--quiet", "--set-config", "eosremoterelease=Immediate"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    pattern = f"{stem}_%03n.%C"  # relative to run_dir (because we set cwd)
    cmd = [
        "gphoto2",
        "--wait-event-and-download=30s",
        "--filename", pattern,
        "--force-overwrite",
    ]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(run_dir),
        )

        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()

        if r.returncode != 0:
            combo = (err + "\n" + out).strip()
            return False, "", (combo[:400] if combo else f"gphoto2 failed rc={r.returncode}")

        # Find newest file that matches our stem
        matches = sorted(
            run_dir.glob(f"{stem}_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            combo = (out + "\n" + err).strip()
            return False, "", ("gphoto2 returned ok but no file found | " + (combo[:400] if combo else "no output"))

        return True, matches[0].name, "ok"

    except FileNotFoundError:
        return False, "", "gphoto2 not found (sudo apt install -y gphoto2)"
    except subprocess.TimeoutExpired:
        return False, "", "capture timeout"
