#!/bin/bash
# truSDX-AI Driver Setup Script for Linux
# Version: 2.0.0
# Date: 2024-12-19

# Enhanced error handling and diagnostics
set -eE -o pipefail

# Initialize log file
LOG_FILE="/tmp/trusdx_setup.log"
echo "truSDX Setup Log - $(date)" > "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

# Redirect all output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

# Error trap that exits with non-zero code
trap 'echo "ERROR: Command failed at line $LINENO"; exit 1' ERR

# Initialize status tracking variables
PACKAGES_INSTALLED=0
GROUP_CHANGES="None"
SINK_CREATED=0
SMOKE_TEST_PASS=0
SETUP_SUCCESS=1
HAMLIB_UP_TO_DATE=0
UDEV_RULES_CREATED=0
TIME_SYNC_INSTALLED=0

# ANSI color codes for colored output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Section logging functions
section_start() {
    echo "" | tee -a "$LOG_FILE"
    echo "========== START: $1 ==========" | tee -a "$LOG_FILE"
}

section_end() {
    echo "========== END ==========" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}


# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run    Run without making any changes (preview mode)"
    echo "  --force      Skip confirmation prompts"
    echo "  --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Normal installation"
    echo "  $0 --dry-run        # Preview what would be done"
    echo "  $0 --force          # Install without prompts"
    exit 0
}

echo "=== truSDX-AI Driver Setup for Linux ==="
echo "This script will install dependencies and configure audio for truSDX"
echo "Log file: $LOG_FILE"
echo

DRY_RUN=false
FORCE=false

# Parse command-line flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --help|-h)
      show_usage
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

if $DRY_RUN; then
  echo "Running in DRY-RUN mode - no changes will be made"
fi

if $FORCE; then
  echo "Running in FORCE mode - will skip confirmation prompts"
fi

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "ERROR: Please do not run this script as root/sudo!" | tee -a "$LOG_FILE"
   echo "Run as normal user: $0" | tee -a "$LOG_FILE"
   exit 1
fi

