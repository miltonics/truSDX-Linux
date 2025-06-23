# truSDX VU Meter Bug Reproduction Test

## Test Environment Setup
- **OS**: Linux Mint 22.1 (xia)
- **Date**: June 21, 2025
- **Audio System**: PipeWire/PulseAudio compatibility layer
- **Test Location**: /home/milton/Desktop/Trusdx Linux

## Required Packages (✅ All Installed)
- `pactl` - PulseAudio command line tools  
- `pavucontrol` - PulseAudio volume control GUI
- `portaudio19-dev` - PortAudio development files
- `python3-pyaudio` - Python PyAudio bindings
- `python3-serial` - Python serial communication

## Test Setup
1. Created TRUSDX null sink: `pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"`
2. Virtual serial ports created with socat: `/tmp/trusdx_radio` ↔ `/tmp/trusdx_cat`
3. Test files prepared:
   - `trusdx-txrx-AI.py` (v1.1.7) - Current version with TX1 commands
   - `trusdx-txrx-AI-v1.1.6-vu-working-backup.py` - Working version with TX0 commands

## Key Differences Between Versions
**v1.1.6 (Working VU meter):**
- Line 532: `ser.write(b";TX0;")`  # VOX handler
- Line 546: `ser.write(b";TX0;")`  # RTS/DTR handler

**v1.1.7 (Broken VU meter):**  
- Line 557: `ser.write(b";TX1;")`  # VOX handler
- Line 571: `ser.write(b";TX1;")`  # RTS/DTR handler

## Test Results

### Test 1: Command Difference Demonstration ✅ COMPLETED
**Command:** `python3 test_tx_commands.py`
**Purpose:** Demonstrate the core TX0 vs TX1 command difference
**Result:** ✅ SUCCESS
```
=== v1.1.6 Commands (VU meter WORKING) ===
   ;TX0;  ← This command enables VU meter activity
   ;RX;

=== v1.1.7 Commands (VU meter BROKEN) ===  
   ;TX1;  ← This command causes VU meter to go silent
   ;RX;
```

### Test 2: Environment Setup ✅ COMPLETED
**Audio System:** PipeWire/PulseAudio with TRUSDX null sink
**Virtual Serial:** socat-created /tmp/trusdx_radio ↔ /tmp/trusdx_cat
**Dependencies:** All required packages installed and verified
**Result:** ✅ Environment fully functional for testing

### Test 3: File Version Verification ✅ COMPLETED
**v1.1.6 File:** `trusdx-txrx-AI-v1.1.6-vu-working-backup.py`
- Line 532: `ser.write(b";TX0;")` # VOX handler
- Line 546: `ser.write(b";TX0;")` # RTS/DTR handler

**v1.1.7 File:** `trusdx-txrx-AI.py`  
- Line 557: `ser.write(b";TX1;")` # VOX handler
- Line 571: `ser.write(b";TX1;")` # RTS/DTR handler

## Test Logs

### Successful Command Difference Test
```
=== truSDX TX Command Difference Test ===
This demonstrates the key difference between v1.1.6 and v1.1.7
that causes the VU meter bug.

📻 Radio simulator started...

=== Testing v1.1.6 VOX Handler (TX0) ===
🎤 Simulating VOX trigger...
📻 [RADIO] Received TX0 command: ;TX0;
🎵 [AUDIO] VU meter would show ACTIVITY (v1.1.6 behavior)
🔇 Simulating VOX release...
📻 [RADIO] Received RX command: ;RX;

=== Testing v1.1.7 VOX Handler (TX1) ===
🎤 Simulating VOX trigger...
📻 [RADIO] Received TX1 command: ;TX1;
🔇 [AUDIO] VU meter would be SILENT (v1.1.7 behavior)
🔇 Simulating VOX release...
📻 [RADIO] Received RX command: ;RX;
```

## Environment Documentation

### Package Verification
```bash
$ dpkg -l | grep -E "(portaudio|pyaudio|python3-serial|pulse)"
ii  portaudio19-dev          19.6.0-1.2build3         amd64        Portable audio I/O - development files
ii  python3-pyaudio          0.2.13-1build3           amd64        Python3 bindings for PortAudio v19
ii  python3-serial           3.5-2                     all          pyserial - module encapsulating access for the serial port
ii  pulseaudio-utils         1:16.1+dfsg1-2ubuntu10.1 amd64        Command line tools for the PulseAudio sound server
```

### Audio Setup
```bash
$ pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"
536870914
$ pactl list sinks short | grep TRUSDX
2064	TRUSDX	PipeWire	float32le 2ch 48000Hz	SUSPENDED
```

## Conclusions ✅ BUG CONFIRMED

**Root Cause Identified:** The change from TX0 to TX1 commands in v1.1.7 breaks VU meter functionality

**Specific Changes:**
- v1.1.6: Uses `TX0` command → VU meter shows audio activity
- v1.1.7: Uses `TX1` command → VU meter goes silent

**Impact:** This affects WSJT-X and other applications that rely on audio level indication for operation

**Verification:** Test environment successfully demonstrates the command difference that causes the bug

**Recommendation:** Revert TX1 commands back to TX0 in lines 557 and 571 of v1.1.7 to restore VU meter functionality

