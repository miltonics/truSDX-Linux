#!/usr/bin/env python3
"""
Auto-route Python audio streams to TRUSDX virtual device
This script monitors for new Python audio streams and automatically routes them to TRUSDX
"""

import subprocess
import time
import re

def get_sink_inputs():
    """Get list of current sink inputs"""
    try:
        result = subprocess.run(['pactl', 'list', 'short', 'sink-inputs'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []

def get_trusdx_sink_id():
    """Get the TRUSDX sink ID"""
    try:
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                              capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if 'TRUSDX' in line:
                return line.split('\t')[0]
        return None
    except subprocess.CalledProcessError:
        return None

def move_python_streams_to_trusdx():
    """Move all Python audio streams to TRUSDX device"""
    trusdx_sink = get_trusdx_sink_id()
    if not trusdx_sink:
        print("TRUSDX sink not found!")
        return False
    
    sink_inputs = get_sink_inputs()
    moved_count = 0
    
    for line in sink_inputs:
        if not line.strip():
            continue
            
        # Get sink input details
        try:
            result = subprocess.run(['pactl', 'list', 'sink-inputs'], 
                                  capture_output=True, text=True, check=True)
            
            # Look for Python audio streams not already on TRUSDX
            for block in result.stdout.split('Sink Input #'):
                if not block.strip():
                    continue
                    
                # Check if this is a Python stream
                if 'python' in block.lower() and f'Sink: {trusdx_sink}' not in block:
                    # Extract sink input ID
                    match = re.search(r'^(\d+)', block)
                    if match:
                        sink_input_id = match.group(1)
                        print(f"Moving sink input #{sink_input_id} to TRUSDX...")
                        try:
                            subprocess.run(['pactl', 'move-sink-input', sink_input_id, 'TRUSDX'], 
                                         check=True)
                            moved_count += 1
                            print(f"✅ Successfully moved sink input #{sink_input_id} to TRUSDX")
                        except subprocess.CalledProcessError as e:
                            print(f"❌ Failed to move sink input #{sink_input_id}: {e}")
                            
        except subprocess.CalledProcessError:
            continue
    
    return moved_count > 0

if __name__ == "__main__":
    print("🔊 Auto-routing Python audio streams to TRUSDX...")
    
    # Run once immediately
    success = move_python_streams_to_trusdx()
    if success:
        print("✅ Audio routing completed successfully!")
    else:
        print("ℹ️  No Python streams found to route")
    
    # Monitor for new streams (optional - run for 30 seconds)
    print("📡 Monitoring for new streams for 30 seconds...")
    start_time = time.time()
    while time.time() - start_time < 30:
        move_python_streams_to_trusdx()
        time.sleep(2)
    
    print("🏁 Audio routing monitor finished")
