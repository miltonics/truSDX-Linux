#!/bin/bash
# monitor_audio_pw-top.sh - Monitor TRUSDX audio with pw-top

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== TRUSDX Audio Monitoring with pw-top ===${NC}"
echo
echo -e "${YELLOW}This script demonstrates how to use pw-top to monitor audio flow through TRUSDX${NC}"
echo
echo -e "${GREEN}Instructions:${NC}"
echo "1. Start the trusdx driver in another terminal: python3 trusdx-txrx-AI.py"
echo "2. Start JS8Call and configure it to use TRUSDX audio devices"
echo "3. Run pw-top to see real-time audio levels"
echo
echo -e "${CYAN}To monitor TRUSDX audio specifically:${NC}"
echo "• Look for nodes named 'TRUSDX' in the pw-top display"
echo "• The 'RATE' column shows audio activity"
echo "• The 'WAIT' column shows buffering delays"
echo "• The 'TRIG' column shows when audio is triggered"
echo
echo -e "${YELLOW}Press Enter to start pw-top (press 'q' to quit pw-top)${NC}"
read

# Check if pw-top exists
if ! command -v pw-top &> /dev/null; then
    echo -e "${YELLOW}pw-top not found. It's part of pipewire-tools package.${NC}"
    echo "Install with: sudo apt install pipewire-tools"
    exit 1
fi

# Run pw-top
echo -e "${GREEN}Starting pw-top...${NC}"
pw-top
