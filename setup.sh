#!/bin/bash
# truSDX-AI Driver Setup Script for Linux
# Version: 2.0.0-AI
# Date: 2024-12-19
# Overhauled with non-interactive installs and modular Hamlib

# Enhanced error handling and diagnostics
set -eE -o pipefail
trap 'echo "ERROR: Command failed at line $LINENO" | tee -a /tmp/trusdx_setup.log; exit 1' ERR

# Initialize log file
LOG_FILE="/tmp/trusdx_setup.log"
echo "truSDX Setup Log - $(date)" > "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

# Initialize status tracking variables
PACKAGES_INSTALLED=0
PIP_PACKAGES_INSTALLED=0
GROUP_CHANGES="None"
SINK_CREATED=0
SMOKE_TEST_PASS=0
SETUP_SUCCESS=1
HAMLIB_UP_TO_DATE=0
RELOGIN_REQUIRED=0

echo "=== truSDX-AI Driver Setup for Linux ==="
echo "This script will install dependencies and configure audio for truSDX"
echo "Log file: $LOG_FILE"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "ERROR: Please do not run this script as root/sudo!" | tee -a "$LOG_FILE"
   echo "Run as normal user: ./setup.sh" | tee -a "$LOG_FILE"
   exit 1
fi

# Function to check current Hamlib version
check_hamlib() {
    if command -v rigctl > /dev/null; then
        CURRENT_VER=$(rigctl --version | head -n1 | awk '{print $3}')
        echo "Found rigctl version: $CURRENT_VER" | tee -a "$LOG_FILE"
    else
        CURRENT_VER="none"
        echo "rigctl not found" | tee -a "$LOG_FILE"
    fi
    
    if [[ "$CURRENT_VER" == "4.6.3" ]]; then
        HAMLIB_UP_TO_DATE=1
        echo "Hamlib 4.6.3 is already installed - no action required" | tee -a "$LOG_FILE"
        return 0
    else
        echo "Hamlib version $CURRENT_VER found, need to build 4.6.3" | tee -a "$LOG_FILE"
        return 1
    fi
}

echo "[1/7] Refreshing package lists..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Package list refresh failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    echo "Updating package lists..." | tee -a "$LOG_FILE"
    sudo apt-get update 2>&1 | tee -a "$LOG_FILE"
    echo "Package lists refreshed successfully" | tee -a "$LOG_FILE"
)

echo "[2/7] Installing system packages..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: System package installation failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    echo "Installing system packages non-interactively..." | tee -a "$LOG_FILE"
    DEBIAN_FRONTEND=noninteractive sudo apt-get install -y \
        python3 \
        python3-pip \
        portaudio19-dev \
        pulseaudio-utils \
        socat \
        build-essential \
        2>&1 | tee -a "$LOG_FILE"
    
    PACKAGES_INSTALLED=1
    echo "System packages installed successfully" | tee -a "$LOG_FILE"
)

echo "[3/7] Installing/upgrading pip packages..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: pip package installation failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    echo "Upgrading pip..." | tee -a "$LOG_FILE"
    python3 -m pip install --user --upgrade pip 2>&1 | tee -a "$LOG_FILE"
    
    echo "Installing Python packages..." | tee -a "$LOG_FILE"
    python3 -m pip install --user --upgrade pyaudio pyserial pytest 2>&1 | tee -a "$LOG_FILE"
    
    PIP_PACKAGES_INSTALLED=1
    echo "Python packages installed successfully" | tee -a "$LOG_FILE"
)

echo "[4/7] Checking / Installing Hamlib 4.6.3..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Hamlib check failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if ! check_hamlib; then
        echo "Calling Hamlib installation script..." | tee -a "$LOG_FILE"
        bash scripts/install_hamlib.sh
        HAMLIB_UP_TO_DATE=1
    fi
)

echo "[5/7] Checking dial-out group membership..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Group setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if groups | grep -q dialout; then
        echo "User already in dialout group" | tee -a "$LOG_FILE"
        GROUP_CHANGES="Already in dialout group"
    else
        echo "Adding user to dialout group for serial access..." | tee -a "$LOG_FILE"
        sudo usermod -a -G dialout "$USER" 2>&1 | tee -a "$LOG_FILE"
        GROUP_CHANGES="Added to dialout group"
        RELOGIN_REQUIRED=1
        echo "User added to dialout group." | tee -a "$LOG_FILE"
        echo "IMPORTANT: You must log out and log back in for serial port access to work!" | tee -a "$LOG_FILE"
    fi
)

echo "[6/7] Setting up truSDX audio device..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Audio device setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    # Check if TRUSDX sink already exists
    if pactl list sinks | grep -q "Name: TRUSDX"; then
        echo "TRUSDX audio device already exists" | tee -a "$LOG_FILE"
        SINK_CREATED=1
    else
        echo "Creating TRUSDX audio device..." | tee -a "$LOG_FILE"
        pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX" 2>&1 | tee -a "$LOG_FILE"
        SINK_CREATED=1
        echo "TRUSDX audio device created successfully" | tee -a "$LOG_FILE"
    fi
    
    # Add to user's pulseaudio config for persistence
    mkdir -p ~/.config/pulse 2>&1 | tee -a "$LOG_FILE"
    if ! grep -q "load-module module-null-sink sink_name=TRUSDX" ~/.config/pulse/default.pa 2>/dev/null; then
        echo "load-module module-null-sink sink_name=TRUSDX sink_properties=device.description=\"TRUSDX\"" >> ~/.config/pulse/default.pa
        echo "TRUSDX audio device will persist after reboot" | tee -a "$LOG_FILE"
    else
        echo "TRUSDX audio device already configured for persistence" | tee -a "$LOG_FILE"
    fi
)

