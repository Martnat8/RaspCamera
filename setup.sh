#!/usr/bin/env bash
set -e

echo "=== Raspberry Pi Camera Capture Setup ==="

echo "=== Updating package list ==="
sudo apt update

echo "=== Installing required system packages ==="
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-gpiozero \
  git \
  gphoto2 \
  libgphoto2-dev \
  jq

echo "=== Removing common camera auto-grabbers ==="
sudo apt purge -y gvfs-backends || true

echo "=== Killing any current camera-grabber processes ==="
sudo pkill -f gvfsd-gphoto2 || true
sudo pkill -f gvfs-gphoto2-volume-monitor || true
sudo pkill -f gphoto2 || true

echo "=== Making Python scripts executable ==="
chmod +x main.py startup.py test.py camera_utils.py experiment_store.py 2>/dev/null || true

echo "=== Checking gphoto2 installation ==="
if ! command -v gphoto2 >/dev/null 2>&1; then
  echo "[FAIL] gphoto2 was not installed correctly."
  exit 1
fi

echo "[OK] gphoto2 found: $(gphoto2 --version | head -n 1)"

echo "=== Checking camera connection ==="
if gphoto2 --summary >/dev/null 2>&1; then
  echo "[OK] Camera detected and responding."
else
  echo "[WARN] Camera was not detected or is busy."
  echo "       This is not always fatal during setup."
  echo "       Before running the experiment, check:"
  echo "       - Camera is ON"
  echo "       - USB cable is connected"
  echo "       - Camera is in manual mode"
  echo "       - Auto power-off is disabled"
  echo "       - Run: python3 startup.py"
fi

echo
echo "=== Setup complete ==="
echo "Recommended next steps:"
echo "  python3 startup.py"
echo "  python3 test.py"
echo "  python3 main.py --base ./experiments/ExpA --mode restart"