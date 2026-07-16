# Raspberry Pi and Canon EOS T3i Triggered Capture System

This repository provides a crash-resilient, production-grade image capture system for Canon EOS DSLR cameras (specifically validated on the Rebel T3i / 600D) controlled via `gphoto2` on a Raspberry Pi 5 running Raspberry Pi OS Bookworm.

The system is designed for long-running scientific and industrial experiments. It operates seamlessly in headless, remote configurations over SSH or locally with a dedicated monitor. It monitors hardware GPIO inputs, executes atomic data logging, manages persistent storage indices, and includes automated USB self-healing mechanisms to recover from hardware timeouts or power-saving states.

---

## Key Features

* **Subprocess Isolation:** Avoids memory leaks and driver socket degradation by running ephemeral, OS-managed `gphoto2` CLI sessions instead of persistent background wrappers.
* **Low-Level USB Self-Healing:** Automatically detects USB/PTP communication lockups and sends raw `USBDEVFS_RESET` signals directly to the camera's USB bus interface, enabling seamless long-term operation.
* **Atomic File & State Persistence:** Writes state data to a temporary file before performing an atomic swap to protect against sudden power loss or system crashes.
* **Interactive Trigger Customization:** Offers terminal menu prompts to review, confirm, or manually update the next trigger counter index when resuming a session.
* **Dual-State Gated Capture:** Separates hardware triggers from active capture states via an Enable Gate, logging all event timestamps even when physical capture is bypassed.
* **Live Focus and Framing Utility:** Includes a low-overhead, concurrent local HTTP server utility for real-time framing and focus adjustments.

---

## Hardware Configuration and Wiring

### Camera Settings
* **Model:** Canon EOS Rebel T3i (600D) or compatible DSLR
* **Focus Mode:** Manual Focus (MF)
* **Exposure Mode:** Manual (M)
* **Auto Power-Off:** Disabled (Off)
* **Image Review:** Disabled (Off)

### GPIO Pin Mapping
The Raspberry Pi 5 GPIO pins are configured with internal/external pull-down resistors (active-high logic):

| Signal Name | Broadcom GPIO | Default Direction | Wiring Notes |
| :--- | :--- | :--- | :--- |
| **TRIGGER** | GPIO 17 | Input (Active-High) | Rising edge initiates the capture block. Requires falling-edge release before re-arming. |
| **ENABLE** | GPIO 27 | Input (Active-High) | Gating line. Must be logic HIGH to activate physical capture. If logic LOW, the trigger is logged but no photo is taken. |

---

## Repository Structure

```text
.
├── main.py              # Core application orchestrator and GPIO polling loop
├── camera_utils.py      # Low-level gphoto2 execution and USB self-healing logic
├── experiment_store.py  # Run management, atomic state persistence, and CSV logging
├── startup.py           # Pre-flight health, disk space check, and USB grabber cleanup
├── focus_check.py       # Live framing preview stream and local HTTP media server
├── test.py              # Test script for camera verification and summary
├── setup.sh             # Automatic system package installer and environment setup
├── agents.md            # Reference guide and architectural constraints for developer agents
└── README.md            # System documentation
```

---

## Run Folder Architecture

Each experiment run generates a dedicated, sequentially indexed subfolder inside the root data directory to prevent accidental data overwrites:

```text
experiments/[EXPERIMENT_NAME]/
└── [EXPERIMENT_NAME]_Run-[Index]/
    ├── photos/
    │   ├── [DDMMYYYY]_[Index].jpg
    │   └── [DDMMYYYY]_[Index + 1].jpg
    ├── log.csv
    └── state.json
```

### Event Log (`log.csv`)
An entry is appended immediately upon every trigger rising edge. This ensures auditing integrity:
```csv
timestamp,trigger_index,enable_state,captured,filename
2026-07-16T10:00:00.123,1,1,1,16072026_00001.jpg
2026-07-16T10:00:05.456,2,0,0,
```

### Persistent State (`state.json`)
Maintains session state variables across program invocations, protecting index continuity from power failures:
```json
{
  "next_image_count": 3,
  "next_trigger_index": 3,
  "run_dir": "/home/pi/RaspCamera/experiments/ExpA/ExpA_Run-01",
  "updated": "2026-07-16T10:00:05"
}
```

---

## Installation and Setup

Execute the automated script on a fresh installation of Raspberry Pi OS to install dependencies and configure the environment:

```bash
git clone <repository-url>
cd RaspCamera
chmod +x setup.sh
./setup.sh
```

The script automatically:
1. Installs system binaries (`gphoto2`, `libgphoto2-dev`, `python3-gpiozero`, etc.).
2. Purges the OS camera volume-monitor services (`gvfs-backends`) which frequently lock camera USB interfaces.
3. Grants executable permissions to all Python modules.

---

## Execution Guide

### 1. Pre-Flight Diagnostic Check
Before starting a long experiment session, run the startup helper to verify hardware readiness, release blocked USB ports, and check local disk storage space:
```bash
python3 startup.py
```

### 2. Launch the Capture Engine
Run the primary execution loop:
```bash
python3 main.py
```

If command-line arguments are omitted, the application will launch an interactive setup guide:
* **Experiment Run Name:** Enter a run name (defaults to `ExpA`).
* **Execution Mode:**
  1. **Resume (Default):** Reconnects to the last active run folder, loads state counters, and prompts you to review or manually override the starting trigger count index.
  2. **Restart:** Wipes historical local memory buffers and starts a completely fresh run index.

To run headlessly or bypass interactive prompt menus (e.g., in automated systemd service environments):
```bash
python3 main.py --base ./experiments/ExpA --mode resume
```

To stop the experiment safely at any point, use `Ctrl + C`.

---

## Real-Time Focus and Framing Utility

To adjust focus, lens calibration, or framing without affecting experiment data counters or logs:

1. Terminate any active execution of `main.py` using `Ctrl + C`.
2. Start the focusing module:
   ```bash
   python3 focus_check.py
   ```
3. Open a web browser on any machine connected to the same local network and visit:
   ```text
   http://[RASPBERRY_PI_IP_ADDRESS]:8000/latest_focus.jpg
   ```
4. Adjust the camera lens. The module continuously updates the target image every 2 seconds. Simply refresh your browser tab to check clarity.
5. Exit using `Ctrl + C` to shut down the preview engine and release the camera interface for standard capture runs.
