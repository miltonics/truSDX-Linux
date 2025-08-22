#!/usr/bin/env bash
# truSDX-AI setup script
# Simple automated setup for Linux Mint/Ubuntu/Debian-like systems.
# - Installs OS packages and Python dependencies system-wide
# - Configures ALSA loopback module and PCM devices
# - Adds user to dialout group for serial port access
# - Creates default config file if missing

# Colors
c_green="\033[1;32m"; c_yellow="\033[1;33m"; c_red="\033[1;31m"; c_blue="\033[1;34m"; c_reset="\033[0m"

# ERR trap for unexpected errors
trap 'log_step "Unexpected" FAIL "$BASH_COMMAND exited with $?"' ERR

# Results tracking
declare -A STEP_STATUS

# Helper function for logging step results
log_step() {
  STEP_STATUS["$1"]=$2
  if [[ $2 == "OK" ]]; then
    echo -e "${c_green}✓ $1${c_reset}"
  else
    echo -e "${c_red}✗ $1 ($3)${c_reset}"
  fi
}

echo -e "${c_blue}==== truSDX-AI Setup Script ====${c_reset}"
echo

# Check if running with sudo (needed for system-wide installs)
if [[ $EUID -eq 0 ]]; then
   echo -e "${c_red}Please do not run this script as root. It will ask for sudo when needed.${c_reset}"
   exit 1
fi

# Install OS packages
if (
  if command -v apt-get >/dev/null 2>&1; then
    echo -e "${c_blue}[1/6] Installing system packages...${c_reset}"
    sudo apt-get update -y
    # Python and pip
    sudo apt-get install -y python3 python3-pip
    # Serial/audio dependencies
    sudo apt-get install -y portaudio19-dev alsa-utils
    # Additional tools
    sudo apt-get install -y socat grep coreutils
  else
    echo -e "${c_yellow}[WARNING] apt-get not found. Please manually install: python3, pip3, portaudio19-dev, alsa-utils${c_reset}"
    exit 1
  fi
); then
  log_step "[1/6] Installing system packages" OK
else
  log_step "[1/6] Installing system packages" FAIL "$?"
fi

# Install Python packages using apt (preferred for system packages)
if (
  echo -e "${c_blue}[2/6] Installing Python packages...${c_reset}"
  sudo apt-get install -y python3-serial python3-pyaudio
); then
  log_step "[2/6] Installing Python packages" OK
else
  log_step "[2/6] Installing Python packages" FAIL "$?"
fi

# Add user to dialout group for serial port access
if (
  echo -e "${c_blue}[3/6] Adding user to dialout group...${c_reset}"
  if ! groups | grep -q dialout; then
    sudo usermod -a -G dialout $USER
    echo -e "${c_green}Added $USER to dialout group. You may need to log out and back in for this to take effect.${c_reset}"
  else
    echo -e "${c_green}User already in dialout group.${c_reset}"
  fi
); then
  log_step "[3/6] Adding user to dialout group" OK
else
  log_step "[3/6] Adding user to dialout group" FAIL "$?"
fi

