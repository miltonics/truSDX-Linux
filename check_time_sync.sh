#!/bin/bash

# Time-sync monitor script for WSJT-X
# Uses timedatectl and chronyc tracking to monitor time synchronization

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
OFFSET_WARN_THRESHOLD=0.5
UPDATE_INTERVAL=5

# Global variables
WATCH_MODE=false
ONCE_MODE=false

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Monitor time synchronization status using timedatectl and chronyc"
    echo ""
    echo "OPTIONS:"
    echo "  --once      Run once and exit"
    echo "  --watch     Run continuously (default)"
    echo "  -h, --help  Show this help message"
    echo ""
    echo "Exit codes:"
    echo "  0: Time is synchronized"
    echo "  1: Time is not synchronized"
    echo "  2: Error accessing time services"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get timedatectl status
get_timedatectl_status() {
    local output
    if ! output=$(timedatectl status 2>/dev/null); then
        echo "ERROR: Cannot access timedatectl" >&2
        return 1
    fi
    echo "$output"
}

# Function to get chronyc tracking info
get_chronyc_tracking() {
    local output
    if ! output=$(chronyc tracking 2>/dev/null); then
        echo "WARNING: Cannot access chronyc tracking" >&2
        return 1
    fi
    echo "$output"
}

# Function to parse timedatectl output
parse_timedatectl() {
    local timedatectl_output="$1"
    local ntp_sync=""
    local ntp_service=""
    
    # Extract NTP synchronization status
    if echo "$timedatectl_output" | grep -q "NTP service: active"; then
        ntp_service="active"
    elif echo "$timedatectl_output" | grep -q "NTP service: inactive"; then
        ntp_service="inactive"
    else
        ntp_service="unknown"
    fi
    
    # Extract synchronization status
    if echo "$timedatectl_output" | grep -Eq "(NTP synchronized: yes|System clock synchronized: yes)"; then
        ntp_sync="yes"
    elif echo "$timedatectl_output" | grep -Eq "(NTP synchronized: no|System clock synchronized: no)"; then
        ntp_sync="no"
    else
        ntp_sync="unknown"
    fi
    
    echo "$ntp_service|$ntp_sync"
}

# Function to parse chronyc tracking output
parse_chronyc_tracking() {
    local chronyc_output="$1"
    local ref_id=""
    local stratum=""
    local ref_time=""
    local system_time=""
    local last_offset=""
    local rms_offset=""
    local frequency=""
    local residual_freq=""
    local skew=""
    local root_delay=""
    local root_dispersion=""
    local update_interval=""
    local leap_status=""
    
    # Parse each line
    while IFS= read -r line; do
        case "$line" in
            "Reference ID"*)
                ref_id=$(echo "$line" | sed 's/Reference ID[[:space:]]*:[[:space:]]*//')
                ;;
            "Stratum"*)
                stratum=$(echo "$line" | sed 's/Stratum[[:space:]]*:[[:space:]]*//')
                ;;
            "Ref time"*)
                ref_time=$(echo "$line" | sed 's/Ref time[[:space:]]*:[[:space:]]*//')
                ;;
            "System time"*)
                system_time=$(echo "$line" | sed 's/System time[[:space:]]*:[[:space:]]*//')
                ;;
            "Last offset"*)
                last_offset=$(echo "$line" | sed 's/Last offset[[:space:]]*:[[:space:]]*//')
                ;;
            "RMS offset"*)
                rms_offset=$(echo "$line" | sed 's/RMS offset[[:space:]]*:[[:space:]]*//')
                ;;
            "Frequency"*)
                frequency=$(echo "$line" | sed 's/Frequency[[:space:]]*:[[:space:]]*//')
                ;;
            "Residual freq"*)
                residual_freq=$(echo "$line" | sed 's/Residual freq[[:space:]]*:[[:space:]]*//')
                ;;
            "Skew"*)
                skew=$(echo "$line" | sed 's/Skew[[:space:]]*:[[:space:]]*//')
                ;;
            "Root delay"*)
                root_delay=$(echo "$line" | sed 's/Root delay[[:space:]]*:[[:space:]]*//')
                ;;
            "Root dispersion"*)
                root_dispersion=$(echo "$line" | sed 's/Root dispersion[[:space:]]*:[[:space:]]*//')
                ;;
            "Update interval"*)
                update_interval=$(echo "$line" | sed 's/Update interval[[:space:]]*:[[:space:]]*//')
                ;;
            "Leap status"*)
                leap_status=$(echo "$line" | sed 's/Leap status[[:space:]]*:[[:space:]]*//')
                ;;
        esac
    done <<< "$chronyc_output"
    
    echo "$ref_id|$stratum|$system_time|$last_offset|$rms_offset|$leap_status"
}

