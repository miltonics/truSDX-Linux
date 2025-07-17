#!/bin/bash
# Check PipeWire audio connections for TruSDX and JS8Call

echo "============================================="
echo "PipeWire Audio Connection Check"
echo "============================================="
echo

# Check if JS8Call is running
if pgrep -x "js8call" > /dev/null; then
    echo "✅ JS8Call is running"
else
    echo "⚠️  JS8Call is not running"
fi

# Check if TruSDX driver is running
if pgrep -f "trusdx-txrx-AI.py" > /dev/null; then
    echo "✅ TruSDX driver is running"
else
    echo "⚠️  TruSDX driver is not running"
fi

echo
echo "=== Audio Devices ==="
echo
echo "TRUSDX-related sinks and sources:"
pactl list short | grep TRUSDX

echo
echo "=== PipeWire Nodes ==="
echo
echo "Audio nodes (filtered for TRUSDX and JS8Call):"
pw-cli list-objects Node | grep -E "(node.name|node.description|media.class)" | grep -B2 -A1 -i "trusdx\|js8call" | head -30

echo
echo "=== Active Connections ==="
echo
echo "PipeWire links:"
pw-link -l | grep -A2 -B2 -E "(TRUSDX|JS8Call|js8call)" | head -50

echo
echo "=== Audio Stream Details ==="
echo
echo "Source outputs (apps recording):"
pactl list source-outputs | grep -E "(application.name|Source:|device.description)" | head -20

echo
echo "Sink inputs (apps playing):"
pactl list sink-inputs | grep -E "(application.name|Sink:|device.description)" | head -20

echo
echo "=== PipeWire Graph ==="
echo
echo "Visual representation of connections:"
echo "(Output Port) -> (Input Port)"
echo

# Parse pw-link output to show connections more clearly
pw-link -l | awk '
    /^[^ ]/ { 
        if (output != "" && ($0 ~ /TRUSDX/ || $0 ~ /[Jj]s8[Cc]all/)) {
            gsub(/^[ \t]+/, "", $0)
            print output " -> " $0
        }
        output = ""
    }
    /->/ && prev ~ /(TRUSDX|[Jj]s8[Cc]all)/ {
        output = prev
    }
    { prev = $0 }
'

echo
echo "=== Recommendations ==="
echo

# Check for expected connections
if pw-link -l | grep -q "js8call.*TRUSDX:playback"; then
    echo "✅ JS8Call output is connected to TRUSDX playback"
else
    echo "⚠️  JS8Call output may not be connected to TRUSDX"
    echo "   Try: pw-link 'js8call:output_FL' 'TRUSDX:playback_FL'"
fi

if pw-link -l | grep -q "TRUSDX.*monitor.*js8call"; then
    echo "✅ TRUSDX monitor is connected to JS8Call input"
else
    echo "⚠️  TRUSDX monitor may not be connected to JS8Call"
    echo "   Try: pw-link 'TRUSDX:monitor_FL' 'js8call:input_FL'"
fi

echo
echo "============================================="
