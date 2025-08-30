#!/bin/bash
# TruSDX ALSA Bridge - Routes audio between truSDX and JS8Call using ALSA loopback

echo "Starting truSDX ALSA Bridge..."
echo "================================"

# Kill any existing processes
pkill -f "arecord.*ttyUSB"
pkill -f "aplay.*ttyUSB"

# Configure serial port
echo "Configuring serial port..."
stty -F /dev/ttyUSB0 115200 cs8 -cstopb -parenb raw -echo

# Initialize radio
echo "Initializing radio..."
echo -e "UA1;FA00007074000;" > /dev/ttyUSB0
sleep 1

echo ""
echo "Starting audio routing..."
echo "Radio RX -> Loopback for JS8Call to hear:"

# Route radio RX audio to loopback device (for JS8Call to receive)
# Radio outputs at 7820 Hz, we'll convert to 48000 Hz for JS8Call
(cat /dev/ttyUSB0 | aplay -r 7820 -f U8 -c 1 -D hw:1,0 2>/dev/null) &
RX_PID=$!
echo "  RX routing started (PID: $RX_PID)"

# Route loopback audio to radio TX (what JS8Call transmits)
# JS8Call outputs at 48000 Hz, we'll convert to 11525 Hz for radio
echo "JS8Call TX -> Radio:"
(arecord -r 48000 -f S16_LE -c 1 -D hw:1,1 2>/dev/null | \
  sox -t raw -r 48000 -e signed -b 16 -c 1 - \
      -t raw -r 11525 -e unsigned -b 8 -c 1 - 2>/dev/null | \
  while true; do
    # Simple VOX - read blocks of audio
    dd bs=1000 count=1 2>/dev/null | {
      data=$(cat)
      if [ ! -z "$data" ]; then
        echo -n -e "TX0;" > /dev/ttyUSB0
        echo -n "$data" > /dev/ttyUSB0
        echo "TX"
      fi
    }
  done) &
TX_PID=$!
echo "  TX routing started (PID: $TX_PID)"

echo ""
echo "================================"
echo "Bridge is running!"
echo ""
echo "IMPORTANT - Configure JS8Call audio:"
echo "  1. Go to File -> Settings -> Audio"
echo "  2. Input Device: 'Loopback: Loopback PCM (hw:1,0)'"
echo "  3. Output Device: 'Loopback: Loopback PCM (hw:1,1)'"
echo "  4. Apply and restart JS8Call"
echo ""
echo "For Radio control:"
echo "  1. Go to File -> Settings -> Radio"
echo "  2. Set Rig to 'None'"
echo "  3. PTT Method: 'VOX'"
echo ""
echo "Press Ctrl+C to stop the bridge"
echo "================================"

# Wait and handle cleanup
trap "echo 'Stopping bridge...'; kill $RX_PID $TX_PID 2>/dev/null; echo -e 'RX;' > /dev/ttyUSB0; exit" INT TERM

while true; do
  sleep 1
  # Check if processes are still running
  if ! kill -0 $RX_PID 2>/dev/null; then
    echo "RX process died, restarting..."
    (cat /dev/ttyUSB0 | aplay -r 7820 -f U8 -c 1 -D hw:1,0 2>/dev/null) &
    RX_PID=$!
  fi
done
