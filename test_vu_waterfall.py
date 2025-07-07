#!/usr/bin/env python3
"""
Test VU Meter and Waterfall Implementation
This script tests the GUI components independently of the main truSDX driver
"""

import sys
import time
import array
import math
import threading

# Test if GUI dependencies are available
try:
    import tkinter as tk
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    GUI_AVAILABLE = True
    print("✅ GUI dependencies available")
except ImportError as e:
    print(f"❌ GUI dependencies missing: {e}")
    sys.exit(1)

# Test configuration
GUI_UPDATE_INTERVAL = 0.1  # 100ms throttling
WATERFALL_HEIGHT = 200     # Number of FFT slices to keep (rolling buffer height)
FFT_SIZE = 512             # FFT size for spectrum analysis (512 frames as requested)
audio_rx_rate = 7812       # Same as truSDX

# GUI state for testing
gui_state = {
    'figure': None,
    'canvas': None,
    'ax_waterfall': None,
    'ax_vu': None,
    'waterfall_data': None,
    'vu_bar': None,
    'last_update': 0,
    'root': None,
    'window_open': False
}

def update_vu_display(level, mode='rx'):
    """Update the VU bar display"""
    try:
        if not gui_state.get('ax_vu') or not gui_state.get('vu_bar'):
            return
            
        # Update VU bar width (for horizontal bar)
        gui_state['vu_bar'].set_width(level)
        
        # Color based on level and mode
        if level > 0.8:
            color = 'red'  # Overload
        elif level > 0.6:
            color = 'orange'  # High
        elif mode == 'tx':
            color = 'lightcoral'  # TX mode
        else:
            color = 'lightgreen'  # RX mode
            
        gui_state['vu_bar'].set_color(color)
        
        # Update title with level percentage
        gui_state['ax_vu'].set_title(f"VU Meter ({mode.upper()}) - {level*100:.0f}%")
        
    except Exception as e:
        print(f"VU display update error: {e}")

