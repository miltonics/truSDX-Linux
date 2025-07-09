# Troubleshooting Guide

This guide helps resolve common issues with the truSDX-AI Driver.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Connection Problems](#connection-problems)
3. [Audio Issues](#audio-issues)
4. [CAT Control Problems](#cat-control-problems)
5. [Performance Issues](#performance-issues)
6. [Hardware Detection](#hardware-detection)
7. [Software Integration](#software-integration)
8. [Debugging Tools](#debugging-tools)

## Installation Issues

### Python Dependencies

**Problem**: Missing Python dependencies
**Solution**: Install required packages:
```bash
sudo apt install python3 python3-pip portaudio19-dev pulseaudio-utils
pip3 install --user -r requirements.txt
```

### Permission Errors

**Problem**: USB device access denied
**Solution**: Add user to dialout group:
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

### Audio System Issues

**Problem**: PulseAudio not running
**Solution**: Start PulseAudio service:
```bash
pulseaudio --start
systemctl --user enable pulseaudio
```

## Connection Problems

### TruSDX Not Detected

**Problem**: Driver can't find TruSDX device
**Symptoms**: 
- "No TruSDX device found" error
- Device not showing in `/dev/ttyUSB*`

**Solutions**:
1. Check USB connection:
   ```bash
   lsusb | grep -i trusdx
   dmesg | tail -20
   ```

2. Verify device permissions:
   ```bash
   ls -la /dev/ttyUSB*
   ```

3. Check for conflicting drivers:
   ```bash
   sudo modprobe -r usbserial
   sudo modprobe usbserial
   ```

### Connection Drops

**Problem**: Frequent connection drops during operation
**Symptoms**:
- TX/RX switching fails
- CAT commands timeout
- Audio interruptions

**Solutions**:
1. Check USB cable quality
2. Use a powered USB hub
3. Reduce system load
4. Enable hardware monitoring:
   ```bash
   python3 trusdx-txrx-AI.py --verbose
   ```

## Audio Issues

### No Audio Output

**Problem**: No audio from TruSDX
**Symptoms**:
- VU meter shows no activity
- JS8Call receives no audio

**Solutions**:
1. Check audio device detection:
   ```bash
   pactl list sources | grep -i trusdx
   ```

2. Verify audio routing:
   ```bash
   python3 -c "from src.audio_io import AudioManager; am = AudioManager(); am.list_devices()"
   ```

3. Test audio loopback:
   ```bash
   python3 test_audio_handling.py
   ```

### Audio Distortion

**Problem**: Distorted or choppy audio
**Solutions**:
1. Adjust buffer sizes:
   ```bash
   python3 trusdx-txrx-AI.py -B 1024 -T 96
   ```

2. Check system audio settings:
   ```bash
   pulseaudio --dump-conf | grep -i sample
   ```

### VU Meter Not Working

**Problem**: VU meter shows no activity
**Solutions**:
1. Enable VU meter explicitly:
   ```bash
   python3 trusdx-txrx-AI.py --unmute
   ```

2. Test VU meter functionality:
   ```bash
   python3 test_vu_meter.py
   ```

## CAT Control Problems

### JS8Call Can't Connect

**Problem**: JS8Call shows "CAT control error"
**Solutions**:
1. Verify driver is running:
   ```bash
   netstat -an | grep 4532
   ```

2. Check firewall settings:
   ```bash
   sudo ufw status
   ```

3. Test CAT emulation:
   ```bash
   python3 test_cat_emulation.py
   ```

### Frequency Sync Issues

**Problem**: Frequency not synchronized between radio and software
**Solutions**:
1. Enable frequency debugging:
   ```bash
   python3 trusdx-txrx-AI.py --verbose
   ```

2. Check frequency initialization:
   ```bash
   python3 test_js8call_config.py
   ```

### TX/RX Switching Problems

**Problem**: Radio doesn't switch between TX and RX
**Solutions**:
1. Test TX0 command handling:
   ```bash
   python3 test_cat_direct.py
   ```

2. Disable power monitoring if causing issues:
   ```bash
   python3 trusdx-txrx-AI.py --no-power-monitor
   ```

## Performance Issues

### High CPU Usage

**Problem**: Driver consuming excessive CPU
**Solutions**:
1. Optimize audio buffer sizes
2. Reduce debugging verbosity
3. Check for memory leaks:
   ```bash
   python3 -m memory_profiler trusdx-txrx-AI.py
   ```

### Memory Leaks

**Problem**: Memory usage increases over time
**Solutions**:
1. Enable connection monitoring:
   ```bash
   python3 trusdx-txrx-AI.py --verbose
   ```

2. Check for thread cleanup issues
3. Monitor with system tools:
   ```bash
   top -p $(pgrep -f trusdx-txrx-AI.py)
   ```

## Hardware Detection

### USB Device Issues

**Problem**: Hardware not recognized consistently
**Solutions**:
1. Check USB enumeration:
   ```bash
   dmesg | grep -i usb
   ```

2. Test hardware detection:
   ```bash
   python3 test_connection_manager.py
   ```

3. Verify driver binding:
   ```bash
   ls -la /sys/class/tty/ttyUSB*
   ```

## Software Integration

### WSJT-X Configuration

**Problem**: WSJT-X not working with driver
**Solutions**:
1. Configure WSJT-X CAT settings:
   - Radio: Kenwood TS-480
   - Port: localhost:4532
   - Data bits: 8
   - Stop bits: 1
   - Parity: None

   ![WSJT-X Radio Configuration](images/wsjt-x-radio-config.png)
   ![WSJT-X CAT Settings](images/wsjt-x-cat-settings.png)
   ![WSJT-X Audio Settings](images/wsjt-x-audio-settings.png)

2. Test WSJT-X integration:
   ```bash
   python3 test_wsjt_integration.py
   ```

### JS8Call Integration

**Problem**: JS8Call specific issues
**Solutions**:
1. Verify JS8Call version compatibility (v2.2+)
2. Configure JS8Call radio settings:
   - Radio: Kenwood TS-480
   - CAT Control: Network
   - Host: localhost
   - Port: 4532

   ![JS8Call Radio Configuration](images/js8call-radio-config.png)
   ![JS8Call CAT Settings](images/js8call-cat-settings.png)
   ![JS8Call Audio Settings](images/js8call-audio-settings.png)

3. Check configuration file:
   ```bash
   cat ~/.config/trusdx-ai/config.json
   ```

## Debugging Tools

### Enable Verbose Logging

```bash
python3 trusdx-txrx-AI.py --verbose --logfile ~/trusdx-debug.log
```

### System Information

```bash
python3 -c "
import platform
import sys
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.architecture()}')
"
```

### Network Debugging

```bash
# Test CAT interface
telnet localhost 4532

# Monitor network traffic
sudo tcpdump -i lo -A port 4532
```

### Audio System Debugging

```bash
# List audio devices
pactl list sources short
pactl list sinks short

# Monitor audio
pactl list source-outputs
```

### Hardware Debugging

```bash
# USB device information
lsusb -v | grep -A 50 -B 5 -i trusdx

# Serial port information
setserial -g /dev/ttyUSB*
```

## Common Error Messages

### "No TruSDX device found"
- Check USB connection
- Verify device permissions
- Ensure drivers are loaded

### "CAT control error"
- Verify driver is running
- Check network connectivity
- Test CAT emulation

### "Audio device not found"
- Check PulseAudio status
- Verify device permissions
- Test audio routing

### "Permission denied"
- Add user to dialout group
- Check device permissions
- Verify USB access rights

## Getting Help

If these solutions don't resolve your issue:

1. **Check the logs**: Look for error messages in the console output
2. **Enable verbose mode**: Run with `--verbose` flag for detailed debugging
3. **Test components**: Use the provided test scripts to isolate issues
4. **Report bugs**: Create a GitHub issue with:
   - System information
   - Error messages
   - Configuration details
   - Steps to reproduce

## Additional Resources

- [Main Documentation](README.md)
- [Testing Guide](testing.md)
- [Architecture Overview](architecture.md)
- [GitHub Issues](https://github.com/your-username/trusdx-ai/issues)

---

*Last updated: 2025-01-27*
*Version: 1.2.0-AI-MONITORING-RECONNECT*