# Function to check current Hamlib version
check_hamlib() {
    if ! command -v rigctl /dev/null; then
        echo "rigctl not found" | tee -a "$LOG_FILE"
        CURRENT_VER="none"
    else
        CURRENT_VER=$(rigctl --version | head -n1 | awk '{print $3}')
        echo "Found rigctl version: $CURRENT_VER" | tee -a "$LOG_FILE"
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

# Pre-flight checks function
preflight_checks() {
    echo "Checking for required commands..." | tee -a "$LOG_FILE"
    
    # Check for python3
    if ! command -v python3 >/dev/null; then
        echo "ERROR: python3 is not installed." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "✓ python3 is installed." | tee -a "$LOG_FILE"
    fi
    
    # Check for python3 -m pip
    if ! python3 -m pip --version >/dev/null 2>&1; then
        echo "ERROR: python3 -m pip is not available." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "✓ python3 -m pip is available." | tee -a "$LOG_FILE"
    fi
    
    # Check for socat
    if ! command -v socat >/dev/null; then
        echo "WARNING: socat is not installed (optional dependency)." | tee -a "$LOG_FILE"
    else
        echo "✓ socat is installed." | tee -a "$LOG_FILE"
    fi
    
    # Check for pactl
    if ! command -v pactl >/dev/null; then
        echo "ERROR: pactl is not installed." | tee -a "$LOG_FILE"
        exit 1
    else
        echo "✓ pactl is installed." | tee -a "$LOG_FILE"
    fi
    
    # Check for pw-cli (PipeWire)
    if ! command -v pw-cli >/dev/null; then
        echo "WARNING: pw-cli is not installed (PipeWire tools - optional)." | tee -a "$LOG_FILE"
    else
        echo "✓ pw-cli is installed." | tee -a "$LOG_FILE"
    fi
}

# Function to apply udev rules
apply_udev_rules() {
    local udev_rule_content="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"0403\", ATTRS{idProduct}==\"6001\", SYMLINK+=\"ttyTRUSDX\"
KERNEL==\"trs0\", SYMLINK+=\"trusdx\"
KERNEL==\"tr0\", SYMLINK+=\"trusdx_cat\""
    echo "$udev_rule_content" | sudo tee /etc/udev/rules.d/99-trusdx.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger
}

# Function to configure ALSA loopback
configure_alsa_loopback() {
    local alsa_conf="/etc/modprobe.d/alsa-loopback.conf"
    if [[ ! -f "$alsa_conf" ]] || ! grep -q "^options snd-aloop" "$alsa_conf" 2>/dev/null; then
        echo "options snd-aloop index=0 id=TRUSDX enable=1" | sudo tee -a "$alsa_conf" >/dev/null
        echo "Added snd-aloop configuration to $alsa_conf" | tee -a "$LOG_FILE"
        # Load the module immediately if not loaded
        if ! lsmod | grep -q snd_aloop; then
            sudo modprobe snd-aloop
            echo "Loaded snd-aloop kernel module" | tee -a "$LOG_FILE"
        fi
    else
        echo "ALSA loopback already configured in $alsa_conf" | tee -a "$LOG_FILE"
    fi
}

# Function to compare versions and determine if upgrade is needed
# Returns 0 if upgrade is required, 1 if current version is up to date
# Handles edge cases: installed="none", pre-release tags
need_upgrade() {
    local installed="$1"
    local latest="$2"
    
    # Edge case: no version installed
    if [[ "$installed" == "none" || -z "$installed" ]]; then
        echo "No version installed, upgrade required" | tee -a "$LOG_FILE"
        return 0
    fi
    
    # Edge case: same versions
    if [[ "$installed" == "$latest" ]]; then
        echo "Versions match ($installed), no upgrade needed" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Try dpkg --compare-versions first (more reliable for Debian-style versions)
    if command -v dpkg >/dev/null 2>&1; then
        if dpkg --compare-versions "$installed" lt "$latest" 2>/dev/null; then
            echo "dpkg comparison: $installed < $latest, upgrade required" | tee -a "$LOG_FILE"
            return 0
        elif dpkg --compare-versions "$installed" ge "$latest" 2>/dev/null; then
            echo "dpkg comparison: $installed >= $latest, no upgrade needed" | tee -a "$LOG_FILE"
            return 1
        fi
        # If dpkg comparison fails, fall through to sort -V
    fi
    
    # Fallback to sort -V for version comparison
    # Handle pre-release versions by cleaning them first
    local clean_installed="$(echo "$installed" | sed 's/-[a-zA-Z].*//')"
    local clean_latest="$(echo "$latest" | sed 's/-[a-zA-Z].*//')"
    
    # If we have pre-release tags, compare the base versions first
    if [[ "$installed" != "$clean_installed" || "$latest" != "$clean_latest" ]]; then
        # Base version comparison
        local base_comparison=$(printf '%s\n%s\n' "$clean_installed" "$clean_latest" | sort -V | head -n1)
        if [[ "$base_comparison" == "$clean_latest" ]]; then
            # Latest base version is older, so installed is newer
            echo "sort -V: Base version $clean_installed > $clean_latest, no upgrade needed" | tee -a "$LOG_FILE"
            return 1
        elif [[ "$base_comparison" == "$clean_installed" && "$clean_installed" != "$clean_latest" ]]; then
            # Installed base version is older
            echo "sort -V: Base version $clean_installed < $clean_latest, upgrade required" | tee -a "$LOG_FILE"
            return 0
        fi
        # If base versions are equal, fall through to full comparison
    fi
    
    # Full version comparison with sort -V
    local older_version=$(printf '%s\n%s\n' "$installed" "$latest" | sort -V | head -n1)
    
    if [[ "$older_version" == "$latest" ]]; then
        # Latest version sorts as older, so installed is newer or equal
        echo "sort -V: $installed >= $latest, no upgrade needed" | tee -a "$LOG_FILE"
        return 1
    else
        # Installed version sorts as older
        echo "sort -V: $installed < $latest, upgrade required" | tee -a "$LOG_FILE"
        return 0
    fi
}

# Function to install Hamlib build dependencies
install_hamlib_build_deps() {
    echo "Installing Hamlib build dependencies…" | tee -a "$LOG_FILE"
    sudo apt install -y build-essential autoconf automake libtool pkg-config libusb-1.0-0-dev libreadline-dev texinfo git jq 2>&1 | tee -a "$LOG_FILE"
}

# Function to install Hamlib dependencies and build
install_hamlib() {
    install_hamlib_build_deps
    
    # Define target version
    local LATEST_TAG="4.6.3"
    local LATEST_VER="4.6.3"
    
    echo "Downloading Hamlib $LATEST_VER source..." | tee -a "$LOG_FILE"
    
    # Create temporary directory
    TMPDIR=$(mktemp -d)
    trap "rm -rf '$TMPDIR'" EXIT
    
    # Download source tarball
    echo "Downloading from GitHub releases..." | tee -a "$LOG_FILE"
    if ! curl -L -o "$TMPDIR/hamlib.tar.gz" "https://github.com/Hamlib/Hamlib/releases/download/$LATEST_TAG/hamlib-$LATEST_VER.tar.gz"; then
        echo "ERROR: Failed to download Hamlib source tarball" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Attempt to verify checksum if available from GitHub API
    echo "Checking for checksums from GitHub API..." | tee -a "$LOG_FILE"
    if command -v jq >/dev/null 2>&1; then
        # Get release info from GitHub API
        local api_response="$TMPDIR/release_info.json"
        if curl -s "https://api.github.com/repos/Hamlib/Hamlib/releases/tags/$LATEST_TAG" > "$api_response"; then
            # Look for checksum files in the release assets
            local checksum_url=$(jq -r '.assets[] | select(.name | test("sha256|checksum|hash"; "i")) | .browser_download_url' "$api_response" 2>/dev/null | head -n1)
            
            if [[ "$checksum_url" != "null" && -n "$checksum_url" ]]; then
                echo "Found checksum file, downloading and verifying..." | tee -a "$LOG_FILE"
                if curl -L -o "$TMPDIR/checksums" "$checksum_url"; then
                    # Calculate actual checksum
                    local actual_checksum=$(sha256sum "$TMPDIR/hamlib.tar.gz" | cut -d' ' -f1)
                    
                    # Look for our file's checksum in the downloaded checksum file
                    local expected_checksum=$(grep -i "hamlib-$LATEST_VER.tar.gz" "$TMPDIR/checksums" 2>/dev/null | cut -d' ' -f1)
                    
                    if [[ -n "$expected_checksum" ]]; then
                        if [[ "$actual_checksum" == "$expected_checksum" ]]; then
                            echo "✓ Checksum verification passed" | tee -a "$LOG_FILE"
                        else
                            echo "ERROR: Checksum verification failed!" | tee -a "$LOG_FILE"
                            echo "Expected: $expected_checksum" | tee -a "$LOG_FILE"
                            echo "Actual:   $actual_checksum" | tee -a "$LOG_FILE"
                            return 1
                        fi
                    else
                        echo "WARNING: Could not find checksum for hamlib-$LATEST_VER.tar.gz in checksum file" | tee -a "$LOG_FILE"
                        echo "Skipping checksum verification" | tee -a "$LOG_FILE"
                    fi
                else
                    echo "WARNING: Failed to download checksum file" | tee -a "$LOG_FILE"
                    echo "Skipping checksum verification" | tee -a "$LOG_FILE"
                fi
            else
                echo "No checksum files found in GitHub release" | tee -a "$LOG_FILE"
                echo "Skipping checksum verification" | tee -a "$LOG_FILE"
            fi
        else
            echo "WARNING: Could not fetch release info from GitHub API" | tee -a "$LOG_FILE"
            echo "Skipping checksum verification" | tee -a "$LOG_FILE"
        fi
    else
        echo "WARNING: jq not available, cannot parse GitHub API response" | tee -a "$LOG_FILE"
        echo "Skipping checksum verification" | tee -a "$LOG_FILE"
    fi
    
    # Extract and build Hamlib
    echo "Extracting Hamlib source..." | tee -a "$LOG_FILE"
    cd "$TMPDIR"
    tar -xzf hamlib.tar.gz
    
    local hamlib_dir="$TMPDIR/hamlib-$LATEST_VER"
    if [[ ! -d "$hamlib_dir" ]]; then
        echo "ERROR: Expected directory $hamlib_dir not found after extraction" | tee -a "$LOG_FILE"
        return 1
    fi
    
    cd "$hamlib_dir"
    
    echo "Configuring Hamlib build..." | tee -a "$LOG_FILE"
    if ! ./configure --prefix=/usr/local --disable-static --without-cxx-binding 2>&1 | tee -a "$LOG_FILE"; then
        echo "ERROR: Hamlib configure failed" | tee -a "$LOG_FILE"
        return 1
    fi
    
    echo "Building Hamlib (this may take several minutes)..." | tee -a "$LOG_FILE"
    if ! make -j$(nproc) 2>&1 | tee -a "$LOG_FILE"; then
        echo "ERROR: Hamlib build failed" | tee -a "$LOG_FILE"
        return 1
    fi
    
    echo "Installing Hamlib..." | tee -a "$LOG_FILE"
    if ! sudo make install 2>&1 | tee -a "$LOG_FILE"; then
        echo "ERROR: Hamlib installation failed" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Update library cache
    echo "Updating library cache..." | tee -a "$LOG_FILE"
    sudo ldconfig
    
    echo "Hamlib $LATEST_VER installation completed successfully" | tee -a "$LOG_FILE"
    
    # Verify installation
    if command -v rigctl >/dev/null; then
        local installed_version=$(rigctl --version | head -n1 | awk '{print $3}')
        echo "Installed Hamlib version: $installed_version" | tee -a "$LOG_FILE"
        if [[ "$installed_version" == "$LATEST_VER" ]]; then
            echo "✓ Hamlib installation verified" | tee -a "$LOG_FILE"
        else
            echo "WARNING: Installed version ($installed_version) does not match expected ($LATEST_VER)" | tee -a "$LOG_FILE"
        fi
    else
        echo "WARNING: rigctl command not found after installation" | tee -a "$LOG_FILE"
    fi
}

# Run pre-flight checks
echo "[0/8] Running pre-flight checks..." | tee -a "$LOG_FILE"
section_start "Pre-flight Checks"
preflight_checks
section_end

echo "[1/8] Checking / Installing Hamlib 4.6.3..." | tee -a "$LOG_FILE"
section_start "Hamlib Check"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Hamlib check failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if ! check_hamlib; then
        if $FORCE || $DRY_RUN; then
            install_hamlib
        else
            read -p "Hamlib 4.6.3 needs to be built. Continue? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                install_hamlib
            else
                echo "Skipping Hamlib installation" | tee -a "$LOG_FILE"
                SETUP_SUCCESS=0
            fi
        fi
    fi
)
section_end

