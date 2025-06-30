#!/bin/bash
# truSDX-AI Driver Setup Script for Linux
# Version: 1.1.7-AI
# Date: 2024-12-19
# Requires: socat

# Enhanced error handling and diagnostics
set -eE -o pipefail
trap 'echo "ERROR: Command failed at line $LINENO" | tee -a /tmp/trusdx_setup.log; exit 1' ERR

# Initialize log file
LOG_FILE="/tmp/trusdx_setup.log"
echo "truSDX Setup Log - $(date)" > "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

# Initialize status tracking variables
PACKAGES_INSTALLED=0
GROUP_CHANGES="None"
SINK_CREATED=0
SMOKE_TEST_PASS=0
SETUP_SUCCESS=1
HAMLIB_UP_TO_DATE=0

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
    if command -v rigctl >/dev/null; then
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

# Function to check if socat is available
check_socat() {
    if command -v socat >/dev/null; then
        echo "socat is present" | tee -a "$LOG_FILE"
        return 0
    else
        echo "socat not found, will install" | tee -a "$LOG_FILE"
        return 1
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
    local LATEST_TAG="hamlib-4.6.3"
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

echo "[1/6] Checking / Installing Hamlib 4.6.3..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Hamlib check failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    if ! check_hamlib; then
        install_hamlib
    fi
)

echo "[2/6] Installing Python dependencies..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Package installation failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    echo "Updating package lists..." | tee -a "$LOG_FILE"
    sudo apt update 2>&1 | tee -a "$LOG_FILE"
    
    echo "Installing system packages..." | tee -a "$LOG_FILE"
    sudo apt install -y python3 python3-pip portaudio19-dev pulseaudio-utils socat 2>&1 | tee -a "$LOG_FILE"
    
    # Check and install socat if not present
    if ! command -v socat >/dev/null; then
        echo "installing socat" | tee -a "$LOG_FILE"
        sudo apt install -y socat 2>&1 | tee -a "$LOG_FILE"
    else
        echo "socat present" | tee -a "$LOG_FILE"
    fi
    
    echo "Installing Python packages..." | tee -a "$LOG_FILE"
    pip3 install --user pyaudio pyserial 2>&1 | tee -a "$LOG_FILE"
    
    PACKAGES_INSTALLED=1
    echo "Package installation completed successfully" | tee -a "$LOG_FILE"
)

echo "[3/6] Setting up truSDX audio device..." | tee -a "$LOG_FILE"
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
)

echo "[4/6] Creating persistent audio setup..." | tee -a "$LOG_FILE"
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
)

echo "[5/6] Setting up directory structure..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Directory setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    mkdir -p /tmp 2>&1 | tee -a "$LOG_FILE"
    mkdir -p ~/.config 2>&1 | tee -a "$LOG_FILE"
    echo "Directory structure setup completed" | tee -a "$LOG_FILE"
)

echo "[5.5/6] Checking user groups for serial access..." | tee -a "$LOG_FILE"
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
)

echo "[6/6] Making driver executable..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Driver setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    chmod +x trusdx-txrx-AI.py 2>&1 | tee -a "$LOG_FILE"
    echo "Driver made executable" | tee -a "$LOG_FILE"
)

echo "[6.1/6] Making bridge helper scripts executable..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Bridge script setup failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
    chmod +x hamlib_bridge.sh create_serial_bridge.sh 2>&1 | tee -a "$LOG_FILE"
    echo "Bridge helper scripts made executable" | tee -a "$LOG_FILE"
)

echo "[6.5/6] Running smoke tests..." | tee -a "$LOG_FILE"
(
    set -eE -o pipefail
    trap 'echo "ERROR: Smoke test failed at line $LINENO" | tee -a "'$LOG_FILE'"; SETUP_SUCCESS=0' ERR
    
echo "Verifying Hamlib version..." | tee -a "$LOG_FILE"
    if rigctl --version | grep -q "4.6.3"; then
        echo "Hamlib version is correct: 4.6.3" | tee -a "$LOG_FILE"
    else
        echo "ERROR: Incorrect Hamlib version" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
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
    
    echo "Verifying socat installation..." | tee -a "$LOG_FILE"
    if command -v socat >/dev/null; then
        echo "socat OK: $(socat -V | head -n1)" | tee -a "$LOG_FILE"
    else
        echo "ERROR: socat not found" | tee -a "$LOG_FILE"
        SETUP_SUCCESS=0
    fi
    
    if [[ $SETUP_SUCCESS -eq 1 ]]; then
        SMOKE_TEST_PASS=1
        echo "All smoke tests passed" | tee -a "$LOG_FILE"
    else
        echo "Some smoke tests failed" | tee -a "$LOG_FILE"
    fi
)

echo
echo "===================================================" | tee -a "$LOG_FILE"
echo "           TRUSDX SETUP RESULTS SUMMARY           " | tee -a "$LOG_FILE"
echo "===================================================" | tee -a "$LOG_FILE"
echo

# Generate installed packages list
echo "INSTALLED PACKAGES:" | tee -a "$LOG_FILE"
if [[ $PACKAGES_INSTALLED -eq 1 ]]; then
    echo "  ✓ python3, python3-pip, portaudio19-dev, pulseaudio-utils, socat" | tee -a "$LOG_FILE"
    echo "  ✓ Python packages: pyaudio, pyserial" | tee -a "$LOG_FILE"
else
    echo "  ✗ Package installation failed or incomplete" | tee -a "$LOG_FILE"
fi
echo

echo "GROUP CHANGES:" | tee -a "$LOG_FILE"
echo "  $GROUP_CHANGES" | tee -a "$LOG_FILE"
echo

echo "SINK CREATION STATUS:" | tee -a "$LOG_FILE"
if [[ $SINK_CREATED -eq 1 ]]; then
    echo "  ✓ TRUSDX audio sink created/verified" | tee -a "$LOG_FILE"
    echo "  ✓ Persistent configuration added" | tee -a "$LOG_FILE"
else
    echo "  ✗ TRUSDX audio sink creation failed" | tee -a "$LOG_FILE"
fi
echo

echo "SMOKE TEST RESULTS:" | tee -a "$LOG_FILE"
if [[ $SMOKE_TEST_PASS -eq 1 ]]; then
    echo "  ✓ All smoke tests passed" | tee -a "$LOG_FILE"
else
    echo "  ✗ Some smoke tests failed" | tee -a "$LOG_FILE"
fi
echo

echo "OVERALL STATUS:" | tee -a "$LOG_FILE"
if [[ $SETUP_SUCCESS -eq 1 ]]; then
    echo "  ✓ Setup completed successfully" | tee -a "$LOG_FILE"
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
else
    echo "  ✗ Setup failed - check errors above" | tee -a "$LOG_FILE"
    echo
    echo "===================================================" | tee -a "$LOG_FILE"
    echo "ERROR: Setup failed. Please read $LOG_FILE for details." | tee -a "$LOG_FILE"
    echo "===================================================" | tee -a "$LOG_FILE"
    exit 1
fi

echo
echo "Complete log available at: $LOG_FILE"

