# Raspberry Pi + Canon EOS T3i Triggered Capture System

This repository contains a **headless, crash-resilient image capture system** for a Canon EOS T3i (600D) controlled via **gphoto2** on a **Raspberry Pi 5**.

** Super vibe coded with generative AI **

The system listens to GPIO trigger lines, conditionally captures images, stores them on the Raspberry Pi, and logs every trigger event for later analysis. It is designed for **long-running experiments** and supports clean resume after crashes or reboots.

---

## Features

- Headless operation (SSH only, no GUI)
- Canon EOS capture via `gphoto2`
- GPIO-controlled triggering
- Enable / disable gating
- One capture per rising edge
- Safe re-arming on falling edge
- Automatic run folder creation
- Resume after crash or reboot
- CSV trigger log with persistent state
- No image overwrites

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
| Signal  | GPIO | Direction | Notes |
|--------|------|-----------|-------|
| TRIGGER | 17 | Input | Rising edge triggers capture |
| ENABLE  | 27 | Input | Must be HIGH to allow capture |

Inputs are assumed **active-high** with pull-downs.

---

## Software Requirements

On the Raspberry Pi:

```bash
sudo apt update
sudo apt install -y gphoto2 python3-gpiozero jq
```

Remove USB grabbers (recommended for stability):

```bash
sudo apt purge -y gvfs-backends
sudo reboot
```

---

## Repository Structure

```
.
├── camera_utils.py        # gphoto2 helpers and retry logic
├── experiment_store.py    # Run folder management, counters, CSV logging, resume logic
├── startup.py             # One-time system preparation for long runs
├── main.py                # GPIO-driven experiment runner
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
```
DDMMYYYY_00001.jpg
```

---

## Run Folder Layout

Each experiment run creates a dedicated folder inside the user-provided base directory:

```
experiments/ExpA/
└── Run_YYYYMMDD_HHMMSS/
    ├── photos/
    │   ├── DDMMYYYY_00001.jpg
    │   ├── DDMMYYYY_00002.jpg
    ├── log.csv
    └── state.json
```

### `log.csv`
One row is written **per trigger event**, regardless of whether an image was captured:

```
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

### 1. Prepare the system
Run once after boot to ensure the camera and system are ready for a long experiment:

```bash
python3 startup.py
```

### 2. Start a new experiment run
Creates a new run folder inside the specified base directory:

```bash
python3 main.py --base ./experiments/ExpA --mode restart
```

### 3. Resume an existing run
Continues the most recent run folder inside the base directory:

```bash
python3 main.py --base ./experiments/ExpA --mode resume
```

Resume behavior:
- Image numbering continues from the last successful capture
- Trigger indexing continues from the last trigger
- New entries are appended to `log.csv`
- Existing images are never overwritten

### Stop the experiment
```text
Ctrl + C
```

---

## Design Goals

- Deterministic behavior
- Safe recovery after failure
- Explicit separation of:
  - Hardware triggers
  - Capture logic
  - Data storage
- Auditability for experiments

---

## Notes

- Images are stored **only on the Pi**, not retained on the camera SD card
- Canon EOS remote capture behavior varies by model; this setup has been validated on the T3i
- For very long runs, use a dummy battery / DC coupler

---

## Future Extensions (Optional)

- Systemd service for auto-start
- Trigger debounce / rate limiting
- Disk space guardrails
- Metadata export per run
- Analysis scripts