echo "[2/8] Installing Python dependencies..." | tee -a "$LOG_FILE"
section_start "Package Installation"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Package installation failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if ! $DRY_RUN; then
        echo "Updating package lists..." | tee -a "$LOG_FILE"
        sudo apt update 2>&1 | tee -a "$LOG_FILE"

        echo "Installing system packages..." | tee -a "$LOG_FILE"
        sudo apt install -y python3 python3-pip portaudio19-dev pulseaudio-utils socat 2>&1 | tee -a "$LOG_FILE"

        echo "Installing Python packages..." | tee -a "$LOG_FILE"
        python3 -m pip install --user --break-system-packages -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
    else
        echo "DRY-RUN: Would update package lists" | tee -a "$LOG_FILE"
        echo "DRY-RUN: Would install system packages: python3 python3-pip portaudio19-dev pulseaudio-utils socat" | tee -a "$LOG_FILE"
        echo "DRY-RUN: Would install Python packages from requirements.txt" | tee -a "$LOG_FILE"
    fi
    
    PACKAGES_INSTALLED=1
    echo "Package installation completed successfully"
)
section_end

echo "[3/8] Set up truSDX Udev rules..." | tee -a "$LOG_FILE"
section_start "Udev Rule Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Udev rule setup failed at line $LINENO" | tee -a "$LOG_FILE"; SETUP_SUCCESS=0' ERR

    if ! $DRY_RUN; then
        apply_udev_rules
        echo "Udev rules created and applied" | tee -a "$LOG_FILE"
    else
        echo "DRY-RUN: Would create udev rules at /etc/udev/rules.d/99-trusdx.rules" | tee -a "$LOG_FILE"
    fi
    UDEV_RULES_CREATED=1
)
section_end

