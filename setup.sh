#!/usr/bin/env bash
set -e

echo "=== Updating system ==="
sudo apt update
sudo apt upgrade -y

echo "=== Installing system packages ==="
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  git \
  gphoto2 \
  libgphoto2-dev

echo "=== Upgrading pip ==="
python3 -m pip install --upgrade pip

echo "=== Installing Python dependencies ==="
pip3 install gpiozero

echo "=== Disabling desktop camera auto-grabbers ==="
sudo killall gvfsd-gphoto2 gvfs-gphoto2-volume-monitor 2>/dev/null || true

echo "=== Setup complete ==="
echo "You can now run:"
echo "  python3 test.py"
echo "  python3 main.py"
