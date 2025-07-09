# truSDX-AI Driver Documentation

Welcome to the comprehensive documentation for the truSDX-AI Driver project. This directory contains all technical documentation, guides, and project information.

## Documentation Structure

### Core Documentation
- **[Installation Guide](installation.md)** - Complete setup instructions for Linux systems
- **[User Guide](user-guide.md)** - How to use the driver with JS8Call and WSJT-X
- **[Configuration Reference](configuration.md)** - Detailed configuration options
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

### Technical Documentation
- **[API Reference](api-reference.md)** - Driver API and command reference
- **[Architecture Overview](architecture.md)** - System design and component interaction
- **[Development Guide](development.md)** - Contributing and development setup
- **[Testing Guide](testing.md)** - Testing procedures and validation

### Project Information
- **[Release Notes](../CHANGELOG.md)** - Version history and changes
- **[Contributing Guidelines](contributing.md)** - How to contribute to the project
- **[License Information](license.md)** - Project licensing details

## Quick Start

1. **Installation**: Follow the [Installation Guide](installation.md)
2. **Configuration**: Set up your system using the [Configuration Reference](configuration.md)
3. **Usage**: Learn basic operation from the [User Guide](user-guide.md)
4. **Troubleshooting**: Resolve issues with the [Troubleshooting Guide](troubleshooting.md)

## Project Overview

The truSDX-AI Driver is a Python-based CAT interface that enables seamless integration between the TruSDX QRP transceiver and digital mode software like JS8Call and WSJT-X on Linux systems.

### Key Features
- **Automatic Frequency Detection**: Reads current radio frequency at startup
- **TX/RX Control**: Handles transmission switching for digital modes
- **VU Meter Support**: Visual transmission feedback during operation
- **CAT Command Forwarding**: Transparent command passing between software and radio
- **Robust Error Handling**: Multiple retry attempts with comprehensive debugging
- **Auto-detection**: Automatically finds TruSDX USB device

### Hardware Compatibility
- TruSDX QRP Transceiver
- Linux systems (Ubuntu, Mint, Debian)
- JS8Call v2.2+
- WSJT-X integration

## Getting Help

If you encounter issues or need assistance:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the [FAQ](faq.md)
3. Search existing [GitHub Issues](https://github.com/your-username/trusdx-ai/issues)
4. Create a new issue with detailed information

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](contributing.md) for details on:
- Code style and standards
- Development workflow
- Testing requirements
- Documentation updates

## Version Information

- **Current Version**: 1.2.0-AI-MONITORING-RECONNECT
- **Last Updated**: 2025-01-27
- **Compatibility**: Python 3.6+, Linux systems

---

*This documentation is maintained as part of the truSDX-AI Driver project. For the latest updates, see the [project repository](https://github.com/your-username/trusdx-ai).*
