#!/usr/bin/env python3
"""
Log analysis script for truSDX-AI JSON formatted logs.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter
import argparse

def analyze_log_file(log_file_path):
    """Analyze a JSON-formatted log file."""
    
    if not Path(log_file_path).exists():
        print(f"Log file not found: {log_file_path}")
        return
    
    entries = []
    parse_errors = 0
    
    print(f"Analyzing log file: {log_file_path}")
    print("=" * 60)
    
    # Read and parse log entries
    with open(log_file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line.strip())
                entries.append(entry)
            except json.JSONDecodeError:
                parse_errors += 1
                if parse_errors <= 5:  # Show first 5 errors
                    print(f"Parse error on line {line_num}: {line.strip()}")
    
    if not entries:
        print("No valid log entries found.")
        return
    
    # Basic statistics
    total_entries = len(entries)
    level_counts = Counter(entry['level'] for entry in entries)
    module_counts = Counter(entry['module'] for entry in entries)
    
    print(f"\nTotal log entries: {total_entries}")
    if parse_errors:
        print(f"Parse errors: {parse_errors}")
    
    # Time range
    timestamps = [datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) 
                  for entry in entries]
    if timestamps:
        start_time = min(timestamps)
        end_time = max(timestamps)
        print(f"Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Log level distribution
    print("\\nLog level distribution:")
    for level, count in level_counts.most_common():
        percentage = (count / total_entries) * 100
        print(f"  {level:10s}: {count:5d} ({percentage:5.1f}%)")
    
    # Module distribution
    print("\\nTop modules by log count:")
    for module, count in module_counts.most_common(10):
        percentage = (count / total_entries) * 100
        print(f"  {module:20s}: {count:5d} ({percentage:5.1f}%)")
    
    # Error and critical messages
    error_entries = [e for e in entries if e['level'] in ['ERROR', 'CRITICAL']]
    if error_entries:
        print(f"\\nError/Critical messages ({len(error_entries)}):")
        for entry in error_entries[-10:]:  # Show last 10 errors
            timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            print(f"  {timestamp.strftime('%H:%M:%S')} [{entry['level']}] {entry['message']}")
    
    # Reconnect events
    reconnect_entries = [e for e in entries if e['level'] == 'RECONNECT']
    if reconnect_entries:
        print(f"\\nReconnect events ({len(reconnect_entries)}):")
        for entry in reconnect_entries[-5:]:  # Show last 5 reconnects
            timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            print(f"  {timestamp.strftime('%H:%M:%S')} {entry['message']}")
    
    # Performance metrics (if available)
    performance_entries = [e for e in entries if 'duration' in e or 'frequency' in e]
    if performance_entries:
        print(f"\\nPerformance-related entries: {len(performance_entries)}")
    
    print("\\n" + "=" * 60)
    print("Analysis complete")

def main():
    parser = argparse.ArgumentParser(description="Analyze truSDX-AI log files")
    parser.add_argument("logfile", nargs="?", 
                       default=str(Path.home() / ".cache" / "trusdx" / "logs" / "trusdx.log"),
                       help="Path to log file (default: ~/.cache/trusdx/logs/trusdx.log)")
    parser.add_argument("--tail", "-t", type=int, help="Show last N entries")
    parser.add_argument("--level", "-l", help="Filter by log level")
    parser.add_argument("--module", "-m", help="Filter by module name")
    parser.add_argument("--search", "-s", help="Search in message text")
    
    args = parser.parse_args()
    
    if not Path(args.logfile).exists():
        print(f"Log file not found: {args.logfile}")
        return
    
    # Basic analysis
    analyze_log_file(args.logfile)
    
    # Additional filtering options
    if args.tail or args.level or args.module or args.search:
        print("\\nFiltered entries:")
        print("-" * 40)
        
        with open(args.logfile, 'r') as f:
            entries = []
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Apply filters
                    if args.level and entry['level'] != args.level.upper():
                        continue
                    if args.module and entry['module'] != args.module:
                        continue
                    if args.search and args.search.lower() not in entry['message'].lower():
                        continue
                    
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
            
            # Apply tail filter
            if args.tail:
                entries = entries[-args.tail:]
            
            # Display filtered entries
            for entry in entries:
                timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                print(f"{timestamp.strftime('%H:%M:%S')} [{entry['level']}] {entry['module']}: {entry['message']}")

if __name__ == "__main__":
    main()
