#!/bin/bash

# Stop the socat serial bridge process
pid_file="/tmp/trusdx_cat_socat.pid"
tmp_link="/tmp/trusdx_cat"

if [ -f "$pid_file" ]; then
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Stopping socat bridge process (PID: $pid)"
        kill "$pid"
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing socat bridge process"
            kill -9 "$pid"
        fi
    fi
    rm "$pid_file"
fi

# Remove the symlink
if [ -L "$tmp_link" ]; then
    rm "$tmp_link"
    echo "Removed serial bridge symlink: $tmp_link"
fi

echo "Serial bridge cleanup complete."
