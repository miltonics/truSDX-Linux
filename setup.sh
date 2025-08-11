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
    echo -e "${c_blue}[1/5] Installing system packages...${c_reset}"
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
  log_step "[1/5] Installing system packages" OK
else
  log_step "[1/5] Installing system packages" FAIL "$?"
fi

# Install Python packages using apt (preferred for system packages)
if (
  echo -e "${c_blue}[2/5] Installing Python packages...${c_reset}"
  sudo apt-get install -y python3-serial python3-pyaudio
); then
  log_step "[2/5] Installing Python packages" OK
else
  log_step "[2/5] Installing Python packages" FAIL "$?"
fi

# Add user to dialout group for serial port access
if (
  echo -e "${c_blue}[3/5] Adding user to dialout group...${c_reset}"
  if ! groups | grep -q dialout; then
    sudo usermod -a -G dialout $USER
    echo -e "${c_green}Added $USER to dialout group. You may need to log out and back in for this to take effect.${c_reset}"
  else
    echo -e "${c_green}User already in dialout group.${c_reset}"
  fi
); then
  log_step "[3/5] Adding user to dialout group" OK
else
  log_step "[3/5] Adding user to dialout group" FAIL "$?"
fi

# Setup ALSA Loopback
if (
  echo -e "${c_blue}[4/5] Setting up ALSA loopback...${c_reset}"
  # Load snd-aloop module for ALSA loopback
  if ! lsmod | grep -q "^snd_aloop"; then
    sudo modprobe snd-aloop
    echo -e "${c_green}Loaded ALSA loopback module.${c_reset}"
    # Make it persistent across reboots
    echo "snd-aloop" | sudo tee -a /etc/modules >/dev/null
    echo -e "${c_green}Added snd-aloop to auto-load on boot.${c_reset}"
  else
    echo -e "${c_green}ALSA loopback module already loaded.${c_reset}"
  fi

  # Create or update ~/.asoundrc with trusdx PCM devices
  ASRC_FILE="${HOME}/.asoundrc"
  echo -e "${c_blue}Configuring ALSA PCM devices...${c_reset}"

  # Check if trusdx_tx and trusdx_rx are already configured
  if [[ -f "${ASRC_FILE}" ]]; then
    if grep -q "trusdx_tx" "${ASRC_FILE}"; then
      if grep -q "trusdx_rx" "${ASRC_FILE}"; then
        echo -e "${c_green}ALSA PCM devices already configured.${c_reset}"
      else
        NEEDS_CONFIG=1
      fi
    else
      NEEDS_CONFIG=1
    fi
  else
    NEEDS_CONFIG=1
  fi
  
  if [[ "${NEEDS_CONFIG}" == "1" ]]; then
    # Backup existing .asoundrc if it exists
    if [[ -f "${ASRC_FILE}" ]]; then
      cp "${ASRC_FILE}" "${ASRC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
      echo -e "${c_yellow}Backed up existing .asoundrc${c_reset}"
    fi
    
    # Append trusdx PCM configuration
    cat >> "${ASRC_FILE}" <<'ALSA'

# truSDX-AI ALSA PCM devices
pcm.trusdx_tx {
    type plug
    slave.pcm "hw:Loopback,0,0"
}

pcm.trusdx_rx {
    type plug
    slave.pcm "hw:Loopback,1,0"
}

# Application-friendly aliases
pcm.trusdx_tx_app {
    type plug
    slave.pcm "hw:Loopback,0,0"
}

pcm.trusdx_rx_app {
    type plug
    slave.pcm "hw:Loopback,1,0"
}
ALSA
    
    echo -e "${c_green}Created ALSA PCM devices: trusdx_tx, trusdx_rx, trusdx_tx_app, and trusdx_rx_app${c_reset}"
    
    # Restore ALSA settings
    alsactl restore 2>/dev/null || true
    
    echo -e "${c_yellow}Note: You may need to logout and login for the new PCM devices to appear in all applications.${c_reset}"
  fi
); then
  log_step "[4/5] Setting up ALSA loopback" OK
else
  log_step "[4/5] Setting up ALSA loopback" FAIL "$?"
fi

# Create default config file
if (
  echo -e "${c_blue}[5/5] Creating configuration...${c_reset}"
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
  log_step "[5/5] Creating configuration" OK
else
  log_step "[5/5] Creating configuration" FAIL "$?"
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
echo -e "  • Audio Input: trusdx_rx_app (or hw:Loopback,1,0)"
echo -e "  • Audio Output: trusdx_tx_app (or hw:Loopback,0,0)"
echo -e "${c_yellow}Troubleshooting: If hw:Loopback does not exist, run 'sudo modprobe snd-aloop' and reboot${c_reset}"

echo
read -rp "Press Enter to exit..."