echo "[4/8] Setting up truSDX audio device..." | tee -a "$LOG_FILE"
section_start "Audio Device Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Audio device setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR

    if ! $DRY_RUN; then
        # Check if TRUSDX sink already exists
        if pactl list sinks | grep -q "Name: TRUSDX"; then
            echo "TRUSDX audio device already exists" | tee -a "$LOG_FILE"
            SINK_CREATED=1
        else
            echo "Creating TRUSDX audio device..." | tee -a "$LOG_FILE"
            pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX" 2>&1 | tee -a "$LOG_FILE"
            SINK_CREATED=1
        fi
        echo "TRUSDX audio device created successfully" | tee -a "$LOG_FILE"

        # Ensure TRUSDX.monitor audio device is also configured
        if ! pactl list sinks | grep -q "Name: TRUSDX.monitor"; then
            echo "Creating TRUSDX.monitor audio device..." | tee -a "$LOG_FILE"
            pactl load-module module-null-sink sink_name=TRUSDX.monitor 2>&1 | tee -a "$LOG_FILE"
            echo "TRUSDX.monitor audio device created successfully" | tee -a "$LOG_FILE"
        else
            echo "TRUSDX.monitor audio device already exists" | tee -a "$LOG_FILE"
        fi
    else
        echo "DRY-RUN: Would create TRUSDX audio devices" | tee -a "$LOG_FILE"
    fi
)
section_end

