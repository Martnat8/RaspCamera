# Raspberry Pi + Canon EOS T3i Triggered Capture System

This repository contains a **crash-resilient image capture system** for a Canon EOS T3i (600D) controlled via **gphoto2** on a **Raspberry Pi 5**.

The system is designed to run from a terminal either:
- directly on a Raspberry Pi with a connected monitor, keyboard, and mouse
- or remotely over SSH in a headless configuration

> Developed with extensive use of generative AI-assisted coding tools.

The system listens to GPIO trigger lines, conditionally captures images, stores them on the Raspberry Pi, and logs every trigger event for later analysis. It is designed for **long-running experiments** and supports clean resume after crashes or reboots.

---

## Features

- Terminal-based operation (local monitor or SSH)
- Canon EOS capture via `gphoto2`
- GPIO-controlled triggering
- Enable / disable gating
- One capture per rising edge
- Safe re-arming on falling edge
- Automatic run folder creation
- Resume after crash or reboot
- CSV trigger log with persistent state
- No image overwrites
- Retry handling for transient camera communication errors

---

## Tested On

- Raspberry Pi 5
- Raspberry Pi OS Bookworm
- Canon EOS Rebel T3i (600D)

---

## Quick Start

On a fresh Raspberry Pi OS installation:

```bash
sudo apt install -y git

git clone <repo-url>
cd <repo-name>

chmod +x setup.sh
./setup.sh
```

# Navigate to the project directory
cd /path/to/your/repo-name

# 1. Clear background processes and check camera connection
python3 startup.py

# 2. Run the experiment (terminal will prompt user input)
python3 main.py

# To STOP the experiment at any time: Press Ctrl + C

---

## Hardware Setup

### Camera

- Canon EOS Rebel T3i (600D)
- USB connected to Raspberry Pi
- Lens in **MF**
- Mode dial set to **M**
- Auto power-off **disabled**
- Image review **off**

### GPIO

### GPIO

| Signal | GPIO | Wire Color | Direction | Notes |
|---|---|---|---|---|
| TRIGGER | 17 | Yellow | Input | Rising edge triggers capture |
| ENABLE | 27 | Green | Input | Must be HIGH to allow capture |

Inputs are assumed **active-high** with pull-downs.

---

## Repository Structure

```
.
├── camera_utils.py        # gphoto2 helpers and retry logic
├── experiment_store.py    # Run folder management, counters, CSV logging, resume logic
├── startup.py             # One-time system preparation for long runs
├── main.py                # GPIO-driven experiment runner
├── setup.sh               # Automated Raspberry Pi setup script
└── README.md
```

---

## How It Works

### Trigger Logic

- Rising edge on **TRIGGER**
- If **ENABLE = HIGH** → capture image
- If **ENABLE = LOW** → no capture
- Must see **TRIGGER** return **LOW** before re-arming
- Trigger count always increments
- Image count increments **only on successful capture**

### File Naming

Images are saved as:

```text
DDMMYYYY_00001.jpg
```

---

## Run Folder Layout

Each experiment run creates a dedicated folder inside the user-provided base directory:

```text
experiments/<EXPERIMENT-NAME>/
└──<EXPERIMENT-NAME>_Run_<#>/
    ├── photos/
    │   ├── DDMMYYYY_00001.jpg
    │   ├── DDMMYYYY_00002.jpg
    ├── log.csv
    └── state.json
```

### `log.csv`

One row is written **per trigger event**, regardless of whether an image was captured:

```text
timestamp,trigger_index,enable_state,captured,filename
```

### `state.json`

Stores persistent state to allow clean resume after interruption:

- Next image index
- Next trigger index
- Run directory path
- Last update timestamp

---

## Usage

### 1. Prepare the System

Run once after boot to ensure the camera and system are ready for a long experiment:

```bash
python3 startup.py
```

### 2. Start a New Experiment Run

Creates a new run folder inside the specified base directory:

```bash
python3 main.py 
```


Resume behavior:

- Image numbering continues from the last successful capture
- Trigger indexing continues from the last trigger
- New entries are appended to `log.csv`
- Existing images are never overwritten

### Stop the Experiment

```text
Ctrl + C
```

---

## Viewing Images Over SSH

When running over SSH, images cannot be displayed directly in the terminal. A simple workaround is to temporarily serve the image directory over HTTP.

From the image directory:

```bash
python3 -m http.server 8000
```

Then, from another computer on the same network, open:

```text
http://<raspi-ip-address>:8000
```

This allows live viewing of captured images while the experiment is running.

---
# Camera Focus & Framing Utility

The repository includes a dedicated real-time adjustment tool (focus_check.py) to easily frame your subject and dial in focus sharpness without polluting or inflating active experiment data logs.

The utility automates a continuous loop that instructs the camera to capture a new photo every 2 seconds, updates a static preview target, and hosts a localized HTTP media server.

## How to Use the Focus Loop

Stop Active Experiments: If main.py is currently running, terminate it using Ctrl + C to release the camera's USB bus interface.

Launch the Focus Tool: Run the script from your terminal:
python3 focus_check.py

Open the Preview Feed: Open a web browser on any computer or phone connected to the same local network and navigate to:
http://<your-raspi-ip-address>/latest_focus.jpg

Adjust in Real-Time: Physically adjust your camera's frame or turn the lens focus ring. Every time the terminal prints a ✅ Frame updated confirmation status line, simply Refresh your browser tab (F5 / Cmd + R) to instantly inspect the visual changes.

Exit and Deploy: Once your focus is perfectly crisp, press Ctrl + C in the terminal window to safely kill the testing loop and shutdown the image server, freeing the hardware up for your primary data-collection runs.

## Operational Notes

Zero Overhead: This utility completely overwrites a single file (latest_focus.jpg) over and over. It does not generate bulk tracking folders, keep counter states, or write rows to any experiment data logs.

Network Constraint: Ensure your viewing device is connected to the same local Wi-Fi router network subnet as the Raspberry Pi 5 to view the web page feed.


## Design Goals

- Deterministic behavior
- Safe recovery after failure
- Explicit separation of:
  - Hardware triggers
  - Capture logic
  - Data storage
- Auditability for experiments
- Long-duration experiment stability

---

## Notes

- Images are stored **only on the Raspberry Pi**, not retained on the camera SD card
- Canon EOS remote capture behavior varies by model; this setup has been validated on the T3i
- For very long runs, use a dummy battery / DC coupler
- Desktop camera auto-mounting can interfere with `gphoto2`; `setup.sh` removes common USB camera grabbers automatically