# Setup ALSA Loopback
if (
  echo -e "${c_blue}[4/6] Setting up ALSA loopback...${c_reset}"
  # Load snd-aloop module for ALSA loopback
  if ! lsmod | grep -q "^snd_aloop"; then
    sudo modprobe snd-aloop index=1 id=Loopback
    echo -e "${c_green}Loaded ALSA loopback module with index=1.${c_reset}"
    # Make it persistent across reboots
    echo "snd-aloop" | sudo tee /etc/modules-load.d/snd-aloop.conf >/dev/null
    echo "options snd-aloop index=1 id=Loopback" | sudo tee /etc/modprobe.d/snd-aloop.conf >/dev/null
    echo -e "${c_green}Added snd-aloop to auto-load on boot with index=1.${c_reset}"
  else
    echo -e "${c_green}ALSA loopback module already loaded.${c_reset}"
  fi

  # Create or update ~/.asoundrc with trusdx PCM devices
  ASRC_FILE="${HOME}/.asoundrc"
  echo -e "${c_blue}Configuring ALSA PCM devices...${c_reset}"

  # Backup existing .asoundrc if it exists
  if [[ -f "${ASRC_FILE}" ]]; then
    cp "${ASRC_FILE}" "${ASRC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${c_yellow}Backed up existing .asoundrc${c_reset}"
  fi
  
  # Create complete .asoundrc with proper hints for Qt applications
  cat > "${ASRC_FILE}" <<'ALSA'
# ALSA configuration for truSDX loopback audio routing
# Created for use with snd-aloop on Linux systems
#
# TX: hw:1,0,0 (apps to radio) - Loopback card 1, device 0, subdevice 0
# RX: hw:1,1,0 (radio to apps) - Loopback card 1, device 1, subdevice 0

# PRIMARY DEVICES (Option #1 - PREFERRED)
# User-friendly device names matching hardware labeling

# TRUSDX - TX path (apps → truSDX)
pcm.TRUSDX {
    type plug
    slave {
        pcm "hw:1,0,0"
        # Allow automatic rate/format conversion
        # JS8Call/WSJT-X will negotiate the best settings
    }
    hint {
        show on
        description "TRUSDX - Audio output to radio (TX)"
    }
}

ctl.TRUSDX {
    type hw
    card 1
}

# TRUSDX.monitor - RX path (truSDX → apps)
pcm."TRUSDX.monitor" {
    type plug
    slave {
        pcm "hw:1,1,0"
        # Allow automatic rate/format conversion
        # JS8Call/WSJT-X will negotiate the best settings
    }
    hint {
        show on
        description "TRUSDX.monitor - Audio input from radio (RX)"
    }
}

ctl."TRUSDX.monitor" {
    type hw
    card 1
}

# TRUSDX_monitor - Alternative naming for compatibility
pcm.TRUSDX_monitor {
    type plug
    slave {
        pcm "hw:1,1,0"
    }
}

# LEGACY DEVICES (Option #2 - kept for backwards compatibility)
# These names are deprecated but kept for existing configurations

pcm.trusdx_tx {
    type plug
    slave {
        pcm "hw:1,0,0"
    }
    hint {
        show on
        description "[Legacy] truSDX TX - Audio output to radio"
    }
}

ctl.trusdx_tx {
    type hw
    card 1
}

pcm.trusdx_rx {
    type plug
    slave {
        pcm "hw:1,1,0"
    }
    hint {
        show on
        description "[Legacy] truSDX RX - Audio input from radio"
    }
}

ctl.trusdx_rx {
    type hw
    card 1
}

# Extra sub-devices for WSJT-X compatibility
pcm.trusdx_tx_app { type plug; slave.pcm "hw:0,1" }   # free playback
ctl.trusdx_tx_app { type hw; card TRUSDX }
pcm.trusdx_rx_app { type plug; slave.pcm "hw:1,1" }   # free capture
ctl.trusdx_rx_app { type hw; card TRUSDX }
ALSA
    
    echo -e "${c_green}Created ALSA PCM devices with proper hints for Qt applications${c_reset}"
    
    # Create system-wide configuration for better visibility
    SYSTEM_ALSA_DIR="/usr/share/alsa/alsa.conf.d"
    if [[ -d "${SYSTEM_ALSA_DIR}" ]]; then
      echo -e "${c_blue}Creating system-wide ALSA configuration...${c_reset}"
      cat > /tmp/99-trusdx.conf <<'SYSALSA'
# truSDX ALSA PCM devices configuration
# This file makes trusdx_tx and trusdx_rx visible to all applications

# TX device - Audio output to radio (WSJT-X/JS8Call transmit audio)
pcm.trusdx_tx {
    type plug
    slave {
        pcm "hw:0,0"
        # Allow automatic format conversion
        # Applications will negotiate the best format
    }
    hint {
        show on
        description "truSDX TX - Audio output to radio"
    }
}

ctl.trusdx_tx {
    type hw
    card TRUSDX
}

# RX device - Audio input from radio (WSJT-X/JS8Call receive audio)
pcm.trusdx_rx {
    type plug
    slave {
        pcm "hw:0,1"
        # Allow automatic format conversion
        # Applications will negotiate the best format
    }
    hint {
        show on
        description "truSDX RX - Audio input from radio"
    }
}

ctl.trusdx_rx {
    type hw
    card TRUSDX
}
SYSALSA
      sudo cp /tmp/99-trusdx.conf "${SYSTEM_ALSA_DIR}/99-trusdx.conf"
      rm /tmp/99-trusdx.conf
      echo -e "${c_green}Created system-wide ALSA configuration${c_reset}"
    fi
    
    # Restore ALSA settings
    alsactl restore 2>/dev/null || true
    sudo alsactl nrestore 2>/dev/null || true
    
    echo -e "${c_green}ALSA devices configured successfully!${c_reset}"
    echo -e "${c_yellow}Note: The devices 'trusdx_tx' and 'trusdx_rx' should now be visible in JS8Call/WSJT-X${c_reset}"
); then
  log_step "[4/6] Setting up ALSA loopback" OK