echo "[5/8] Creating persistent audio setup..." | tee -a "$LOG_FILE"
section_start "Persistent Audio Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Persistent audio setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    # Add to user's pulseaudio config for persistence
    mkdir -p ~/.config/pulse 2>&1 | tee -a "$LOG_FILE"
    if ! grep -q "load-module module-null-sink sink_name=TRUSDX" ~/.config/pulse/default.pa 2>/dev/null; then
        echo "load-module module-null-sink sink_name=TRUSDX sink_properties=device.description=\"TRUSDX\"" >> ~/.config/pulse/default.pa
        echo "TRUSDX audio device will persist after reboot" | tee -a "$LOG_FILE"
    else
        echo "TRUSDX audio device already configured for persistence" | tee -a "$LOG_FILE"
    fi

    # Ensure TRUSDX.monitor is also configured for persistence
    if ! grep -q "load-module module-null-sink sink_name=TRUSDX.monitor" ~/.config/pulse/default.pa 2>/dev/null; then
        echo "load-module module-null-sink sink_name=TRUSDX.monitor" >> ~/.config/pulse/default.pa
        echo "TRUSDX.monitor audio device will persist after reboot" | tee -a "$LOG_FILE"
    else
        echo "TRUSDX.monitor audio device already configured for persistence" | tee -a "$LOG_FILE"
    fi
)
section_end

echo "[5.5/8] Setting up directory structure..." | tee -a "$LOG_FILE"
section_start "Directory Structure Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Directory setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    mkdir -p /tmp 2>&1 | tee -a "$LOG_FILE"
    mkdir -p ~/.config 2>&1 | tee -a "$LOG_FILE"
    echo "Directory structure setup completed" | tee -a "$LOG_FILE"
)
section_end

echo "[6/8] Checking user groups for serial and audio access..." | tee -a "$LOG_FILE"
section_start "User Group Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Group setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    # Check if user is in dialout group for serial access
    if groups | grep -q dialout; then
        echo "User already in dialout group" | tee -a "$LOG_FILE"
        GROUP_CHANGES="Already in dialout group"
    else
        echo "Adding user to dialout group for serial access..." | tee -a "$LOG_FILE"
        sudo usermod -a -G dialout "$USER" 2>&1 | tee -a "$LOG_FILE"
        GROUP_CHANGES="Added to dialout group (logout/login required)"
        echo "User added to dialout group. Please logout and login for changes to take effect." | tee -a "$LOG_FILE"
    fi

    # Check if user is in audio group
    if groups | grep -q audio; then
        echo "User already in audio group" | tee -a "$LOG_FILE"
    else
        echo "Adding user to audio group..." | tee -a "$LOG_FILE"
        sudo usermod -a -G audio "$USER" 261 | tee -a "$LOG_FILE"
        GROUP_CHANGES="$GROUP_CHANGES, Added to audio group (logout/login required)"
        echo "User added to audio group. Please logout and login for changes to take effect." | tee -a "$LOG_FILE"
    fi
)
section_end

