#!/bin/bash
# Jobber — Install Dependencies
# Run this script to install Docker, Docker Compose, and optionally
# the NVIDIA Container Toolkit on a fresh Ubuntu/Debian system.
#
# Usage: sudo ./install-deps.sh [--with-gpu]
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

WITH_GPU=false
for arg in "$@"; do
    case "$arg" in
        --with-gpu) WITH_GPU=true ;;
        -h|--help)
            echo "Usage: sudo $0 [--with-gpu]"
            echo ""
            echo "Installs Docker Engine, Docker Compose plugin, and optionally"
            echo "the NVIDIA Container Toolkit for GPU-accelerated containers."
            exit 0
            ;;
    esac
done

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    error "This script must be run as root. Use: sudo $0"
    exit 1
fi

# Detect the real user (when run via sudo)
REAL_USER="${SUDO_USER:-$USER}"

echo ""
echo "=========================================="
echo "  Jobber — Dependency Installer"
echo "=========================================="
echo ""

# ── Docker Engine ────────────────────────────
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
    info "Docker Engine already installed (v${DOCKER_VER})"
else
    info "Installing Docker Engine..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    info "Docker Engine installed"
fi

# ── Docker Compose ───────────────────────────
if docker compose version &>/dev/null; then
    COMPOSE_VER=$(docker compose version --short 2>/dev/null || echo "unknown")
    info "Docker Compose already installed (v${COMPOSE_VER})"
else
    info "Installing Docker Compose plugin..."
    apt-get update -qq
    apt-get install -y docker-compose-plugin
    info "Docker Compose plugin installed"
fi

# ── Docker group ─────────────────────────────
if [ "$REAL_USER" != "root" ]; then
    if groups "$REAL_USER" | grep -q docker; then
        info "User '${REAL_USER}' is already in the docker group"
    else
        info "Adding user '${REAL_USER}' to the docker group..."
        usermod -aG docker "$REAL_USER"
        warn "You will need to log out and back in (or run 'newgrp docker') for group changes to take effect"
    fi
fi

# ── NVIDIA Container Toolkit (optional) ──────
if [ "$WITH_GPU" = true ]; then
    if command -v nvidia-smi &>/dev/null; then
        info "NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"

        if command -v nvidia-container-cli &>/dev/null; then
            info "NVIDIA Container Toolkit already installed"
        else
            info "Installing NVIDIA Container Toolkit..."
            # Add NVIDIA apt repo
            curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
                | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
            curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
                | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
                | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
            apt-get update -qq
            apt-get install -y nvidia-container-toolkit
            nvidia-ctk runtime configure --runtime=docker
            systemctl restart docker
            info "NVIDIA Container Toolkit installed and configured"
        fi
    else
        warn "No NVIDIA GPU detected (nvidia-smi not found). Skipping GPU toolkit."
    fi
else
    if command -v nvidia-smi &>/dev/null; then
        warn "NVIDIA GPU detected but --with-gpu not specified. Run with --with-gpu to install container toolkit."
    fi
fi

echo ""
info "All dependencies installed. You can now run:"
echo ""
echo "  ./jobber-setup install"
echo ""
