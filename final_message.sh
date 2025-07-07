#!/bin/bash

# Display setup complete message in green
echo -e "\033[32m**Setup Complete!**\033[0m"
echo ""

# Check if reboot is needed
if [ "$REBOOT_NEEDED" = "1" ]; then
    echo "⚠️  IMPORTANT: A reboot or logout is required for new group membership to take effect"
    echo "   before using the truSDX-AI driver. Please:"
    echo "   - Reboot your system, OR"
    echo "   - Log out and log back in"
    echo ""
fi

# Print quick-start commands
echo "Quick-start commands:"
echo "  ./trusdx-ai --help              # Show all options"
echo "  ./trusdx-ai --scan              # Scan for truSDX devices"
echo "  ./trusdx-ai --device /dev/ttyUSB0 --band 20m --mode USB --freq 14.230"
echo "  ./trusdx-ai --device /dev/ttyUSB0 --waterfall --duration 60"
echo "  ./trusdx-ai --device /dev/ttyUSB0 --auto-tune --target-band 40m"
echo ""
echo "For more examples and documentation:"
echo "  cat README.md"
echo "  cat EXAMPLES.md"

# Return 0 to indicate successful completion
exit 0
