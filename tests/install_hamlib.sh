#!/bin/bash
# Install hamlib for TS-480 integration testing

echo "Installing hamlib utilities for truSDX-AI integration testing..."

# Update package lists
sudo apt update

# Install hamlib tools
sudo apt install -y hamlib-utils

# Install netcat if not available
sudo apt install -y netcat-openbsd

echo "Hamlib installation complete!"
echo ""
echo "You can now run integration tests with:"
echo "  cd tests"
echo "  python3 test_cat_emulation.py"
echo ""
echo "To test manually with rigctld:"
echo "  rigctld -m 2014 -r /dev/pts/X -s 115200 -t 4532"
echo "  rigctl -m 2 -r localhost:4532"
echo ""
