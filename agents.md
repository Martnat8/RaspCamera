# AI Agent Guide for RaspCamera

This document serves as an instruction manual and reference for AI agents (and human developers) when interacting with, modifying, or refactoring the RaspCamera codebase.

---

## System Overview

The RaspCamera system is a crash-resilient, GPIO-triggered image capture utility designed for long-running scientific experiments. It runs on a Raspberry Pi (validated on Raspberry Pi 5 under OS Bookworm) and controls a Canon EOS Rebel T3i (600D) via the `gphoto2` CLI.

---

## Architectural Principles & Constraints

Any modifications or features proposed must adhere to the following core engineering choices:

### 1. No Persistent Camera Control Libraries
- **Principle**: The system executes raw, ephemeral CLI subprocesses for `gphoto2` operations rather than maintaining a persistent socket or using python bindings (e.g., `python-gphoto2`).
- **Reasoning**: Stateful SDKs and connection-oriented wrappers often leak system file descriptors or memory during extremely long-running experiments (e.g., multiple days or weeks). Running gphoto2 as a distinct, short-lived process ensures that the OS cleans up all USB/driver resources immediately after each operation.
- **Constraint**: Do not refactor the code to use persistent background camera-monitoring libraries unless explicitly requested.

### 2. File-System Resilience & Atomic Updates
- **Principle**: Critical state data (`state.json`) and camera image files must never be corrupted by a sudden power loss, system crash, or manual termination.
- **Reasoning**: A direct write can leave a half-written file if the script is interrupted.
- **Implementation**:
  - Image files are first captured to a unique, timestamp-based temporary file name in the target directory (e.g., `gphoto_tmp_1700000000.jpg`).
  - Once written successfully, Python atomically renames the temporary file to its final destination (`DDMMYYYY_00001.jpg`).
  - `state.json` updates are written to `.json.tmp` and then swapped atomically using `Path.replace()`.
- **Constraint**: Maintain this atomic write pattern for any new state files or data storage additions.

### 3. Separation of Concerns
- **`camera_utils.py`**: Handles low-level subprocess spawning, command execution, transient error retry logic, and low-level hardware-level USB bus resets to recover from camera lockups (e.g., PTP I/O errors).
- **`experiment_store.py`**: Manages the high-level directories, session/run directories (e.g., `ExpA_Run-01`), CSV logs, and persistent index state tracking.
- **`main.py`**: Manages GPIO input polling, edge-detection trigger logic, and orchestrates calls between camera utility commands and the persistent store.

---

## GPIO & Hardware Configuration

- **Trigger Input (GPIO 17)**: Configured as active-high. A rising edge initiates an image capture if armed and enabled.
- **Enable Gate (GPIO 27)**: Configured as active-high. Must be logic HIGH for the trigger input to perform a physical capture. If LOW, the trigger is still counted, indexed, and logged to CSV, but the camera is not fired.
- **Polling Loop Interval (`POLL_S = 0.005`)**: Uses a 5ms sleep interval in `main.py` to balance low CPU utilization with responsive hardware edge detection.
- **Re-arming Loop State**: The trigger must return to logic LOW before the system will re-arm itself for the next rising edge capture, ensuring exactly one capture per trigger event.

---

## Verification Procedures

Before delivering any major change, ensure the following steps are adhered to:

1. **Verify Startup Preparation**:
   - Ensure any changes do not break `startup.py`. This script performs a essential pre-flight health check (disk space validation, killing standard background USB grabbers like `gvfsd-gphoto2`, and verifying camera responsiveness).

2. **Verify Focus Check Loop**:
   - Any edits to `camera_utils.py` or image capture parameters should be verified against `focus_check.py` to ensure it continues to continuously stream downsampled or full-frame images for real-time adjustments without corrupting any active experiment counters.
