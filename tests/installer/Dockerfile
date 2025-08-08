# Use Ubuntu as base image for Linux testing
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install basic dependencies that would typically be present
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python3-openssl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for testing
RUN useradd -m -s /bin/bash testuser && \
    echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Switch to the test user
USER testuser
WORKDIR /home/testuser

# Copy the test script
COPY --chown=testuser:testuser test_installer.sh /home/testuser/
RUN chmod +x /home/testuser/test_installer.sh

# Set the entrypoint to run the test
ENTRYPOINT ["/home/testuser/test_installer.sh"]