#!/bin/bash
# regression_test.sh - Automated regression test for truSDX driver
# Tests WSJT-X simulation with dummy audio streams and reconnection logic

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
TEST_DURATION=120  # 2 minutes
STREAM_CYCLES=5    # Number of start/stop cycles
CYCLE_DURATION=10  # Duration of each cycle in seconds
LOG_DIR="./logs"
TEST_LOG="$LOG_DIR/regression_test_$(date +%Y%m%d_%H%M%S).log"
DRIVER_LOG="$LOG_DIR/trusdx_driver_test.log"
AUDIO_TEST_FILE="/tmp/trusdx_regression_audio.wav"

# Process PIDs
DRIVER_PID=""
ARECORD_PID=""
APLAY_PID=""

# Test results
TEST_PASSED=true
ERROR_COUNT=0
SUCCESS_COUNT=0

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}" | tee -a "$TEST_LOG"
}

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$TEST_LOG"
}

# Function to cleanup on exit
cleanup() {
    print_color "$YELLOW" "\n=== Cleaning up test environment ==="
    
    # Kill all test processes
    if [ -n "$APLAY_PID" ]; then
        kill -TERM "$APLAY_PID" 2>/dev/null || true
        log_message "Stopped aplay process (PID: $APLAY_PID)"
    fi
    
    if [ -n "$ARECORD_PID" ]; then
        kill -TERM "$ARECORD_PID" 2>/dev/null || true
        log_message "Stopped arecord process (PID: $ARECORD_PID)"
    fi
    
    if [ -n "$DRIVER_PID" ]; then
        kill -TERM "$DRIVER_PID" 2>/dev/null || true
        sleep 2
        if kill -0 "$DRIVER_PID" 2>/dev/null; then
            kill -KILL "$DRIVER_PID" 2>/dev/null || true
        fi
        log_message "Stopped driver process (PID: $DRIVER_PID)"
    fi
    
    # Clean up test files
    rm -f "$AUDIO_TEST_FILE"
    
    print_color "$GREEN" "✅ Cleanup complete"
}

# Set up trap for cleanup
trap cleanup EXIT

# Function to check if ALSA loopback is available
check_alsa_loopback() {
    print_color "$CYAN" "\n=== Checking ALSA Loopback Module ==="
    
    if ! lsmod | grep -q snd_aloop; then
        print_color "$YELLOW" "Loading ALSA loopback module..."
        sudo modprobe snd-aloop
        sleep 2
    fi
    
    if aplay -l | grep -q "Loopback"; then
        print_color "$GREEN" "✅ ALSA Loopback card available"
        log_message "ALSA Loopback card detected"
        return 0
    else
        print_color "$RED" "❌ ALSA Loopback card not found"
        log_message "ERROR: ALSA Loopback card not available"
        return 1
    fi
}

# Function to verify audio devices
verify_audio_devices() {
    print_color "$CYAN" "\n=== Verifying Audio Devices ==="
    
    # Check for trusdx devices
    local has_rx_app=false
    local has_tx_app=false
    
    # Check using aplay/arecord
    if aplay -L | grep -q "trusdx_tx_app"; then
        has_tx_app=true
        print_color "$GREEN" "✅ Found trusdx_tx_app device"
    fi
    
    if arecord -L | grep -q "trusdx_rx_app"; then
        has_rx_app=true
        print_color "$GREEN" "✅ Found trusdx_rx_app device"
    fi
    
    if [ "$has_tx_app" = true ] && [ "$has_rx_app" = true ]; then
        log_message "All required audio devices found"
        return 0
    else
        print_color "$YELLOW" "⚠️  Some devices not found, will use hw:Loopback directly"
        log_message "WARNING: Using hw:Loopback devices directly"
        return 0
    fi
}

# Function to start dummy audio streams (mimicking WSJT-X)
start_dummy_streams() {
    print_color "$CYAN" "\n=== Starting Dummy Audio Streams (WSJT-X simulation) ==="
    
    # Generate test tone for playback
    print_color "$BLUE" "Generating test audio..."
    sox -n -r 48000 -c 1 -b 16 "$AUDIO_TEST_FILE" synth 60 sine 1000 gain -20
    
    # Start aplay to simulate WSJT-X TX (sending audio to driver)
    print_color "$BLUE" "Starting aplay (simulating WSJT-X TX)..."
    
    # Try trusdx_tx_app first, fallback to hw:Loopback
    if aplay -L | grep -q "trusdx_tx_app"; then
        aplay -D trusdx_tx_app -r 48000 -f S16_LE -c 1 "$AUDIO_TEST_FILE" -q --duration=300 &
    else
        aplay -D hw:Loopback,1,0 -r 48000 -f S16_LE -c 1 "$AUDIO_TEST_FILE" -q --duration=300 &
    fi
    APLAY_PID=$!
    log_message "Started aplay process (PID: $APLAY_PID)"
    
    # Start arecord to simulate WSJT-X RX (receiving audio from driver)
    print_color "$BLUE" "Starting arecord (simulating WSJT-X RX)..."
    
    # Try trusdx_rx_app first, fallback to hw:Loopback
    if arecord -L | grep -q "trusdx_rx_app"; then
        arecord -D trusdx_rx_app -r 48000 -f S16_LE -c 1 -q /dev/null &
    else
        arecord -D hw:Loopback,1,1 -r 48000 -f S16_LE -c 1 -q /dev/null &
    fi
    ARECORD_PID=$!
    log_message "Started arecord process (PID: $ARECORD_PID)"
    
    print_color "$GREEN" "✅ Dummy audio streams started"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
}

