#!/bin/bash
# trusdx-audio-connect.sh - Connect JS8Call/WSJT-X to TRUSDX audio devices
# This script helps connect digital mode applications to the TRUSDX virtual audio device

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to ensure TRUSDX sink exists
ensure_trusdx_sink() {
    if ! pactl list sinks | grep -q "Name: TRUSDX"; then
        print_color "$YELLOW" "TRUSDX sink not found, creating..."
        MODULE_ID=$(pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX")
        print_color "$GREEN" "✅ Created TRUSDX sink (module ID: $MODULE_ID)"
    else
        print_color "$GREEN" "✅ TRUSDX sink already exists"
    fi
}

# Function to list audio sources and sinks
list_audio_devices() {
    print_color "$CYAN" "\n=== Available Audio Sources (Inputs) ==="
    if command_exists pw-cli; then
        pw-cli ls Node | grep -E "node.name.*monitor|node.description.*monitor" -A1 -B1 | grep -E "node.name|node.description" || true
    else
        pactl list sources short | grep -v ".monitor" || true
    fi
    
    print_color "$CYAN" "\n=== Available Audio Sinks (Outputs) ==="
    if command_exists pw-cli; then
        pw-cli ls Node | grep -E "node.name.*[Ss]ink" -A1 -B1 | grep -E "node.name|node.description" | grep -v monitor || true
    else
        pactl list sinks short || true
    fi
}

# Function to connect using pw-link (PipeWire)
connect_pipewire() {
    local app_name="$1"
    
    print_color "$BLUE" "\nSearching for $app_name audio ports..."
    
    # Find application ports
    local app_output=$(pw-link -o | grep -i "$app_name" | grep -i "output\|playback" | head -1)
    local app_input=$(pw-link -i | grep -i "$app_name" | grep -i "input\|capture" | head -1)
    
    if [ -z "$app_output" ] && [ -z "$app_input" ]; then
        print_color "$RED" "❌ No $app_name audio ports found. Is $app_name running?"
        return 1
    fi
    
    # Connect application output to TRUSDX input
    if [ -n "$app_output" ]; then
        print_color "$YELLOW" "Connecting $app_name output to TRUSDX..."
        pw-link "$app_output" "TRUSDX:playback_FL" || pw-link "$app_output" "TRUSDX:input_FL" || true
        pw-link "$app_output" "TRUSDX:playback_FR" || pw-link "$app_output" "TRUSDX:input_FR" || true
        print_color "$GREEN" "✅ Connected $app_name output → TRUSDX"
    fi
    
    # Connect TRUSDX.monitor to application input
    if [ -n "$app_input" ]; then
        print_color "$YELLOW" "Connecting TRUSDX.monitor to $app_name input..."
        pw-link "TRUSDX.monitor:capture_FL" "$app_input" || pw-link "TRUSDX.monitor:monitor_FL" "$app_input" || true
        print_color "$GREEN" "✅ Connected TRUSDX.monitor → $app_name input"
    fi
}

# Function to connect using pactl (PulseAudio)
connect_pulseaudio() {
    local app_name="$1"
    
    print_color "$BLUE" "\nSearching for $app_name audio streams..."
    
    # Find application sink inputs (playback streams)
    local sink_inputs=$(pactl list sink-inputs | grep -B20 -i "$app_name" | grep "Sink Input #" | cut -d'#' -f2)
    
    # Find application source outputs (recording streams)
    local source_outputs=$(pactl list source-outputs | grep -B20 -i "$app_name" | grep "Source Output #" | cut -d'#' -f2)
    
    if [ -z "$sink_inputs" ] && [ -z "$source_outputs" ]; then
        print_color "$RED" "❌ No $app_name audio streams found. Is $app_name running?"
        return 1
    fi
    
    # Move playback streams to TRUSDX sink
    for input in $sink_inputs; do
        print_color "$YELLOW" "Moving $app_name playback stream #$input to TRUSDX..."
        pactl move-sink-input "$input" "TRUSDX"
        print_color "$GREEN" "✅ Moved playback stream #$input → TRUSDX"
    done
    
    # Move recording streams to TRUSDX.monitor
    for output in $source_outputs; do
        print_color "$YELLOW" "Moving $app_name recording stream #$output to TRUSDX.monitor..."
        pactl move-source-output "$output" "TRUSDX.monitor"
        print_color "$GREEN" "✅ Moved recording stream #$output → TRUSDX.monitor"
    done
}

# Function to verify connections
verify_connections() {
    print_color "$CYAN" "\n=== Verifying Connections ==="
    
    if command_exists pw-link; then
        print_color "$BLUE" "PipeWire connections to/from TRUSDX:"
        pw-link -l | grep -i "trusdx" || print_color "$YELLOW" "No connections found"
    fi
    
    print_color "$BLUE" "\nActive streams using TRUSDX:"
    pactl list sink-inputs | grep -A10 "Sink: .*TRUSDX" | grep -E "Sink:|application.name" || true
    pactl list source-outputs | grep -A10 "Source: .*TRUSDX.monitor" | grep -E "Source:|application.name" || true
}

# Function to test audio with parecord
test_audio() {
    print_color "$CYAN" "\n=== Testing Audio Capture ==="
    print_color "$YELLOW" "Recording 5 seconds from TRUSDX.monitor..."
    
    parecord --device=TRUSDX.monitor -d 5 /tmp/trusdx_test.wav
    
    if [ -f /tmp/trusdx_test.wav ]; then
        local file_size=$(stat -c%s /tmp/trusdx_test.wav 2>/dev/null || stat -f%z /tmp/trusdx_test.wav 2>/dev/null)
        if [ "$file_size" -gt 1000 ]; then
            print_color "$GREEN" "✅ Test recording successful (size: $file_size bytes)"
            print_color "$BLUE" "Test file saved to: /tmp/trusdx_test.wav"
            
            # Optional: play back the recording
            if command_exists paplay; then
                read -p "Play back the test recording? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    paplay /tmp/trusdx_test.wav
                fi
            fi
        else
            print_color "$RED" "❌ Test recording is too small (no audio captured?)"
        fi
    else
        print_color "$RED" "❌ Failed to create test recording"
    fi
}

# Main menu
show_menu() {
    clear
    print_color "$CYAN" "=== TRUSDX Audio Connection Utility ==="
    print_color "$GREEN" "This tool helps connect JS8Call/WSJT-X to TRUSDX virtual audio"
    echo
    echo "1) Connect JS8Call to TRUSDX"
    echo "2) Connect WSJT-X to TRUSDX"
    echo "3) Connect FLDigi to TRUSDX"
    echo "4) List audio devices"
    echo "5) Verify connections"
    echo "6) Test audio recording"
    echo "7) Show JS8Call audio setup instructions"
    echo "8) Exit"
    echo
}

# Show JS8Call instructions
show_js8call_instructions() {
    print_color "$CYAN" "\n=== JS8Call Audio Configuration ==="
    print_color "$YELLOW" "In JS8Call, go to File → Settings → Radio:"
    echo
    print_color "$GREEN" "Audio Input (from radio):"
    echo "  • Select: TRUSDX.monitor"
    echo "  • This receives audio from the truSDX radio"
    echo
    print_color "$GREEN" "Audio Output (to radio):"
    echo "  • Select: TRUSDX"
    echo "  • This sends audio to the truSDX radio"
    echo
    print_color "$YELLOW" "Make sure to click 'OK' to save the settings!"
    echo
    read -p "Press Enter to continue..."
}

# Main script
main() {
    # Check for required tools
    if ! command_exists pactl; then
        print_color "$RED" "Error: pactl not found. Please install PulseAudio utilities."
        exit 1
    fi
    
    # Ensure TRUSDX sink exists
    ensure_trusdx_sink
    
    # Interactive menu
    while true; do
        show_menu
        read -p "Select option (1-8): " choice
        
        case $choice in
            1)
                if command_exists pw-link; then
                    connect_pipewire "js8call"
                else
                    connect_pulseaudio "js8call"
                fi
                read -p "Press Enter to continue..."
                ;;
            2)
                if command_exists pw-link; then
                    connect_pipewire "wsjtx"
                else
                    connect_pulseaudio "wsjtx"
                fi
                read -p "Press Enter to continue..."
                ;;
            3)
                if command_exists pw-link; then
                    connect_pipewire "fldigi"
                else
                    connect_pulseaudio "fldigi"
                fi
                read -p "Press Enter to continue..."
                ;;
            4)
                list_audio_devices
                read -p "Press Enter to continue..."
                ;;
            5)
                verify_connections
                read -p "Press Enter to continue..."
                ;;
            6)
                test_audio
                read -p "Press Enter to continue..."
                ;;
            7)
                show_js8call_instructions
                ;;
            8)
                print_color "$GREEN" "Exiting..."
                exit 0
                ;;
            *)
                print_color "$RED" "Invalid option"
                sleep 1
                ;;
        esac
    done
}

# Run with command line arguments or interactive mode
if [ $# -gt 0 ]; then
    case "$1" in
        connect)
            ensure_trusdx_sink
            if [ -z "$2" ]; then
                print_color "$RED" "Usage: $0 connect <app_name>"
                exit 1
            fi
            if command_exists pw-link; then
                connect_pipewire "$2"
            else
                connect_pulseaudio "$2"
            fi
            ;;
        list)
            list_audio_devices
            ;;
        verify)
            verify_connections
            ;;
        test)
            test_audio
            ;;
        help|--help|-h)
            print_color "$CYAN" "TRUSDX Audio Connection Utility"
            echo "Usage: $0 [command] [args]"
            echo
            echo "Commands:"
            echo "  connect <app>  - Connect application to TRUSDX"
            echo "  list          - List audio devices"
            echo "  verify        - Verify connections"
            echo "  test          - Test audio recording"
            echo "  help          - Show this help"
            echo
            echo "Without arguments, runs in interactive mode"
            ;;
        *)
            print_color "$RED" "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
else
    main
fi
