# ALSA Audio Device Audit Results

## Date: 2025-01-13

## 1. Current ALSA Loopback Sub-devices Available

From `aplay -l` / `arecord -l`:
```
Card 0: Loopback [Loopback]
  Device 0: Loopback PCM
    - Playback: 8 subdevices (7 free, 1 used by trusdx_tx)
    - Capture: 8 subdevices (all free)
  Device 1: Loopback PCM  
    - Playback: 8 subdevices (all free)
    - Capture: 8 subdevices (all free)
```

## 2. Driver Audio Device Usage (from logs)

The truSDX driver currently opens:
```
[ALSA-AUDIT] OPENING TX STREAM: 'trusdx_tx' (PyAudio index: 16) for input from WSJT-X/JS8Call
[ALSA-AUDIT] OPENING RX STREAM: 'trusdx_rx' (PyAudio index: 17) for output to WSJT-X/JS8Call
```

Expected ALSA mappings according to driver:
- `trusdx_tx` → hw:Loopback,0,x (playback) - Driver receives TX audio from WSJT-X
- `trusdx_rx` → hw:Loopback,1,x (capture) - Driver sends RX audio to WSJT-X

## 3. Current .asoundrc Configuration (INCORRECT)

```
pcm.trusdx_tx {
    type plug
    slave {
        pcm "hw:Loopback,0,0"  # ✓ Correct: Playback device
        rate 48000
        format S16_LE
        channels 1
    }
}

pcm.trusdx_rx {
    type plug
    slave {
        pcm "hw:Loopback,0,1"  # ✗ WRONG: Should be hw:Loopback,1,0 (capture)
        rate 48000
        format S16_LE
        channels 1
    }
}
```

## 4. Issue Identified

The `.asoundrc` file has an incorrect mapping for `trusdx_rx`. It currently points to:
- `hw:Loopback,0,1` (which is device 0, subdevice 1, PLAYBACK)

But it should point to:
- `hw:Loopback,1,0` (which is device 1, subdevice 0, CAPTURE)

## 5. Correct ALSA Loopback Architecture

For proper loopback operation:

### TX Path (WSJT-X → Driver → Radio):
1. WSJT-X writes audio to `hw:Loopback,0,0` (playback)
2. Driver reads from `hw:Loopback,1,0` (capture - the other end of the loopback)
3. Driver sends to radio via serial

### RX Path (Radio → Driver → WSJT-X):
1. Driver receives audio from radio via serial
2. Driver writes to `hw:Loopback,0,1` (playback)
3. WSJT-X reads from `hw:Loopback,1,1` (capture - the other end of the loopback)

## 6. Free Sub-devices for WSJT-X

Based on the audit, the following sub-devices are available for WSJT-X:
- **hw:Loopback,0,1** - Playback (for WSJT-X to receive RX audio)
- **hw:Loopback,1,1** - Capture (for WSJT-X to monitor its own TX)

## 7. Required Corrections

1. Fix `.asoundrc` to use correct device mappings
2. Update driver to properly use the loopback pairs
3. Configure WSJT-X to use the correct ALSA devices directly instead of PulseAudio

## 8. WSJT-X Current Configuration

From `~/.config/WSJT-X.ini`:
```
SoundInName=alsa_output.platform-snd_aloop.0.analog-stereo.monitor
SoundOutName=alsa_output.platform-snd_aloop.0.analog-stereo
```

This shows WSJT-X is currently using PulseAudio, not direct ALSA access.

## Outcome

✅ Confirmed current mapping and identified configuration errors
✅ Identified free sub-devices: hw:Loopback,0,1 and hw:Loopback,1,1 for WSJT-X
✅ Documented required corrections to avoid conflicts

The main issue is that the `.asoundrc` file has incorrect device mappings that don't properly utilize the ALSA loopback architecture's capture/playback pairs.