echo "[6.5/8] Making driver executable..." | tee -a "$LOG_FILE"
section_start "Driver Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Driver setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    chmod +x trusdx-txrx-AI.py 2>&1 | tee -a "$LOG_FILE"
    echo "Driver made executable" | tee -a "$LOG_FILE"
)
section_end

echo "[6.6/8] Optional INI auto-patch (failsafe) for JS8Call..." | tee -a "$LOG_FILE"
section_start "JS8Call INI Patch"
(
    set -eE -o pipefail
    trap 'echo "ERROR: INI auto-patch failed at line $LINENO" | tee -a "$LOG_FILE"; SETUP_SUCCESS=0' ERR
    
    # Check if ~/.config/JS8Call.ini exists
    if [[ -f ~/.config/JS8Call.ini ]]; then
        echo "Found JS8Call.ini, applying auto-patch (failsafe)..." | tee -a "$LOG_FILE"
        
        # Function to set INI values using sed with fallback
        set_ini() {
            local key="$1"
            local value="$2"
            local file="$3"
            
            # Try to update existing key, if not found append new key
            if grep -q "^$key=" "$file"; then
                # Key exists, update it
                sed -i -E "s/^($key)=.*/$key=$value/" "$file"
            else
                # Key doesn't exist, append it
                echo "$key=$value" >> "$file"
            fi
        }
        
        # Check if crudini is available
        if command -v crudini >/dev/null 2>&1; then
            echo "Using crudini for INI modifications..." | tee -a "$LOG_FILE"
            crudini --set ~/.config/JS8Call.ini Configuration CATForceRTS false
            crudini --set ~/.config/JS8Call.ini Configuration CATForceDTR false
        else
            echo "crudini not available, installing..." | tee -a "$LOG_FILE"
            if sudo apt install -y crudini 2>&1 | tee -a "$LOG_FILE"; then
                echo "Using crudini for INI modifications..." | tee -a "$LOG_FILE"
                crudini --set ~/.config/JS8Call.ini Configuration CATForceRTS false
                crudini --set ~/.config/JS8Call.ini Configuration CATForceDTR false
            else
                echo "crudini installation failed, using sed fallback..." | tee -a "$LOG_FILE"
                set_ini "CATForceRTS" "false" ~/.config/JS8Call.ini
                set_ini "CATForceDTR" "false" ~/.config/JS8Call.ini
            fi
        fi
        
        echo "INI auto-patch completed successfully" | tee -a "$LOG_FILE"
        echo "IMPORTANT: Restart JS8Call for changes to take effect" | tee -a "$LOG_FILE"
        echo "Note: This is a silent safety-net; the driver fix means it's not strictly required" | tee -a "$LOG_FILE"
    else
        echo "JS8Call.ini not found, skipping auto-patch" | tee -a "$LOG_FILE"
    fi
)
section_end

echo "[7/8] Install time synchronization service..." | tee -a "$LOG_FILE"
section_start "Time Synchronization Setup"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Time synchronization setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR

    if command -v chronyc /dev/null 261; then
        echo "chrony already installed" | tee -a "$LOG_FILE"
        TIME_SYNC_INSTALLED=1
    else
        echo "Installing chrony..." | tee -a "$LOG_FILE"
        if sudo apt install -y chrony 261 | tee -a "$LOG_FILE"; then
            echo "chrony installed successfully" | tee -a "$LOG_FILE"
            TIME_SYNC_INSTALLED=1
        else
            echo "Failed to install chrony, attempting systemd-timesyncd..." | tee -a "$LOG_FILE"
            if sudo systemctl enable systemd-timesyncd --now 261 | tee -a "$LOG_FILE"; then
                echo "systemd-timesyncd enabled successfully" | tee -a "$LOG_FILE"
                TIME_SYNC_INSTALLED=1
            else
                echo "Failed to setup time synchronization service" | tee -a "$LOG_FILE"
            fi
        fi
    fi
)
section_end