else
  log_step "[4/6] Setting up ALSA loopback" FAIL "$?"
fi

# Setup PipeWire virtual sink if PipeWire is available
if (
  # Check if PipeWire is running
  if systemctl --user --quiet is-active pipewire; then
    echo -e "${c_blue}[4b/6] Setting up PipeWire virtual devices...${c_reset}"
    
    # Create PipeWire config directory
    PW_DIR="${HOME}/.config/pipewire/pipewire.conf.d"
    mkdir -p "${PW_DIR}"
    
    # Create PipeWire configuration for TRUSDX virtual sink
    PW_FILE="${PW_DIR}/90-trusdx.conf"
    cat > "${PW_FILE}" <<'PWCONF'
context.objects = [
    {
        factory = adapter
        args = {
            factory.name     = support.null-audio-sink
            node.name        = "TRUSDX"
            node.description = "TRUSDX Virtual Sink"
            media.class      = "Audio/Sink"
            audio.position   = "FL,FR"
        }
    }
]
PWCONF
    echo -e "${c_green}Created PipeWire configuration for TRUSDX virtual sink${c_reset}"
    
    # Restart PipeWire to apply changes
    systemctl --user restart pipewire pipewire-pulse 2>/dev/null || true
    sleep 2
    
    # Verify the virtual sink was created
    if pactl list short sinks 2>/dev/null | grep -q "TRUSDX"; then
      echo -e "${c_green}✓ TRUSDX PipeWire virtual sink created successfully${c_reset}"
      echo -e "${c_green}✓ TRUSDX.monitor source will be available for input${c_reset}"
    else
      echo -e "${c_yellow}⚠ TRUSDX virtual sink not detected yet (may require restart)${c_reset}"
    fi
  else
    echo -e "${c_yellow}PipeWire not detected, skipping virtual sink setup${c_reset}"
    echo -e "${c_yellow}Using ALSA loopback devices only${c_reset}"
  fi
); then
  log_step "[4b/6] Setting up PipeWire virtual devices" OK
else
  # Not a critical failure if PipeWire isn't present
  if systemctl --user --quiet is-active pipewire; then
    log_step "[4b/6] Setting up PipeWire virtual devices" FAIL "$?"
  else
    log_step "[4b/6] Setting up PipeWire virtual devices" OK "(skipped - no PipeWire)"
  fi
fi

# Create default config file
if (
  echo -e "${c_blue}[5/6] Creating configuration...${c_reset}"
  CONF_DIR="${HOME}/.config"
  CONF_FILE="${CONF_DIR}/trusdx-ai.json"
  mkdir -p "${CONF_DIR}"
  if [[ ! -f "${CONF_FILE}" ]]; then
    cat > "${CONF_FILE}" <<JSON
{
  "cat_port": "/tmp/trusdx_cat",
  "audio_device": "TRUSDX"
}
JSON
    echo -e "${c_green}Created default config at ${CONF_FILE}${c_reset}"
  else
    echo -e "${c_green}Config file already exists at ${CONF_FILE}${c_reset}"
  fi
); then
  log_step "[5/6] Creating configuration" OK
else
  log_step "[5/6] Creating configuration" FAIL "$?"
fi

