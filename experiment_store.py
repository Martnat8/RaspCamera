#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


RUN_DIR_RE = re.compile(r"^Run_(\d{8})_(\d{6})$")  # Run_YYYYMMDD_HHMMSS


@dataclass
class TriggerLogRow:
    timestamp: str
    trigger_index: int
    enable_state: int
    captured: int
    filename: str  # empty if not captured


class ExperimentStore:
    """
    Owns experiment run folder creation/resume, counters, and CSV logging.
    Images are stored under run_dir/photos/.

    - image_count increments only on successful capture
    - trigger_index increments on every trigger rising edge (even if enable=0)
    """

    def __init__(self, base_dir: str | Path, mode: str = "resume") -> None:
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.mode = mode.lower().strip()
        if self.mode not in ("resume", "restart"):
            raise ValueError("mode must be 'resume' or 'restart'")

        self.run_dir: Path
        self.photos_dir: Path
        self.log_csv: Path
        self.state_json: Path

        # Next indices (persisted)
        self.next_image_count: int = 1
        self.next_trigger_index: int = 1

        self._init_run_dir()
        self._init_paths()
        self._load_or_init_state()
        self._init_csv_header()

    # ---------- public API ----------

    def allocate_trigger(self, enable_state: bool) -> tuple[int, int]:
        """
        Called once per rising edge.
        Returns (trigger_index_for_this_event, enable_state_int).
        Always increments trigger_index for the event.
        """
        ti = self.next_trigger_index
        self.next_trigger_index += 1
        self._save_state()
        return ti, 1 if enable_state else 0

    def next_image_path(self) -> tuple[Path, int]:
        """
        Returns (path_for_next_image, image_index_used).
        Does NOT increment until commit_capture_success().
        """
        date_str = datetime.now().strftime("%d%m%Y")  # DDMMYYYY
        idx = self.next_image_count
        filename = f"{date_str}_{idx:05d}.jpg"
        return (self.photos_dir / filename), idx

    def commit_capture_success(self) -> None:
        """Increment image counter and persist."""
        self.next_image_count += 1
        self._save_state()

    def log_trigger_result(
        self,
        *,
        trigger_index: int,
        enable_state_int: int,
        captured: bool,
        filename: str = "",
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Append one row to log.csv for each trigger.
        filename should be "" if not captured.
        """
        ts = timestamp or datetime.now().isoformat(timespec="milliseconds")
        row = TriggerLogRow(
            timestamp=ts,
            trigger_index=trigger_index,
            enable_state=enable_state_int,
            captured=1 if captured else 0,
            filename=filename if captured else "",
        )
        line = f"{row.timestamp},{row.trigger_index},{row.enable_state},{row.captured},{row.filename}\n"
        with self.log_csv.open("a", encoding="utf-8", newline="") as f:
            f.write(line)
            f.flush()

    # ---------- init helpers ----------

    def _init_run_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "restart":
            self.run_dir = self._create_new_run_dir()
            return

        # resume mode
        latest = self._find_latest_run_dir()
        if latest is None:
            # Your chosen behavior (B): create new run if none exists
            self.run_dir = self._create_new_run_dir()
        else:
            self.run_dir = latest

    def _init_paths(self) -> None:
        self.photos_dir = self.run_dir / "photos"
        self.log_csv = self.run_dir / "log.csv"
        self.state_json = self.run_dir / "state.json"
        self.photos_dir.mkdir(parents=True, exist_ok=True)

    def _init_csv_header(self) -> None:
        if not self.log_csv.exists():
            with self.log_csv.open("w", encoding="utf-8", newline="") as f:
                f.write("timestamp,trigger_index,enable_state,captured,filename\n")
                f.flush()

    def _load_or_init_state(self) -> None:
        if self.mode == "restart":
            self.next_image_count = 1
            self.next_trigger_index = 1
            self._save_state()
            return

        # resume mode: try state.json, else fallback
        if self.state_json.exists():
            try:
                data = json.loads(self.state_json.read_text(encoding="utf-8"))
                self.next_image_count = int(data.get("next_image_count", 1))
                self.next_trigger_index = int(data.get("next_trigger_index", 1))
                if self.next_image_count < 1:
                    self.next_image_count = 1
                if self.next_trigger_index < 1:
                    self.next_trigger_index = 1
                return
            except Exception:
                # fall through to rebuild
                pass

        # Fallback rebuild if state is missing/corrupt
        self.next_image_count = self._infer_next_image_count()
        self.next_trigger_index = self._infer_next_trigger_index()
        self._save_state()

    def _save_state(self) -> None:
        data = {
            "next_image_count": self.next_image_count,
            "next_trigger_index": self.next_trigger_index,
            "run_dir": str(self.run_dir),
            "updated": datetime.now().isoformat(timespec="seconds"),
        }
        tmp = self.state_json.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.state_json)

    # ---------- fallback inference ----------

    def _infer_next_image_count(self) -> int:
        # Look for DDMMYYYY_00001.jpg -> extract last 5-digit number
        max_idx = 0
        for p in self.photos_dir.glob("*.jpg"):
            m = re.search(r"_(\d{5})\.jpg$", p.name)
            if m:
                max_idx = max(max_idx, int(m.group(1)))
        return max_idx + 1 if max_idx > 0 else 1

    def _infer_next_trigger_index(self) -> int:
        if not self.log_csv.exists():
            return 1
        try:
            # Read last non-header line
            lines = self.log_csv.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines):
                if line.startswith("timestamp,"):
                    break
                parts = line.split(",")
                if len(parts) >= 2 and parts[1].isdigit():
                    last = int(parts[1])
                    return last + 1
        except Exception:
            pass
        return 1

    # ---------- run folder selection ----------

    def _create_new_run_dir(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = self.base_dir / f"Run_{ts}"
        run.mkdir(parents=True, exist_ok=False)
        return run

    def _find_latest_run_dir(self) -> Optional[Path]:
        candidates: list[Path] = []
        for p in self.base_dir.iterdir():
            if p.is_dir() and RUN_DIR_RE.match(p.name):
                candidates.append(p)
        if not candidates:
            return None
        # Most reliable: pick by mtime
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]
