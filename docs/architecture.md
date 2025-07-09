# Architecture Overview

The truSDX-AI driver is composed of several key modules, each with its own responsibilities within the system. This document outlines the high-level architecture and interaction between these modules.

## Modules

### 1. audio_io.py

- **Functionality**: Manages audio input/output and processing.
- **Interfaces**: Provides methods to show available audio devices, create streams, and handle audio data.

### 2. cat_emulator.py

- **Functionality**: Emulates Kenwood TS-480 CAT commands and manages radio state.
- **Interfaces**: Includes methods for handling specific CAT commands.

### 3. connection_manager.py

- **Functionality**: Manages and monitors serial connections to the radio.
- **Interfaces**: Provides connection setup and reconnection logic.

### 4. ui.py

- **Functionality**: Manages the terminal-based user interface and control headers.
- **Interfaces**: Includes methods for displaying headers and other UI components.

### 5. logging_cfg.py

- **Functionality**: Provides logging support across the application with color-coded output.
- **Interfaces**: Methods for logging messages at different levels.

### 6. main.py

- **Functionality**: Serves as the entry point of the application.
- **Interfaces**: Initializes and coordinates other modules, handles command-line arguments.

## Data Structures

#### RadioState

- Represents the state of the radio, including frequency, mode, and other settings.

#### AppState

- Manages application state across multiple components.

## Configuration

The application uses global dictionaries for configuration. For persistence, JSON is recommended for user-editable settings, pointing to a configuration file path in the code.

## Execution Flow

The `main.py` acts as the orchestrator, initializing all components and ensuring they communicate effectively with each other through their defined interfaces. The application is executed by running `main.py`, which sets up threads and initiates communication with the radio device.