# Setup systemd service for automatic USB monitoring
if (
  echo -e "${c_blue}[6/6] Setting up TRUSDX.monitor service...${c_reset}"
  
  # Create symlink to avoid space issues in path
  if [[ ! -L "/opt/trusdx" ]]; then
    sudo ln -s "$(pwd)" /opt/trusdx
    echo -e "${c_green}Created symlink /opt/trusdx${c_reset}"
  fi
  
  # Make monitor script executable
  if [[ -f "trusdx-monitor.sh" ]]; then
    chmod +x trusdx-monitor.sh
    echo -e "${c_green}Made trusdx-monitor.sh executable${c_reset}"
  else
    echo -e "${c_yellow}WARNING: trusdx-monitor.sh not found${c_reset}"
  fi
  
  # Create systemd service file
  cat > /tmp/TRUSDX.monitor.service <<'SYSTEMD'
[Unit]
Description=truSDX USB connection monitor
After=network.target multi-user.target
Wants=network.target

[Service]
Type=simple
User=$USER
Environment="PYTHONUNBUFFERED=1"
WorkingDirectory=/opt/trusdx
ExecStart=/opt/trusdx/trusdx-monitor.sh
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD
  
  # Replace $USER in service file
  sed -i "s/\$USER/$USER/g" /tmp/TRUSDX.monitor.service
  
  # Install and enable service
  sudo cp /tmp/TRUSDX.monitor.service /etc/systemd/system/TRUSDX.monitor.service
  rm /tmp/TRUSDX.monitor.service
  sudo systemctl daemon-reload
  sudo systemctl enable TRUSDX.monitor.service
  
  echo -e "${c_green}TRUSDX.monitor service installed and enabled${c_reset}"
  echo -e "${c_yellow}The service will start automatically on boot${c_reset}"
  echo -e "${c_yellow}To start it now: sudo systemctl start TRUSDX.monitor${c_reset}"
); then
  log_step "[6/6] Setting up TRUSDX.monitor service" OK
else
  log_step "[6/6] Setting up TRUSDX.monitor service" FAIL "$?"
fi

# Verify installation
echo
echo -e "${c_blue}Verifying installation...${c_reset}"
python3 - <<'PY'
import sys
try:
    import serial
    print("✓ pyserial installed")
except Exception as e:
    print("✗ pyserial not found:", e)
    sys.exit(1)
try:
    import pyaudio
    print("✓ pyaudio installed")
except Exception as e:
    print("✗ pyaudio not found:", e)
    sys.exit(1)
PY

# Verify ALSA loopback devices
echo -e "${c_blue}Checking ALSA PCM aliases...${c_reset}"
aplay -L 2>/dev/null | grep trusdx_ || {
  echo -e "${c_yellow}⚠ WARNING: ALSA PCM aliases not visible yet!${c_reset}"
  echo -e "${c_yellow}  The aliases (trusdx_tx, trusdx_rx, trusdx_tx_app, trusdx_rx_app) may require:${c_reset}"
  echo -e "${c_yellow}  • Logout and login again${c_reset}"
  echo -e "${c_yellow}  • Or restart ALSA: sudo alsa force-reload${c_reset}"
  echo -e "${c_yellow}  • Or reboot the system${c_reset}"
}
if aplay -L 2>/dev/null | grep -q "trusdx_"; then
  echo -e "${c_green}✓ ALSA PCM aliases are visible:${c_reset}"
  aplay -L 2>/dev/null | grep trusdx_ | while read -r line; do
    echo "  • $line"
  done
fi

echo
echo -e "${c_green}==== Setup Complete! ====${c_reset}"
echo
# Display summary of step results
echo -e "${c_blue}=== Summary ===${c_reset}"
for k in "${!STEP_STATUS[@]}"; do 
  if [[ "${STEP_STATUS[$k]}" == "FAIL" ]]; then
    # Highlight FAIL entries in red
    echo -e "${c_red}$k : ${STEP_STATUS[$k]}${c_reset}"
  else
    echo "$k : ${STEP_STATUS[$k]}"
  fi
done
echo
echo -e "${c_green}To run the driver:${c_reset}"
echo -e "  ${c_blue}./trusdx-txrx-AI.py${c_reset}"
echo
echo -e "${c_yellow}Note: If you were added to the dialout group, you may need to log out and back in.${c_reset}"
echo -e "${c_yellow}Note: To see the new ALSA devices, verify with: aplay -L | grep trusdx_${c_reset}"
echo
echo -e "For WSJT-X/JS8Call configuration:"
echo -e "  • Radio: Kenwood TS-480"
echo -e "  • Port: /tmp/trusdx_cat"
echo -e "  • Baud: 115200"
echo -e "  • Audio Input: ${c_green}TRUSDX_monitor${c_reset} or ${c_green}TRUSDX.monitor${c_reset} (for receiving from radio)"
echo -e "  • Audio Output: ${c_green}TRUSDX${c_reset} (for transmitting to radio)"
echo -e "${c_yellow}Troubleshooting: If hw:Loopback does not exist, run 'sudo modprobe snd-aloop' and reboot${c_reset}"

echo
read -rp "Press Enter to exit..."
