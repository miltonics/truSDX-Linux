#!/bin/bash
# Hamlib 4.6.3 Installation Script
# Separated from main setup.sh for clarity

set -eE -o pipefail
trap 'echo "ERROR: Command failed at line $LINENO"; exit 1' ERR

LOG_FILE="/tmp/trusdx_setup_hamlib.log"
echo "Hamlib Setup Log - $(date)" > "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

install_hamlib_build_deps() {
    echo "Installing Hamlib build dependencies…" | tee -a "$LOG_FILE"
    DEBIAN_FRONTEND=noninteractive sudo apt-get install -y \
        build-essential \
        autoconf \
        automake \
        libtool \
        pkg-config \
        libusb-1.0-0-dev \
        libreadline-dev \
        texinfo \
        git \
        jq \
        2>&1 | tee -a "$LOG_FILE"
}

install_hamlib() {
    install_hamlib_build_deps
    
    local LATEST_TAG="hamlib-4.6.3"
    local LATEST_VER="4.6.3"
    
    echo "Downloading Hamlib $LATEST_VER source..." | tee -a "$LOG_FILE"
    
    TMPDIR=$(mktemp -d)
    trap "rm -rf '$TMPDIR'" EXIT

    echo "Downloading from GitHub releases..." | tee -a "$LOG_FILE"
    if ! curl -L -o "$TMPDIR/hamlib.tar.gz" "https://github.com/Hamlib/Hamlib/releases/download/$LATEST_TAG/hamlib-$LATEST_VER.tar.gz"; then
        echo "ERROR: Failed to download Hamlib source tarball" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Basic checksum verification (simplified)
    echo "Performing basic file verification..." | tee -a "$LOG_FILE"
    if [[ ! -s "$TMPDIR/hamlib.tar.gz" ]]; then
        echo "ERROR: Downloaded file is empty" | tee -a "$LOG_FILE"
        return 1
    fi
    
    echo "Extracting Hamlib source..." | tee -a "$LOG_FILE"
    cd "$TMPDIR"
    if ! tar -xzf hamlib.tar.gz; then
        echo "ERROR: Failed to extract Hamlib source" | tee -a "$LOG_FILE"
        return 1
    fi
    
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
    if command -v rigctl > /dev/null; then
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

echo "Starting Hamlib 4.6.3 installation..."
install_hamlib
echo "Hamlib installation script completed."