# Function to stop dummy audio streams
stop_dummy_streams() {
    print_color "$CYAN" "\n=== Stopping Dummy Audio Streams ==="
    
    if [ -n "$APLAY_PID" ]; then
        kill -TERM "$APLAY_PID" 2>/dev/null || true
        APLAY_PID=""
        log_message "Stopped aplay process"
    fi
    
    if [ -n "$ARECORD_PID" ]; then
        kill -TERM "$ARECORD_PID" 2>/dev/null || true
        ARECORD_PID=""
        log_message "Stopped arecord process"
    fi
    
    print_color "$GREEN" "✅ Dummy audio streams stopped"
}

# Function to start the driver
start_driver() {
    print_color "$CYAN" "\n=== Starting truSDX Driver ==="
    
    # Check if driver script exists
    if [ ! -f "./trusdx-txrx-AI.py" ]; then
        print_color "$RED" "❌ Driver script not found: ./trusdx-txrx-AI.py"
        log_message "ERROR: Driver script not found"
        return 1
    fi
    
    # Start the driver in background, redirect output to log
    print_color "$BLUE" "Starting driver process..."
    python3 ./trusdx-txrx-AI.py > "$DRIVER_LOG" 2>&1 &
    DRIVER_PID=$!
    
    log_message "Started driver process (PID: $DRIVER_PID)"
    
    # Wait for driver to initialize
    sleep 5
    
    # Check if driver is still running
    if kill -0 "$DRIVER_PID" 2>/dev/null; then
        print_color "$GREEN" "✅ Driver started successfully (PID: $DRIVER_PID)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        return 0
    else
        print_color "$RED" "❌ Driver failed to start"
        log_message "ERROR: Driver failed to start"
        
        # Show last lines of driver log
        print_color "$YELLOW" "Last lines from driver log:"
        tail -20 "$DRIVER_LOG" | while read line; do
            echo "  $line"
        done
        
        return 1
    fi
}

# Function to check driver health
check_driver_health() {
    local check_duration=$1
    local start_time=$(date +%s)
    local errors_found=false
    
    print_color "$CYAN" "\n=== Monitoring Driver Health for $check_duration seconds ==="
    
    while [ $(($(date +%s) - start_time)) -lt $check_duration ]; do
        # Check if driver is still running
        if ! kill -0 "$DRIVER_PID" 2>/dev/null; then
            print_color "$RED" "❌ Driver process crashed!"
            log_message "ERROR: Driver process crashed"
            ERROR_COUNT=$((ERROR_COUNT + 1))
            errors_found=true
            break
        fi
        
        # Check for "Device unavailable" errors in log
        if grep -q "Device unavailable" "$DRIVER_LOG" 2>/dev/null; then
            print_color "$RED" "❌ Found 'Device unavailable' error in driver log"
            log_message "ERROR: Device unavailable detected"
            ERROR_COUNT=$((ERROR_COUNT + 1))
            errors_found=true
            
            # Show the error context
            print_color "$YELLOW" "Error context:"
            grep -C 2 "Device unavailable" "$DRIVER_LOG" | tail -10 | while read line; do
                echo "  $line"
            done
        fi
        
        # Check for Python tracebacks
        if grep -q "Traceback" "$DRIVER_LOG" 2>/dev/null; then
            print_color "$RED" "❌ Found Python traceback in driver log"
            log_message "ERROR: Python traceback detected"
            ERROR_COUNT=$((ERROR_COUNT + 1))
            errors_found=true
            
            # Show the traceback
            print_color "$YELLOW" "Traceback:"
            grep -A 10 "Traceback" "$DRIVER_LOG" | tail -15 | while read line; do
                echo "  $line"
            done
        fi
        
        # Progress indicator
        echo -n "."
        sleep 2
    done
    
    echo  # New line after progress dots
    
    if [ "$errors_found" = false ]; then
        print_color "$GREEN" "✅ Driver healthy for $check_duration seconds"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        return 0
    else
        return 1
    fi
}

