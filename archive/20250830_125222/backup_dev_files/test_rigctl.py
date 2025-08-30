#!/usr/bin/env python3
"""
Test rigctl interaction using socat
"""

import subprocess
import time
import threading
import os
import signal
from unittest.mock import MagicMock

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", "trusdx-txrx-AI.py")
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

class RigctlTest:
    def __init__(self):
        self.socat_process = None
        self.cat_port = '/tmp/trusdx_cat'
        
        # Mock config
        trusdx.config = {'verbose': True}
        
        # Mock serial
        self.mock_ser = MagicMock()
        
        # Mock log function
        trusdx.log = lambda msg, level='INFO': print(f"[{level}] {msg}")
        
        # Set up initial radio state
        trusdx.radio_state = {
            'vfo_a_freq': '00014074000',  # 14.074 MHz
            'vfo_b_freq': '00014074000',  # 14.074 MHz
            'mode': '2',                  # USB
            'rx_vfo': '0',               # VFO A
            'tx_vfo': '0',               # VFO A
            'split': '0',                # Split off
            'rit': '0',                  # RIT off
            'xit': '0',                  # XIT off
            'rit_offset': '00000',       # No offset
            'power_on': '1',             # Power on
            'ai_mode': '2'               # Auto info on
        }
        
    def create_socat_bridge(self):
        """Create socat bridge for testing"""
        # Create bidirectional pipe
        cmd = [
            'socat', 
            '-d', '-d',
            f'pty,link={self.cat_port},raw,echo=0',
            'exec:python3 test_cat_handler.py'
        ]
        
        try:
            self.socat_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for socat to create the link
            time.sleep(1)
            
            if os.path.exists(self.cat_port):
                print(f"✅ Created CAT port: {self.cat_port}")
                return True
            else:
                print(f"❌ Failed to create CAT port: {self.cat_port}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating socat bridge: {e}")
            return False
    
    def test_rigctl_commands(self):
        """Test rigctl commands"""
        commands = [
            ('V', 'Get current VFO'),
            ('f', 'Get frequency'),
            ('vfo', 'Get VFO info'),
            ('i', 'Get radio info'),
        ]
        
        print("Testing rigctl commands...")
        
        for cmd, description in commands:
            print(f"\n🔍 Testing: {description}")
            try:
                result = subprocess.run(
                    ['rigctl', '-m', '2028', '-r', self.cat_port, cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print(f"✅ Command '{cmd}' succeeded")
                    print(f"   Output: {result.stdout.strip()}")
                else:
                    print(f"❌ Command '{cmd}' failed (code: {result.returncode})")
                    print(f"   Error: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                print(f"❌ Command '{cmd}' timed out")
            except Exception as e:
                print(f"❌ Command '{cmd}' error: {e}")
                
            time.sleep(0.5)  # Small delay between commands
    
    def cleanup(self):
        """Clean up resources"""
        if self.socat_process:
            try:
                os.killpg(os.getpgid(self.socat_process.pid), signal.SIGTERM)
                self.socat_process.wait(timeout=5)
            except:
                pass
        
        if os.path.exists(self.cat_port):
            try:
                os.remove(self.cat_port)
            except:
                pass
        
        print("🧹 Cleanup completed")

def main():
    # First create the CAT handler script
    handler_script = '''#!/usr/bin/env python3
import sys
import os
from unittest.mock import MagicMock

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", "trusdx-txrx-AI.py")
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

# Mock config
trusdx.config = {'verbose': True}

# Mock serial
mock_ser = MagicMock()

# Mock log function
trusdx.log = lambda msg, level='INFO': sys.stderr.write(f"[{level}] {msg}\\n")

# Set up initial radio state
trusdx.radio_state = {
    'vfo_a_freq': '00014074000',  # 14.074 MHz
    'vfo_b_freq': '00014074000',  # 14.074 MHz
    'mode': '2',                  # USB
    'rx_vfo': '0',               # VFO A
    'tx_vfo': '0',               # VFO A
    'split': '0',                # Split off
    'rit': '0',                  # RIT off
    'xit': '0',                  # XIT off
    'rit_offset': '00000',       # No offset
    'power_on': '1',             # Power on
    'ai_mode': '2'               # Auto info on
}

# Simple CAT handler that reads from stdin and writes to stdout
buffer = b''
while True:
    try:
        data = sys.stdin.buffer.read(1)
        if not data:
            break
        
        buffer += data
        
        # Process complete commands
        if b';' in buffer:
            commands = buffer.split(b';')
            buffer = commands[-1]  # Keep incomplete command
            
            for cmd in commands[:-1]:
                if cmd.strip():
                    full_cmd = cmd + b';'
                    sys.stderr.write(f"Processing: {full_cmd}\\n")
                    
                    response = trusdx.handle_ts480_command(full_cmd, mock_ser)
                    if response:
                        sys.stderr.write(f"Response: {response}\\n")
                        sys.stdout.buffer.write(response)
                        sys.stdout.buffer.flush()
                    else:
                        sys.stderr.write("No response (forwarded to radio)\\n")
                        
    except Exception as e:
        sys.stderr.write(f"Error: {e}\\n")
        break
'''
    
    # Write the handler script
    with open('test_cat_handler.py', 'w') as f:
        f.write(handler_script)
    
    os.chmod('test_cat_handler.py', 0o755)
    
    # Now run the test
    tester = RigctlTest()
    
    try:
        if tester.create_socat_bridge():
            time.sleep(2)  # Wait for socat to stabilize
            tester.test_rigctl_commands()
        else:
            print("❌ Failed to create socat bridge")
    
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    
    finally:
        tester.cleanup()
        
        # Remove test files
        try:
            os.remove('test_cat_handler.py')
        except:
            pass

if __name__ == '__main__':
    main()