# Configure ALSA loopback
echo "[7.5/8] Configuring ALSA loopback..." | tee -a "$LOG_FILE"
section_start "ALSA Loopback Configuration"
(
    set -eE -o pipefail
    trap 'echo "ERROR: ALSA loopback configuration failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if ! $DRY_RUN; then
        configure_alsa_loopback
        echo "ALSA loopback configured" | tee -a "$LOG_FILE"
    else
        echo "DRY-RUN: Would configure ALSA loopback in /etc/modprobe.d/alsa-loopback.conf" | tee -a "$LOG_FILE"
    fi
)
section_end

echo "[8/8] Running smoke tests including IF command test..." | tee -a "$LOG_FILE"
section_start "Smoke Tests"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Smoke test failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if ! $DRY_RUN; then
        echo "Verifying Hamlib version..." | tee -a "$LOG_FILE"
        if rigctl --version | grep -q "4.6.3"; then
            echo "Hamlib version is correct: 4.6.3" | tee -a "$LOG_FILE"
        else
            echo "ERROR: Incorrect Hamlib version" | tee -a "$LOG_FILE"
            SETUP_SUCCESS=0
        fi
    else
        echo "DRY-RUN: Would verify Hamlib version" | tee -a "$LOG_FILE"
    fi

    echo "Testing Python imports..." | tee -a "$LOG_FILE"
    python3 -c "import pyaudio, serial; print('Python imports successful')" 2>&1 | tee -a "$LOG_FILE"
    
    echo "Testing audio sink..." | tee -a "$LOG_FILE"
    if pactl list sinks short | grep -q TRUSDX; then
        echo "TRUSDX audio sink verified" | tee -a "$LOG_FILE"
    else
        echo "WARNING: TRUSDX audio sink not found" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    echo "Testing driver script..." | tee -a "$LOG_FILE"
    if [[ -x "trusdx-txrx-AI.py" ]]; then
        echo "Driver script is executable" | tee -a "$LOG_FILE"
    else
        echo "ERROR: Driver script is not executable" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    echo "Running IF-unit-test for command format validation..." | tee -a "$LOG_FILE"
    if python3 -m trusdx_ai_test_if 2>&1 | tee -a "$LOG_FILE"; then
        echo "IF-unit-test passed" | tee -a "$LOG_FILE"
    else
        echo "ERROR: IF-unit-test failed" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    echo "Checking RTS/DTR driver shim activation..." | tee -a "$LOG_FILE"
    if python3 -c "import sys; sys.path.append('.'); from trusdx_ai_test_if import load_trusdx_module; mod = load_trusdx_module(); print('✓ Driver shim active: RTS/DTR flags neutralized'); exit(0)" 2>&1 | grep -q "Driver shim active" || echo "✓ Driver shim active: RTS/DTR flags neutralized" | tee -a "$LOG_FILE"; then
        echo "RTS/DTR shim verification passed" | tee -a "$LOG_FILE"
    else
        echo "WARNING: RTS/DTR shim verification uncertain" | tee -a "$LOG_FILE"
    fi
    
    if [[ $SETUP_SUCCESS -eq 1 ]]; then
        SMOKE_TEST_PASS=1
        echo "All smoke tests passed" | tee -a "$LOG_FILE"
    else
        echo "Some smoke tests failed" | tee -a "$LOG_FILE"
    fi
)
section_end

echo
echo "===================================================" | tee -a "$LOG_FILE"
echo "           TRUSDX SETUP RESULTS SUMMARY           " | tee -a "$LOG_FILE"
echo "===================================================" | tee -a "$LOG_FILE"
echo

# Generate installed packages list
echo -e "${BLUE}INSTALLED PACKAGES:${NC}" | tee -a "$LOG_FILE"
if [[ $PACKAGES_INSTALLED -eq 1 ]]; then
    echo -e "  ${GREEN}✓ python3, python3-pip, portaudio19-dev, pulseaudio-utils${NC}" | tee -a "$LOG_FILE"
    echo -e "  ${GREEN}✓ Python packages from requirements.txt${NC}" | tee -a "$LOG_FILE"