# Function to extract numeric value from offset string
extract_offset_value() {
    local offset_str="$1"
    # Extract numeric value, handle both positive and negative
    echo "$offset_str" | sed -n 's/.*\([+-]\?[0-9]*\.[0-9]*\).*/\1/p'
}

# Function to check if offset exceeds threshold
check_offset_threshold() {
    local offset_str="$1"
    local threshold="$2"
    local offset_val
    
    offset_val=$(extract_offset_value "$offset_str")
    
    if [[ -z "$offset_val" ]]; then
        return 1
    fi
    
    # Use awk for floating point comparison
    if awk "BEGIN {exit !(($offset_val > $threshold) || ($offset_val < -$threshold))}"; then
        return 0  # Threshold exceeded
    else
        return 1  # Within threshold
    fi
}

# Function to display colorized table
display_status_table() {
    local timedatectl_output="$1"
    local chronyc_output="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Parse outputs
    local timedatectl_info
    local chronyc_info
    
    timedatectl_info=$(parse_timedatectl "$timedatectl_output")
    IFS='|' read -r ntp_service ntp_sync <<< "$timedatectl_info"
    
    if [[ -n "$chronyc_output" ]]; then
        chronyc_info=$(parse_chronyc_tracking "$chronyc_output")
        IFS='|' read -r ref_id stratum system_time last_offset rms_offset leap_status <<< "$chronyc_info"
    else
        ref_id="N/A"
        stratum="N/A"
        system_time="N/A"
        last_offset="N/A"
        rms_offset="N/A"
        leap_status="N/A"
    fi
    
    # Determine sync status color
    local sync_color="$RED"
    local sync_status="NOT SYNCED"
    if [[ "$ntp_sync" == "yes" ]]; then
        sync_color="$GREEN"
        sync_status="SYNCED"
    fi
    
    # Check offset warning
    local offset_color="$GREEN"
    local offset_warning=""
    if [[ "$last_offset" != "N/A" ]] && check_offset_threshold "$last_offset" "$OFFSET_WARN_THRESHOLD"; then
        offset_color="$YELLOW"
        offset_warning=" ${RED}⚠ WARNING${NC}"
    fi
    
    # Determine leap status color
    local leap_color="$GREEN"
    case "$leap_status" in
        "Normal")
            leap_color="$GREEN"
            ;;
        "Insert second"|"Delete second")
            leap_color="$YELLOW"
            ;;
        *)
            leap_color="$CYAN"
            ;;
    esac
    
    # Clear screen and display table
    clear
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}                              TIME SYNCHRONIZATION STATUS                              ${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Timestamp:${NC} $timestamp"
    echo ""
    echo -e "${BOLD}┌─────────────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BOLD}│                                  SYSTEM STATUS                                  │${NC}"
    echo -e "${BOLD}├─────────────────────────────────────────────────────────────────────────────────────┤${NC}"
    printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} %-55s ${BOLD}│${NC}\n" "NTP Service" "${ntp_service}"
    printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} ${sync_color}%-55s${NC} ${BOLD}│${NC}\n" "Sync Status" "$sync_status"
    echo -e "${BOLD}└─────────────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    
    if [[ "$chronyc_output" != "" ]]; then
        echo -e "${BOLD}┌─────────────────────────────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${BOLD}│                                 CHRONY TRACKING                                 │${NC}"
        echo -e "${BOLD}├─────────────────────────────────────────────────────────────────────────────────────┤${NC}"
        printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} %-55s ${BOLD}│${NC}\n" "Reference ID" "$ref_id"
        printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} %-55s ${BOLD}│${NC}\n" "Stratum" "$stratum"
        printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} %-55s ${BOLD}│${NC}\n" "System Time" "$system_time"
        printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} ${offset_color}%-55s${NC} ${BOLD}│${NC}\n" "Last Offset" "$last_offset$offset_warning"
        printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} %-55s ${BOLD}│${NC}\n" "RMS Offset" "$rms_offset"
        printf "${BOLD}│${NC} %-20s ${BOLD}│${NC} ${leap_color}%-55s${NC} ${BOLD}│${NC}\n" "Leap Status" "$leap_status"
        echo -e "${BOLD}└─────────────────────────────────────────────────────────────────────────────────────┘${NC}"
    else
        echo -e "${YELLOW}Warning: chronyc tracking information not available${NC}"
    fi
    
    echo ""
    if [[ "$offset_warning" != "" ]]; then
        echo -e "${RED}${BOLD}⚠ WARNING: Time offset exceeds ${OFFSET_WARN_THRESHOLD}s threshold!${NC}"
        echo ""
    fi
    
    if [[ "$WATCH_MODE" == "true" ]]; then
        echo -e "${CYAN}Monitoring... (Press Ctrl+C to stop)${NC}"
        echo -e "${CYAN}Update interval: ${UPDATE_INTERVAL}s${NC}"
    fi
}

