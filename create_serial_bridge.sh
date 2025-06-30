#!/bin/bash

# Create a PTY pair and link one end to /tmp/trusdx_cat
tmp_link="/tmp/trusdx_cat"

# Check if socat is available
if ! command -v socat &> /dev/null; then
    echo "Error: socat is not installed. Please install it first:"
    echo "  Ubuntu/Debian: sudo apt install socat"
    echo "  Fedora/RHEL:   sudo dnf install socat"
    echo "  Arch:          sudo pacman -S socat"
    exit 1
fi

# Remove existing link if it exists
if [ -L "$tmp_link" ]; then
    rm "$tmp_link"
fi

# Launch socat to create a virtual serial port at /tmp/trusdx_cat
# The first PTY is linked to /tmp/trusdx_cat, the second is the other end of the pair
socat -d -d PTY,link=$tmp_link,raw,echo=0,perm=0777 PTY,raw,echo=0 &

# Store the socat PID for later cleanup
SOCAT_PID=$!
echo $SOCAT_PID > /tmp/trusdx_cat_socat.pid

# Wait for socat to establish the link
sleep 2

# Ensure the permissions are set correctly
if [ -L "$tmp_link" ]; then
    chmod 777 "$tmp_link"
    echo "Serial bridge created at $tmp_link with permissions 777 (PID: $SOCAT_PID)"
else
    echo "Error: Failed to create serial bridge at $tmp_link"
    exit 1
fi