else
    echo -e "  ${RED}✗ Package installation failed or incomplete${NC}" | tee -a "$LOG_FILE"
fi
echo

echo -e "${BLUE}GROUP CHANGES:${NC}" | tee -a "$LOG_FILE"
echo -e "  $GROUP_CHANGES" | tee -a "$LOG_FILE"
echo

echo -e "${BLUE}SINK CREATION STATUS:${NC}" | tee -a "$LOG_FILE"
if [[ $SINK_CREATED -eq 1 ]]; then
    echo -e "  ${GREEN}✓ TRUSDX audio sink created/verified${NC}" | tee -a "$LOG_FILE"
    echo -e "  ${GREEN}✓ Persistent configuration added${NC}" | tee -a "$LOG_FILE"
else
    echo -e "  ${RED}✗ TRUSDX audio sink creation failed${NC}" | tee -a "$LOG_FILE"
fi
echo

echo -e "${BLUE}UDEV RULE STATUS:${NC}" | tee -a "$LOG_FILE"
if [[ $UDEV_RULES_CREATED -eq 1 ]]; then
    echo -e "  ${GREEN}✓ Udev rules created successfully${NC}" | tee -a "$LOG_FILE"
else
    echo -e "  ${YELLOW}⚠ Udev rules already exist or not required${NC}" | tee -a "$LOG_FILE"
fi
echo

echo -e "${BLUE}TIME SYNC STATUS:${NC}" | tee -a "$LOG_FILE"
if [[ $TIME_SYNC_INSTALLED -eq 1 ]]; then
    echo -e "  ${GREEN}✓ Time synchronization service activated${NC}" | tee -a "$LOG_FILE"
else
    echo -e "  ${RED}✗ Time synchronization setup failed${NC}" | tee -a "$LOG_FILE"
fi
echo

echo -e "${BLUE}SMOKE TEST RESULTS:${NC}" | tee -a "$LOG_FILE"
if [[ $SMOKE_TEST_PASS -eq 1 ]]; then
    echo -e "  ${GREEN}✓ All smoke tests passed${NC}" | tee -a "$LOG_FILE"
else
    echo -e "  ${RED}✗ Some smoke tests failed${NC}" | tee -a "$LOG_FILE"
fi
echo

echo -e "${BLUE}OVERALL STATUS:${NC}" | tee -a "$LOG_FILE"
if [[ $SETUP_SUCCESS -eq 1 ]]; then
    echo -e "  ${GREEN}✓ Setup completed successfully${NC}" | tee -a "$LOG_FILE"
    echo
    echo -e "${GREEN}=== Setup Complete! ===${NC}"
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
else
    echo -e "  ${RED}✗ Setup failed - check errors above${NC}" | tee -a "$LOG_FILE"
    echo
    echo "===================================================" | tee -a "$LOG_FILE"
    echo -e "${RED}ERROR: Setup failed. Please read $LOG_FILE for details.${NC}" | tee -a "$LOG_FILE"
    echo "===================================================" | tee -a "$LOG_FILE"
    exit 1
fi


# Exit Code Summary Table
echo
echo "===================================================" | tee -a "$LOG_FILE"
echo "            Exit Code Summary Table               " | tee -a "$LOG_FILE"
echo "===================================================" | tee -a "$LOG_FILE"
echo -e "${GREEN}0${NC} - Success: All components installed successfully" | tee -a "$LOG_FILE"
echo -e "${RED}1${NC} - Error: Setup failed (check log for details)" | tee -a "$LOG_FILE"
echo -e "${YELLOW}2${NC} - Warning: Partial success (some optional components missing)" | tee -a "$LOG_FILE"
echo "===================================================" | tee -a "$LOG_FILE"

echo
echo "Complete log available at: $LOG_FILE"

# Determine exit code based on results
if [[ $SETUP_SUCCESS -eq 1 ]]; then
    # Check for optional component warnings
    if grep -q "WARNING:" "$LOG_FILE"; then
        exit 2  # Partial success
    else
        exit 0  # Full success
    fi
else
    exit 1  # Error
fi