# Function to test stream reconnection
test_stream_reconnection() {
    print_color "$CYAN" "\n=== Testing Stream Reconnection Logic ==="
    
    for i in $(seq 1 $STREAM_CYCLES); do
        print_color "$BLUE" "\nCycle $i/$STREAM_CYCLES:"
        
        # Start streams
        print_color "$YELLOW" "  Starting audio streams..."
        start_dummy_streams
        
        # Let streams run
        print_color "$YELLOW" "  Running for $CYCLE_DURATION seconds..."
        if ! check_driver_health $CYCLE_DURATION; then
            print_color "$RED" "  ❌ Driver health check failed in cycle $i"
            TEST_PASSED=false
        fi
        
        # Stop streams
        print_color "$YELLOW" "  Stopping audio streams..."
        stop_dummy_streams
        
        # Wait for reconnection
        print_color "$YELLOW" "  Waiting for reconnection logic..."
        sleep 3
        
        # Check if driver is still alive
        if kill -0 "$DRIVER_PID" 2>/dev/null; then
            print_color "$GREEN" "  ✅ Driver survived stream restart cycle $i"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            print_color "$RED" "  ❌ Driver crashed during cycle $i"
            log_message "ERROR: Driver crashed in reconnection cycle $i"
            ERROR_COUNT=$((ERROR_COUNT + 1))
            TEST_PASSED=false
            break
        fi
    done
}

# Function to generate test report
generate_report() {
    print_color "$CYAN" "\n=== TEST REPORT ==="
    
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    print_color "$BLUE" "Test completed at: $end_time"
    print_color "$BLUE" "Log file: $TEST_LOG"
    print_color "$BLUE" "Driver log: $DRIVER_LOG"
    
    echo ""
    print_color "$CYAN" "Results:"
    print_color "$GREEN" "  Successful checks: $SUCCESS_COUNT"
    print_color "$RED" "  Errors found: $ERROR_COUNT"
    
    if [ "$TEST_PASSED" = true ] && [ $ERROR_COUNT -eq 0 ]; then
        print_color "$GREEN" "\n✅ ✅ ✅ REGRESSION TEST PASSED ✅ ✅ ✅"
        log_message "RESULT: TEST PASSED"
        return 0
    else
        print_color "$RED" "\n❌ ❌ ❌ REGRESSION TEST FAILED ❌ ❌ ❌"
        log_message "RESULT: TEST FAILED"
        
        # Show summary of errors
        if [ $ERROR_COUNT -gt 0 ]; then
            print_color "$YELLOW" "\nError Summary:"
            grep "ERROR:" "$TEST_LOG" | while read line; do
                echo "  • $line"
            done
        fi
        
        return 1
    fi
}

# Main test execution
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Initialize log
    echo "=== truSDX Regression Test Log ===" > "$TEST_LOG"
    echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$TEST_LOG"
    echo "" >> "$TEST_LOG"
    
    print_color "$CYAN" "=== truSDX Driver Regression Test ==="
    print_color "$YELLOW" "This test simulates WSJT-X audio streams and verifies driver stability"
    echo ""
    
    # Step 1: Check prerequisites
    print_color "$CYAN" "Step 1: Checking prerequisites..."
    if ! check_alsa_loopback; then
        print_color "$RED" "Failed to set up ALSA loopback"
        exit 1
    fi
    
    verify_audio_devices
    
    # Step 2: Start dummy audio streams
    print_color "$CYAN" "\nStep 2: Starting dummy audio streams..."
    start_dummy_streams
    
    # Step 3: Start the driver
    print_color "$CYAN" "\nStep 3: Starting truSDX driver..."
    if ! start_driver; then
        print_color "$RED" "Failed to start driver"
        TEST_PASSED=false
        generate_report
        exit 1
    fi
    
    # Step 4: Monitor driver for initial period
    print_color "$CYAN" "\nStep 4: Initial stability test..."
    if ! check_driver_health 30; then
        TEST_PASSED=false
    fi
    
    # Step 5: Test stream reconnection
    print_color "$CYAN" "\nStep 5: Testing stream reconnection..."
    test_stream_reconnection
    
    # Step 6: Final stability test
    print_color "$CYAN" "\nStep 6: Final stability test..."
    start_dummy_streams  # Ensure streams are running
    if ! check_driver_health 30; then
        TEST_PASSED=false
    fi
    
    # Step 7: Generate report
    generate_report
    
    # Exit with appropriate code
    if [ "$TEST_PASSED" = true ] && [ $ERROR_COUNT -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run the main test
main
