#!/bin/bash
# truSDX-AI Driver Setup Script for Linux
# Version: 1.1.6-AI-VU-WORKING
# Date: 2024-06-10

set -e

echo "=== truSDX-AI Driver Setup for Linux ==="
echo "This script will install dependencies and configure audio for truSDX"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please do not run this script as root/sudo!"
   echo "Run as normal user: ./setup.sh"
   exit 1
fi

echo "[1/5] Installing Python dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip portaudio19-dev pulseaudio-utils
pip3 install --user pyaudio pyserial

echo "[2/5] Setting up truSDX audio device..."
# Check if TRUSDX sink already exists
if pactl list sinks | grep -q "Name: TRUSDX"; then
    echo "TRUSDX audio device already exists"
else
    echo "Creating TRUSDX audio device..."
    pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"
fi

echo "[3/5] Creating persistent audio setup..."
# Add to user's pulseaudio config for persistence
mkdir -p ~/.config/pulse
if ! grep -q "load-module module-null-sink sink_name=TRUSDX" ~/.config/pulse/default.pa 2>/dev/null; then
    echo "load-module module-null-sink sink_name=TRUSDX sink_properties=device.description=\"TRUSDX\"" >> ~/.config/pulse/default.pa
    echo "TRUSDX audio device will persist after reboot"
else
    echo "TRUSDX audio device already configured for persistence"
fi

echo "[4/5] Setting up directory structure..."
mkdir -p /tmp
mkdir -p ~/.config

echo "[5/5] Making driver executable..."
chmod +x trusdx-txrx-AI.py

echo
echo "=== Setup Complete! ==="
echo
echo "IMPORTANT: Connect your truSDX via USB before running the driver"
echo
echo "To start the driver:"
echo "  ./trusdx-txrx-AI.py"
echo
echo "For verbose output:"
echo "  ./trusdx-txrx-AI.py --verbose"
echo
echo "=== WSJT-X Configuration ==="
echo "Radio: Kenwood TS-480"
echo "CAT Port: /tmp/trusdx_cat"
echo "Baud Rate: 115200"
echo "Audio Input: Monitor of TRUSDX"
echo "Audio Output: TRUSDX"
echo "PTT Method: CAT or RTS/DTR"
echo "Poll Interval: 80ms"
echo
echo "Run 'pavucontrol' to verify audio routing if needed."

