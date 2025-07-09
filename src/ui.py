#!/usr/bin/env python3
"""
User Interface module for truSDX-AI driver.
Handles the terminal-based user interface and header information.
"""

import os
import datetime
from typing import Optional

class UserInterface:
    """Manages the terminal-based user interface for truSDX."""
    
    def __init__(self):
        self.has_color = self._check_term_color()
        self.header_lines = 7  # Number of lines used by header
        
    def _check_term_color(self) -> bool:
        """Check if terminal supports color based on TERM environment variable."""
        term = os.getenv("TERM", "")
        # Check for common color-capable terminals
        color_terms = ['xterm', 'screen', 'tmux', 'rxvt', 'konsole', 'gnome']
        return any(color_term in term for color_term in color_terms) or 'color' in term
    
    def _get_color_code(self, color_code: str) -> str:
        """Return color code if terminal supports color, otherwise empty string."""
        return color_code if self.has_color else ""
    
    def show_persistent_header(self, version: str, build_date: str, callsign: str, port_info: dict, power_info=None, reconnect_status=None):
        """Display persistent header with version, callsign, connection, and status info.
        
        Args:
            version: Software version
            build_date: Build date
            callsign: Ham radio callsign from config
            port_info: Dict with 'cat_port' and 'audio_device' keys
            power_info: Optional dict with 'watts' key
            reconnect_status: Optional reconnection status info
        """
        # Colors with fallback
        clr_green = self._get_color_code("\033[1;32m")
        clr_cyan = self._get_color_code("\033[1;36m")
        clr_yellow = self._get_color_code("\033[1;33m")
        clr_white = self._get_color_code("\033[1;37m")
        clr_magenta = self._get_color_code("\033[1;35m")
        clr_red = self._get_color_code("\033[1;31m")
        reset = self._get_color_code("\033[0m")
        
        # Clear screen and position cursor
        print("\033[2J", end="")  # Clear entire screen
        print("\033[H", end="")   # Move cursor to home position
        
        # Header line
        print(clr_green + "="*80 + reset)
        
        # Version and build date
        print(f"{clr_cyan}truSDX-AI Driver v{version}{reset} - {clr_yellow}{build_date}{reset}")
        
        # Callsign
        print(f"{clr_white}Callsign: {callsign}{reset}")
        
        # Radio connection info
        cat_port = port_info.get('cat_port', '/tmp/trusdx_cat')
        audio_device = port_info.get('audio_device', 'TRUSDX')
        
        radio_line = f"{clr_magenta}  Radio:{reset} Kenwood TS-480 | {clr_magenta}Port:{reset} {cat_port} | {clr_magenta}Baud:{reset} 115200 | {clr_magenta}Poll:{reset} 80ms"
        
        # Add power info if available
        if power_info:
            watts = power_info.get('watts', 0)
            if power_info.get('reconnecting', False) or watts == 0:
                radio_line += f" | {clr_yellow}Power: {watts}W (reconnecting...){reset}"
            else:
                radio_line += f" | {clr_green}Power: {watts}W{reset}"
        
        print(radio_line)
        
        # Audio connection info
        audio_line = f"{clr_magenta}  Audio:{reset} {audio_device} (Input/Output) | {clr_magenta}PTT:{reset} CAT"
        
        # Add reconnection status if available
        if reconnect_status:
            if reconnect_status.get('active', False):
                audio_line += f" | {clr_yellow}Status: Reconnecting...{reset}"
            else:
                audio_line += f" | {clr_green}Status: Ready{reset}"
        else:
            audio_line += f" | {clr_green}Status: Ready{reset}"
        
        print(audio_line)
        
        # Footer line
        print(clr_green + "="*80 + reset)
        print()  # Empty line
        
        # Set scrolling region to preserve header
        print(f"\033[{self.header_lines + 1};24r", end="")  # Set scrolling region
        print(f"\033[{self.header_lines + 1};1H", end="")   # Move cursor below header
    
    def refresh_header_only(self, version: str, build_date: str, callsign: str, port_info: dict, power_info=None, reconnect_status=None):
        """Refresh just the header without clearing scroll-back.
        
        Args:
            version: Software version
            build_date: Build date
            callsign: Ham radio callsign from config
            port_info: Dict with 'cat_port' and 'audio_device' keys
            power_info: Optional dict with 'watts' key
            reconnect_status: Optional reconnection status info
        """
        # Save cursor position
        print("\033[s", end="")
        
        # Move to header area and redraw
        print("\033[1;1H", end="")  # Move to top-left
        
        # Colors with fallback
        clr_green = self._get_color_code("\033[1;32m")
        clr_cyan = self._get_color_code("\033[1;36m")
        clr_yellow = self._get_color_code("\033[1;33m")
        clr_white = self._get_color_code("\033[1;37m")
        clr_magenta = self._get_color_code("\033[1;35m")
        clr_red = self._get_color_code("\033[1;31m")
        reset = self._get_color_code("\033[0m")
        
        # Clear header area only
        for i in range(self.header_lines):
            print(f"\033[{i+1};1H\033[K", end="")  # Clear each header line
        
        # Redraw header
        print("\033[1;1H", end="")  # Back to top
        
        # Header line
        print(clr_green + "="*80 + reset)
        
        # Version and build date
        print(f"{clr_cyan}truSDX-AI Driver v{version}{reset} - {clr_yellow}{build_date}{reset}")
        
        # Callsign
        print(f"{clr_white}Callsign: {callsign}{reset}")
        
        # Radio connection info
        cat_port = port_info.get('cat_port', '/tmp/trusdx_cat')
        audio_device = port_info.get('audio_device', 'TRUSDX')
        
        radio_line = f"{clr_magenta}  Radio:{reset} Kenwood TS-480 | {clr_magenta}Port:{reset} {cat_port} | {clr_magenta}Baud:{reset} 115200 | {clr_magenta}Poll:{reset} 80ms"
        
        # Add power info if available
        if power_info:
            watts = power_info.get('watts', 0)
            if power_info.get('reconnecting', False) or watts == 0:
                radio_line += f" | {clr_yellow}Power: {watts}W (reconnecting...){reset}"
            else:
                radio_line += f" | {clr_green}Power: {watts}W{reset}"
        
        print(radio_line)
        
        # Audio connection info
        audio_line = f"{clr_magenta}  Audio:{reset} {audio_device} (Input/Output) | {clr_magenta}PTT:{reset} CAT"
        
        # Add reconnection status if available
        if reconnect_status:
            if reconnect_status.get('active', False):
                audio_line += f" | {clr_yellow}Status: Reconnecting...{reset}"
            else:
                audio_line += f" | {clr_green}Status: Ready{reset}"
        else:
            audio_line += f" | {clr_green}Status: Ready{reset}"
        
        print(audio_line)
        
        # Footer line
        print(clr_green + "="*80 + reset)
        print()  # Empty line
        
        # Restore cursor position
        print("\033[u", end="")
    
    def show_version_info(self, version: str, build_date: str, author: str, platform: str, compatible_programs: list, ts480_commands: dict):
        """Display version and configuration information for connecting programs.
        
        Args:
            version: Software version
            build_date: Build date
            author: Author information
            platform: Platform identifier
            compatible_programs: List of compatible programs
            ts480_commands: Dictionary of supported CAT commands
        """
        print(f"\n=== truSDX-AI Driver v{version} ===")
        print(f"Build Date: {build_date}")
        print(f"Author: {author}")
        print(f"Platform: {platform}")
        print("\n=== Connection Information for WSJT-X/JS8Call ===")
        print("Radio Configuration:")
        print("  Rig: Kenwood TS-480")
        print("  Poll Interval: 80ms")
        print(f"  CAT Serial Port: /tmp/trusdx_cat")
        print("  Baud Rate: 115200")
        print("  Data Bits: 8")
        print("  Stop Bits: 1")
        print("  Parity: None")
        print("  Handshake: None")
        print("  PTT Method: CAT or RTS/DTR")
        print("\nAudio Configuration:")
        print(f"  Input Device: TRUSDX")
        print(f"  Output Device: TRUSDX")
        print("  Sample Rate: 48000 Hz")
        print("  Channels: 1 (Mono)")
        print("\nSupported Programs:")
        for prog in compatible_programs:
            print(f"  - {prog}")
        print("\nCAT Commands Supported:")
        for cmd, desc in list(ts480_commands.items())[:10]:  # Show first 10
            print(f"  {cmd}: {desc}")
        print(f"  ... and {len(ts480_commands)-10} more commands")
        print("\n" + "="*50)
    
    @staticmethod
    def clear_screen():
        """Clear terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
