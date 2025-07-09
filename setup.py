#!/usr/bin/env python3
"""
Setup script for truSDX-AI Driver
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read the requirements file
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Read version from main.py
version = "1.2.0"
with open("src/main.py", "r", encoding="utf-8") as fh:
    for line in fh:
        if line.startswith("VERSION = "):
            version = line.split('"')[1]
            break

setup(
    name="trusdx-ai",
    version=version,
    author="SQ3SWF, PE1NNZ, AI-Enhanced",
    author_email="",
    description="AI-enhanced CAT interface driver for TruSDX QRP transceiver with JS8Call integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/milton-tanaka/trusdx-ai",
    packages=["trusdx_ai"],
    package_dir={"trusdx_ai": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Communications :: Ham Radio",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "trusdx-ai=trusdx_ai.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.cfg"],
    },
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/milton-tanaka/trusdx-ai/issues",
        "Source": "https://github.com/milton-tanaka/trusdx-ai",
        "Documentation": "https://github.com/milton-tanaka/trusdx-ai/blob/main/README.md",
    },
)