# Function to check sync status and return appropriate exit code
check_sync_status() {
    local timedatectl_output="$1"
    
    if echo "$timedatectl_output" | grep -Eq "(NTP synchronized: yes|System clock synchronized: yes)"; then
        return 0  # Synchronized
    else
        return 1  # Not synchronized
    fi
}

# Function to run the monitoring loop
run_monitor() {
    local timedatectl_output
    local chronyc_output
    local exit_code=0
    
    while true; do
        # Get timedatectl status
        if ! timedatectl_output=$(get_timedatectl_status); then
            echo -e "${RED}ERROR: Cannot access timedatectl${NC}" >&2
            exit 2
        fi
        
        # Get chronyc tracking (optional)
        chronyc_output=$(get_chronyc_tracking 2>/dev/null || echo "")
        
        # Display status table
        display_status_table "$timedatectl_output" "$chronyc_output"
        
        # Check sync status for exit code
        if ! check_sync_status "$timedatectl_output"; then
            exit_code=1
        fi
        
        # Exit if in once mode
        if [[ "$ONCE_MODE" == "true" ]]; then
            exit $exit_code
        fi
        
        # Wait for next update
        sleep $UPDATE_INTERVAL
    done
}

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo -e "${CYAN}Monitoring stopped.${NC}"
    exit 0
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --once)
                ONCE_MODE=true
                shift
                ;;
            --watch)
                WATCH_MODE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage
                exit 1
                ;;
        esac
    done
    
    # Set default mode if none specified
    if [[ "$ONCE_MODE" == "false" && "$WATCH_MODE" == "false" ]]; then
        WATCH_MODE=true
    fi
    
    # Check for required commands
    if ! command_exists timedatectl; then
        echo -e "${RED}ERROR: timedatectl not found${NC}" >&2
        exit 2
    fi
    
    if ! command_exists chronyc; then
        echo -e "${YELLOW}WARNING: chronyc not found, some features will be limited${NC}" >&2
    fi
    
    # Set up signal handlers for clean exit
    trap cleanup SIGINT SIGTERM
    
    # Run the monitor
    run_monitor
}

# Run main function with all arguments
main "$@"
