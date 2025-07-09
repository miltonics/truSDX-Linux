#!/usr/bin/env python3
"""
Auto-update version and build date from git information.
This script updates src/main.py with current version and build date.
"""

import os
import subprocess
import sys
import re
from datetime import datetime

def get_git_version():
    """Get version from git describe."""
    try:
        # Get the current git describe output
        result = subprocess.run(['git', 'describe', '--tags', '--dirty', '--always'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback if git is not available or no tags
        return "unknown"

def get_build_date():
    """Get current build date."""
    return datetime.now().strftime("%Y-%m-%d")

def update_main_py():
    """Update VERSION and BUILD_DATE in src/main.py."""
    main_py_path = "src/main.py"
    
    if not os.path.exists(main_py_path):
        print(f"Error: {main_py_path} not found")
        return False
    
    # Get current version and build date
    version = get_git_version()
    build_date = get_build_date()
    
    # Read the current file
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Update VERSION line
    version_pattern = r'VERSION = ".*"'
    new_version_line = f'VERSION = "{version}"'
    content = re.sub(version_pattern, new_version_line, content)
    
    # Update BUILD_DATE line
    build_date_pattern = r'BUILD_DATE = ".*"'
    new_build_date_line = f'BUILD_DATE = "{build_date}"'
    content = re.sub(build_date_pattern, new_build_date_line, content)
    
    # Write the updated content
    with open(main_py_path, 'w') as f:
        f.write(content)
    
    print(f"Updated {main_py_path}:")
    print(f"  VERSION = \"{version}\"")
    print(f"  BUILD_DATE = \"{build_date}\"")
    
    return True

def update_changelog():
    """Update CHANGELOG.md with current version information."""
    changelog_path = "CHANGELOG.md"
    
    if not os.path.exists(changelog_path):
        print(f"Warning: {changelog_path} not found")
        return False
    
    version = get_git_version()
    build_date = get_build_date()
    
    # Read the current file
    with open(changelog_path, 'r') as f:
        content = f.read()
    
    # Check if [Unreleased] section exists and update it
    if "[Unreleased]" in content:
        # Add version info to unreleased section
        unreleased_pattern = r'(## \[Unreleased\])'
        replacement = f'\\1\n\n*Current build: {version} ({build_date})*'
        content = re.sub(unreleased_pattern, replacement, content, count=1)
        
        # Write the updated content
        with open(changelog_path, 'w') as f:
            f.write(content)
        
        print(f"Updated {changelog_path} with current build info")
    
    return True

def main():
    """Main function to update version information."""
    print("Auto-updating version and build date...")
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Update main.py
    if not update_main_py():
        sys.exit(1)
    
    # Update changelog
    update_changelog()
    
    print("Version update completed successfully!")

if __name__ == "__main__":
    main()
