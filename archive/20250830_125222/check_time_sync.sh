#!/bin/bash
#
# check_time_sync.sh - Monitor system time synchronization
# Runs every 10 minutes via systemd-timer
# Logs to syslog and /var/log/trusdx/time_sync.log

# Ensure log directory exists
LOG_DIR="/var/log/trusdx"
LOG_FILE="${LOG_DIR}/time_sync.log"

if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi

# Function to log to both syslog and file
log_message() {
    local message="$1"
    logger -t truSDX "$message"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" >> "$LOG_FILE"
}

# Check if system clock is synchronized
if ! timedatectl | grep -q 'System clock synchronized: yes'; then
    log_message "Clock unsynced – calling chronyc makestep"
    chronyc makestep
fi

# Check clock drift
chronyc tracking | awk '/Last offset/ { 
    if ($4 > 0.5 || $4 < -0.5) {
        system("logger -t truSDX \"Clock drift >0.5s: " $4 "s\"")
        print strftime("%Y-%m-%d %H:%M:%S") " - Clock drift >0.5s: " $4 "s" >> "'"$LOG_FILE"'"
    }
}'
