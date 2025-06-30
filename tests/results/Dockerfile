FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    portaudio19-dev \
    pulseaudio \
    pulseaudio-utils \
    socat \
    build-essential \
    pkg-config \
    cmake \
    git \
    curl \
    wget \
    libusb-1.0-0-dev \
    libfftw3-dev \
    libtool \
    autoconf \
    automake \
    texinfo \
    dbus-x11 \
    alsa-utils \
    sox \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install pyaudio pyserial pytest numpy

# Create test user (non-root)
RUN useradd -m -s /bin/bash testuser && \
    usermod -a -G audio,dialout testuser

# Set up PulseAudio for headless operation
RUN mkdir -p /home/testuser/.config/pulse
COPY pulse-config /home/testuser/.config/pulse/client.conf
RUN echo "autospawn = no" >> /home/testuser/.config/pulse/client.conf && \
    echo "daemon-binary = /bin/true" >> /home/testuser/.config/pulse/client.conf && \
    chown -R testuser:testuser /home/testuser/.config

# Create working directory
WORKDIR /app
RUN chown testuser:testuser /app

USER testuser
