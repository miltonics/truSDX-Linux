#!/bin/bash
# TruSDX PipeWire Bridge - Routes audio between truSDX driver and JS8Call via PipeWire

echo "Starting truSDX PipeWire Bridge..."
echo "================================"

# Kill any existing processes
pkill -f trusdx-txrx-AI.py

# Start the trusdx driver
echo "Starting truSDX driver..."
cd /opt/trusdx
python3 trusdx-txrx-AI.py &
DRIVER_PID=$!
echo "Driver started (PID: $DRIVER_PID)"

# Wait for driver to initialize
sleep 3

# Create audio routing using pw-link
echo "Setting up PipeWire audio routing..."

# Find the trusdx driver's audio ports
echo "Looking for trusdx audio ports..."

# Route trusdx RX audio (from radio) to TRUSDX sink
# This makes it available via TRUSDX.monitor for JS8Call
pw-link -d 2>&1 | grep -i "trusdx_rx" | while read line; do
    echo "Found: $line"
done

# Use pacat to bridge ALSA loopback to PipeWire
echo "Creating audio bridges..."

# Bridge from ALSA loopback (trusdx_rx) to PipeWire TRUSDX sink
# This makes radio audio available on TRUSDX.monitor for JS8Call
(while true; do
    arecord -D trusdx_rx -f S16_LE -r 48000 -c 1 2>/dev/null | \
    pacat --device=TRUSDX --rate=48000 --channels=1 --format=s16le --latency-msec=10 2>/dev/null
    echo "RX bridge restarting..."
    sleep 1
done) &
RX_BRIDGE_PID=$!
echo "RX bridge started (PID: $RX_BRIDGE_PID)"

# Bridge from PipeWire TRUSDX sink to ALSA loopback (trusdx_tx)
# This sends JS8Call's TX audio to the radio
(while true; do
    parec --device=TRUSDX.monitor --rate=48000 --channels=1 --format=s16le 2>/dev/null | \
    aplay -D trusdx_tx -f S16_LE -r 48000 -c 1 2>/dev/null
    echo "TX bridge restarting..."
    sleep 1
done) &
TX_BRIDGE_PID=$!
echo "TX bridge started (PID: $TX_BRIDGE_PID)"

echo ""
echo "================================"
echo "Bridge is running!"
echo ""
echo "IMPORTANT - Configure JS8Call audio:"
echo "  1. Go to File -> Settings -> Audio"
echo "  2. Input Device: 'TRUSDX.monitor'"
echo "  3. Output Device: 'TRUSDX'"
echo "  4. Apply and restart JS8Call"
echo ""
echo "The waterfall should now show signals received by the radio."
echo ""
echo "Press Ctrl+C to stop the bridge"
echo "================================"

# Wait and handle cleanup
trap "echo 'Stopping bridge...'; kill $DRIVER_PID $RX_BRIDGE_PID $TX_BRIDGE_PID 2>/dev/null; exit" INT TERM

# Monitor processes
while true; do
    sleep 5
    
    # Check if driver is still running
    if ! kill -0 $DRIVER_PID 2>/dev/null; then
        echo "Driver stopped, restarting..."
        cd /opt/trusdx
        python3 trusdx-txrx-AI.py &
        DRIVER_PID=$!
        echo "Driver restarted (PID: $DRIVER_PID)"
    fi
    
    # Check if RX bridge is still running
    if ! kill -0 $RX_BRIDGE_PID 2>/dev/null; then
        echo "RX bridge stopped, restarting..."
        (while true; do
            arecord -D trusdx_rx -f S16_LE -r 48000 -c 1 2>/dev/null | \
            pacat --device=TRUSDX --rate=48000 --channels=1 --format=s16le --latency-msec=10 2>/dev/null
            sleep 1
        done) &
        RX_BRIDGE_PID=$!
        echo "RX bridge restarted (PID: $RX_BRIDGE_PID)"
    fi
done
