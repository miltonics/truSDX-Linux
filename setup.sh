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
    sudo apt-get install -y portaudio19-dev alsa-utils libasound2-plugins pulseaudio-utils pavucontrol
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

  # Create or update ~/.asoundrc with a minimal, safe config that exposes Pulse to ALSA apps
  ASRC_FILE="${HOME}/.asoundrc"
  echo -e "${c_blue}Configuring ALSA (minimal pulse bridge)...${c_reset}"

  # Backup existing .asoundrc if it exists
  if [[ -f "${ASRC_FILE}" ]]; then
    cp "${ASRC_FILE}" "${ASRC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${c_yellow}Backed up existing .asoundrc${c_reset}"
  fi
  
  # Minimal config: route ALSA default to PulseAudio/PipeWire
  cat > "${ASRC_FILE}" <<'ALSA'
# Minimal ALSA config to expose PulseAudio/PipeWire to ALSA apps
# Previous config backed up as ~/.asoundrc.backup.*

pcm.!default {
    type pulse
}

ctl.!default {
    type pulse
}

pcm.pulse {
    type pulse
}

ctl.pulse {
    type pulse
}
ALSA
    
    echo -e "${c_green}Created minimal ALSA config (default → pulse)${c_reset}"
    
    # Restore ALSA settings
    alsactl restore 2>/dev/null || true
    sudo alsactl nrestore 2>/dev/null || true
    
    echo -e "${c_green}ALSA configured successfully!${c_reset}"
    echo -e "${c_yellow}Note: Apps will see 'pulse' and 'default' alongside your normal devices${c_reset}"
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

# Setup systemd service for automatic USB monitoring (DISABLED BY DEFAULT)
# The following block has been intentionally commented out to ensure the driver
# never auto-starts. You can re-enable this section once the driver is stable.
#
#: <<'TRUSDX_SERVICE_BLOCK'
#if (
#  echo -e "${c_blue}[6/6] Setting up TRUSDX.monitor service...${c_reset}"
#  
#  # Create symlink to avoid space issues in path
#  if [[ ! -L "/opt/trusdx" ]]; then
#    sudo ln -s "$(pwd)" /opt/trusdx
#    echo -e "${c_green}Created symlink /opt/trusdx${c_reset}"
#  fi
#  
#  # Make monitor script executable
#  if [[ -f "trusdx-monitor.sh" ]]; then
#    chmod +x trusdx-monitor.sh
#    echo -e "${c_green}Made trusdx-monitor.sh executable${c_reset}"
#  else
#    echo -e "${c_yellow}WARNING: trusdx-monitor.sh not found${c_reset}"
#  fi
#  
#  # Create systemd service file
#  cat > /tmp/TRUSDX.monitor.service <<'SYSTEMD'
#[Unit]
#Description=truSDX USB connection monitor
#After=network.target multi-user.target
#Wants=network.target
#
#[Service]
#Type=simple
#User=$USER
#Environment="PYTHONUNBUFFERED=1"
#WorkingDirectory=/opt/trusdx
#ExecStart=/opt/trusdx/trusdx-monitor.sh
#Restart=on-failure
#RestartSec=10
#StandardOutput=journal
#StandardError=journal
#
#[Install]
#WantedBy=multi-user.target
#SYSTEMD
#  
#  # Replace $USER in service file
#  sed -i "s/\$USER/$USER/g" /tmp/TRUSDX.monitor.service
#  
#  # Install and enable service
#  sudo cp /tmp/TRUSDX.monitor.service /etc/systemd/system/TRUSDX.monitor.service
#  rm /tmp/TRUSDX.monitor.service
#  sudo systemctl daemon-reload
#  sudo systemctl enable TRUSDX.monitor.service
#  
#  echo -e "${c_green}TRUSDX.monitor service installed and enabled${c_reset}"
#  echo -e "${c_yellow}The service will start automatically on boot${c_reset}"
#  echo -e "${c_yellow}To start it now: sudo systemctl start TRUSDX.monitor${c_reset}"
#); then
#  log_step "[6/6] Setting up TRUSDX.monitor service" OK
#else
#  log_step "[6/6] Setting up TRUSDX.monitor service" FAIL "$?"
#fi
#TRUSDX_SERVICE_BLOCK

# Record as skipped in the summary
log_step "[6/6] Setting up TRUSDX.monitor service" OK "(skipped - service disabled by default)"

# Block services that grab serial ports and install udev ignore rules for truSDX
if (
  echo -e "${c_blue}[7/7] Protecting truSDX serial port...${c_reset}"
  
  # Make ModemManager ignore CH340 (truSDX) completely
  echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", ENV{ID_MM_DEVICE_IGNORE}="1", ENV{ID_MM_PORT_IGNORE}="1"' | sudo tee /etc/udev/rules.d/77-mm-ignore-trusdx.rules >/dev/null
  
  # Install shipped udev rules for truSDX power/perms/symlink
  if [[ -f "99-trusdx.rules" ]]; then
    sudo cp 99-trusdx.rules /etc/udev/rules.d/99-trusdx.rules
  fi
  
  # Reload udev rules and trigger
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  
  # Disable and mask ModemManager if present (prevents grabbing /dev/ttyUSB0)
  if systemctl list-unit-files | grep -q "^ModemManager.service"; then
    echo -e "${c_yellow}Disabling and masking ModemManager to prevent serial port grabs...${c_reset}"
    sudo systemctl disable --now ModemManager || true
    sudo systemctl mask ModemManager || true
  else
    echo -e "${c_green}ModemManager not present or already disabled.${c_reset}"
  fi
); then
  log_step "[7/7] Serial-port protection (udev + disable ModemManager)" OK
else
  log_step "[7/7] Serial-port protection (udev + disable ModemManager)" FAIL "$?"
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
# Helpful knobs for PTT testing
echo -e "${c_blue}Tips:${c_reset}"
echo -e "  • JS8Call/WSJT-X ‘Test PTT’ often sends no audio. The driver will auto-release PTT after silence." 
echo -e "  • Tuning knobs: --ptt-silence-timeout <seconds> and --silence-pp-threshold <0-255>."
echo -e "    Example: ./trusdx-txrx-AI.py -v --ptt-silence-timeout 1.5 --silence-pp-threshold 2"
echo
echo -e "${c_yellow}Note: If you were added to the dialout group, you may need to log out and back in.${c_reset}"
echo -e "${c_yellow}Note: To see the new ALSA devices, verify with: aplay -L | grep trusdx_${c_reset}"
echo
echo -e "For WSJT-X/JS8Call configuration:"
echo -e "  • Radio: Kenwood TS-480"
echo -e "  • Port: /tmp/trusdx_cat"
echo -e "  • Baud: 115200"
echo -e "  • Audio Input: ${c_green}pulse${c_reset} (then select ${c_green}TRUSDX.monitor${c_reset} in the system mixer)"
echo -e "  • Audio Output: ${c_green}pulse${c_reset} (then route to ${c_green}TRUSDX${c_reset} in the system mixer)"
echo -e "${c_yellow}Tip: Use 'pavucontrol' → Recording/Playback tabs to pick TRUSDX/TRUSDX.monitor for the apps${c_reset}"
echo -e "${c_yellow}Troubleshooting: If 'Loopback' card does not exist, run 'sudo modprobe snd-aloop' and reboot${c_reset}"

echo
read -rp "Press Enter to exit..."
