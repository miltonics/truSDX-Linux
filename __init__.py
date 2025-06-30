#!/usr/bin/env python3
"""
truSDX-AI Driver Package

This module provides centralized version management and imports for the truSDX-AI project.
"""

# Import version information from the centralized version module
from .version import (
    __version__, __build_date__, __author__, __description__,
    VERSION, BUILD_DATE, AUTHOR, COMPATIBLE_PROGRAMS,
    get_version_string, get_full_version_info, get_banner_info
)

# Package metadata
__all__ = [
    '__version__', '__build_date__', '__author__', '__description__',
    'VERSION', 'BUILD_DATE', 'AUTHOR', 'COMPATIBLE_PROGRAMS',
    'get_version_string', 'get_full_version_info', 'get_banner_info'
]