echo "[7/7] Final setup and verification..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Final setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    # Make scripts executable
    chmod +x trusdx-txrx-AI.py hamlib_bridge.sh create_serial_bridge.sh 2>&1 | tee -a "$LOG_FILE"
    chmod +x scripts/install_hamlib.sh 2>&1 | tee -a "$LOG_FILE"
    
    # Smoke tests
    echo "Running verification tests..." | tee -a "$LOG_FILE"
    
    # Test Hamlib
    if command -v rigctl > /dev/null && rigctl --version | grep -q "4.6.3"; then
        echo "✓ Hamlib 4.6.3 verified" | tee -a "$LOG_FILE"
    else
        echo "✗ Hamlib verification failed" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    # Test Python imports
    if python3 -c "import pyaudio, serial, pytest; print('Python imports OK')" 2>&1 | tee -a "$LOG_FILE"; then
        echo "✓ Python packages verified" | tee -a "$LOG_FILE"
    else
        echo "✗ Python package verification failed" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    # Test audio sink
    if pactl list sinks short | grep -q TRUSDX; then
        echo "✓ TRUSDX audio sink verified" | tee -a "$LOG_FILE"
    else
        echo "✗ TRUSDX audio sink verification failed" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    # Test socat
    if command -v socat > /dev/null; then
        echo "✓ socat verified" | tee -a "$LOG_FILE"
    else
        echo "✗ socat verification failed" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    if [[ $SETUP_SUCCESS -eq 1 ]]; then
        SMOKE_TEST_PASS=1
        echo "All verification tests passed" | tee -a "$LOG_FILE"
    else
        echo "Some verification tests failed" | tee -a "$LOG_FILE"
    fi
)

echo
echo "=============================================" | tee -a "$LOG_FILE"
echo "         TRUSDX SETUP SUMMARY TABLE         " | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"

printf "%-25s | %-10s\n" "Component" "Status" | tee -a "$LOG_FILE"
echo "---------------------------------------------" | tee -a "$LOG_FILE"

# System packages
if [[ $PACKAGES_INSTALLED -eq 1 ]]; then
    printf "%-25s | %-10s\n" "System Packages" "✓ PASS" | tee -a "$LOG_FILE"
else
    printf "%-25s | %-10s\n" "System Packages" "✗ FAIL" | tee -a "$LOG_FILE"
fi

# Pip packages
if [[ $PIP_PACKAGES_INSTALLED -eq 1 ]]; then
    printf "%-25s | %-10s\n" "Python Packages" "✓ PASS" | tee -a "$LOG_FILE"
else
    printf "%-25s | %-10s\n" "Python Packages" "✗ FAIL" | tee -a "$LOG_FILE"
fi

# Hamlib
if [[ $HAMLIB_UP_TO_DATE -eq 1 ]]; then
    printf "%-25s | %-10s\n" "Hamlib 4.6.3" "✓ PASS" | tee -a "$LOG_FILE"
else
    printf "%-25s | %-10s\n" "Hamlib 4.6.3" "✗ FAIL" | tee -a "$LOG_FILE"
fi

# Group membership
if [[ "$GROUP_CHANGES" == "Already in dialout group" ]]; then
    printf "%-25s | %-10s\n" "Dialout Group" "✓ PASS" | tee -a "$LOG_FILE"
elif [[ "$GROUP_CHANGES" == "Added to dialout group" ]]; then
    printf "%-25s | %-10s\n" "Dialout Group" "✓ ADDED" | tee -a "$LOG_FILE"
else
    printf "%-25s | %-10s\n" "Dialout Group" "✗ FAIL" | tee -a "$LOG_FILE"
fi

# Audio sink
if [[ $SINK_CREATED -eq 1 ]]; then
    printf "%-25s | %-10s\n" "Audio Sink" "✓ PASS" | tee -a "$LOG_FILE"
else
    printf "%-25s | %-10s\n" "Audio Sink" "✗ FAIL" | tee -a "$LOG_FILE"
fi

# Overall status
if [[ $SETUP_SUCCESS -eq 1 ]]; then
    printf "%-25s | %-10s\n" "Overall Setup" "✓ PASS" | tee -a "$LOG_FILE"
else
    printf "%-25s | %-10s\n" "Overall Setup" "✗ FAIL" | tee -a "$LOG_FILE"
fi

echo "=============================================" | tee -a "$LOG_FILE"

# Final messages
if [[ $SETUP_SUCCESS -eq 1 ]]; then
    echo
    echo "🎉 Setup completed successfully!"
    echo
    if [[ $RELOGIN_REQUIRED -eq 1 ]]; then
        echo "⚠️  IMPORTANT: You have been added to the dialout group."
        echo "   Please log out and log back in for serial port access to work."
        echo
    fi
    echo "📋 Quick Start:"
    echo "   1. Connect your truSDX via USB"
    echo "   2. Run: ./trusdx-txrx-AI.py"
    echo
    echo "🔧 WSJT-X Configuration:"
    echo "   Radio: Kenwood TS-480"
    echo "   CAT Port: /tmp/trusdx_cat"
    echo "   Baud Rate: 115200"
    echo "   Audio Input: Monitor of TRUSDX"
    echo "   Audio Output: TRUSDX"
    echo
else
    echo
    echo "❌ Setup failed. Check the log file for details:"
    echo "   $LOG_FILE"
    echo
    exit 1
fi

echo "📄 Complete log: $LOG_FILE"
