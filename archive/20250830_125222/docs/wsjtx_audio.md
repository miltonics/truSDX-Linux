# WSJT-X Audio Configuration for (tr)uSDX

This guide explains how to configure WSJT-X to work with the (tr)uSDX radio using ALSA loopback devices.

## Prerequisites

- WSJT-X installed on your system
- trusdx-audio-connect script properly configured
- ALSA loopback module loaded

## Audio Configuration Steps

### 1. Open WSJT-X Settings

Open WSJT-X and navigate to:
- **File** → **Settings** (or press F2)
- Select the **Audio** tab

### 2. Configure Audio Input (RX)

Set the audio input device for receiving:

- **Input**: Select **trusdx_rx_app**
  - This is the ALSA loopback capture sub-device 1
  - It receives audio from the (tr)uSDX radio

![Audio Input Configuration](screenshots/wsjtx_input.png)

### 3. Configure Audio Output (TX)

Set the audio output device for transmitting:

- **Output**: Select **trusdx_tx_app**
  - This is the ALSA loopback playback sub-device 1
  - It sends audio to the (tr)uSDX radio

![Audio Output Configuration](screenshots/wsjtx_output.png)

### 4. Complete Configuration

The complete audio configuration should look like this:

- **Input**: `trusdx_rx_app` (ALSA loopback capture sub-device 1)
- **Output**: `trusdx_tx_app` (ALSA loopback playback sub-device 1)

![Complete Audio Configuration](screenshots/wsjtx_complete.png)

### 5. Apply Settings

Click **OK** to save and apply the settings.

## Verification

To verify the configuration is working:

1. Ensure the trusdx-audio-connect script is running
2. Check that audio levels are showing in WSJT-X when receiving
3. Test transmission with a low power setting

## Troubleshooting

If audio is not working:

1. Verify ALSA loopback devices are created:
   ```bash
   aplay -l | grep Loopback
   arecord -l | grep Loopback
   ```

2. Check that the trusdx-audio-connect script is running:
   ```bash
   ps aux | grep trusdx-audio-connect
   ```

3. Ensure the correct devices are selected in WSJT-X settings

4. Check audio levels:
   - RX audio should show activity in the WSJT-X waterfall
   - TX audio levels should be adjusted to avoid overdriving

## Notes

- The `trusdx_rx_app` and `trusdx_tx_app` devices are created by the ALSA configuration
- These virtual devices route audio between WSJT-X and the (tr)uSDX radio
- Make sure no other applications are using these audio devices simultaneously