def update_waterfall_with_fft(samples):
    """Update waterfall display with FFT of audio samples"""
    try:
        if not gui_state.get('ax_waterfall') or len(samples) < FFT_SIZE:
            return
            
        # Pad or truncate samples to FFT_SIZE
        if len(samples) > FFT_SIZE:
            samples = samples[:FFT_SIZE]
        elif len(samples) < FFT_SIZE:
            samples = np.pad(samples, (0, FFT_SIZE - len(samples)))
        
        # Apply window function to reduce spectral leakage
        windowed_samples = samples * np.hanning(FFT_SIZE)
        
        # Compute FFT as specified: 20*log10(abs(rfft(windowed_samples))+1e-6)
        fft = 20 * np.log10(np.abs(np.fft.rfft(windowed_samples)) + 1e-6)
        
        # Normalize to 0-1 range for display
        min_db, max_db = -60, 20  # Typical dynamic range
        fft_norm = np.clip((fft - min_db) / (max_db - min_db), 0, 1)
        
        # Initialize rolling numpy image buffer (512×200) if needed
        if gui_state['waterfall_data'] is None:
            gui_state['waterfall_data'] = np.zeros((WATERFALL_HEIGHT, len(fft_norm)))
        
        # Shift existing data up and add new column at bottom (rolling buffer)
        gui_state['waterfall_data'][:-1] = gui_state['waterfall_data'][1:]
        gui_state['waterfall_data'][-1] = fft_norm
        
        # Update waterfall image with specified parameters
        gui_state['ax_waterfall'].clear()
        gui_state['ax_waterfall'].imshow(
            gui_state['waterfall_data'], 
            aspect='auto', 
            origin='lower',  # Changed from 'upper' to 'lower' as specified
            cmap='viridis',
            extent=[0, audio_rx_rate//2, 0, WATERFALL_HEIGHT]
        )
        gui_state['ax_waterfall'].set_title("Waterfall Display (512 frames FFT)")
        gui_state['ax_waterfall'].set_xlabel("Frequency (Hz)")
        gui_state['ax_waterfall'].set_ylabel("Time (newer at top)")
        
    except Exception as e:
        print(f"Waterfall FFT update error: {e}")

def initialize_gui():
    """Initialize GUI components with persistent figure"""
    try:
        # Create main window
        gui_state['root'] = tk.Tk()
        gui_state['root'].title("truSDX VU Meter & Waterfall Test")
        gui_state['root'].geometry("800x600")
        
        # Create persistent figure with two subplots
        gui_state['figure'] = Figure(figsize=(10, 8), dpi=80)
        
        # Create two axes: waterfall (top) and VU meter (bottom)
        gui_state['ax_waterfall'] = gui_state['figure'].add_subplot(2, 1, 1)
        gui_state['ax_vu'] = gui_state['figure'].add_subplot(2, 1, 2)
        
        # Initialize waterfall data (512×200 rolling buffer)
        gui_state['waterfall_data'] = np.zeros((WATERFALL_HEIGHT, FFT_SIZE//2 + 1))  # +1 for rfft output size
        
        # Setup waterfall plot
        gui_state['ax_waterfall'].imshow(
            gui_state['waterfall_data'], 
            aspect='auto', 
            cmap='viridis', 
            origin='lower',
            extent=[0, audio_rx_rate//2, 0, WATERFALL_HEIGHT]
        )
        gui_state['ax_waterfall'].set_title("Waterfall Display")
        gui_state['ax_waterfall'].set_xlabel("Frequency (Hz)")
        gui_state['ax_waterfall'].set_ylabel("Time (newer at bottom)")
        
        # Setup VU meter as horizontal bar
        gui_state['vu_bar'] = gui_state['ax_vu'].barh([0], [0], height=0.5, color='lightgreen')[0]
        gui_state['ax_vu'].set_xlim(0, 1)
        gui_state['ax_vu'].set_ylim(-0.5, 0.5)
        gui_state['ax_vu'].set_xlabel("Level")
        gui_state['ax_vu'].set_title("VU Meter (RX) - 0%")
        gui_state['ax_vu'].grid(True, alpha=0.3)
        
        # Remove y-axis labels for VU meter (cleaner look)
        gui_state['ax_vu'].set_yticks([])
        
        # Create canvas
        gui_state['canvas'] = FigureCanvasTkAgg(gui_state['figure'], master=gui_state['root'])
        gui_state['canvas'].draw()
        gui_state['canvas'].get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # Handle window close event
        def on_closing():
            gui_state['window_open'] = False
            gui_state['root'].destroy()
            
        gui_state['root'].protocol("WM_DELETE_WINDOW", on_closing)
        
        # Initialize update timestamp
        gui_state['last_update'] = 0
        
        # Start GUI in non-blocking mode
        gui_state['window_open'] = True
        
        print("✅ GUI initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ GUI initialization failed: {e}")
        return False

def simulate_audio_data():
    """Simulate audio data for testing"""
    while gui_state['window_open']:
        try:
            # Generate simulated audio samples
            t = time.time()
            
            # Simulate RX level that varies with time
            rx_level = abs(math.sin(t * 0.5)) * 0.7  # Slow sine wave
            
            # Simulate some signal with multiple frequencies
            freq1 = 1000  # 1 kHz tone
            freq2 = 2000  # 2 kHz tone
            sample_rate = audio_rx_rate
            samples = []
            
            for i in range(FFT_SIZE):
                sample_time = i / sample_rate
                signal = (math.sin(2 * math.pi * freq1 * sample_time) * rx_level +
                         math.sin(2 * math.pi * freq2 * sample_time) * rx_level * 0.5)
                samples.append(signal * 1000)  # Scale for visibility
            
            # Convert to numpy array
            audio_samples = np.array(samples, dtype=np.float32)
            
            # Throttle updates to 100ms as requested
            current_time = time.time()
            if current_time - gui_state.get('last_update', 0) >= GUI_UPDATE_INTERVAL:
                # Update VU meter
                update_vu_display(rx_level, 'rx')
                
                # Update waterfall
                update_waterfall_with_fft(audio_samples)
                
                gui_state['last_update'] = current_time
                
                # Schedule canvas update
                if gui_state.get('canvas'):
                    gui_state['canvas'].draw_idle()
            
            time.sleep(0.05)  # 50ms between data generation
            
        except Exception as e:
            print(f"❌ Error in audio simulation: {e}")
            break

def update_gui():
    """Update GUI in main thread"""
    if gui_state['window_open'] and gui_state['root']:
        try:
            gui_state['root'].update_idletasks()
            gui_state['root'].after(50, update_gui)  # Schedule next update
        except tk.TclError:
            # Window was closed
            gui_state['window_open'] = False

def main():
    print("=== VU Meter & Waterfall Test ===")
    print()
    
    # Initialize GUI
    if not initialize_gui():
        return 1
    
    print("✅ Starting GUI update loop...")
    gui_state['root'].after(50, update_gui)
    
    print("✅ Starting audio simulation...")
    audio_thread = threading.Thread(target=simulate_audio_data, daemon=True)
    audio_thread.start()
    
    print("✅ GUI window should now be visible with animated VU meter and waterfall")
    print("ℹ️  Close the window to exit")
    
    # Run GUI main loop
    try:
        gui_state['root'].mainloop()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    print("✅ Test completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
