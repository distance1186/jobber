#!/bin/bash
# Build a .tar.gz archive for Jobber (generic Linux).
# Usage: ./packaging/build-tarball.sh <version> <path-to-linux-binary>
# Example: ./packaging/build-tarball.sh 0.1.0 dist/linux/jobber-setup
set -euo pipefail

VERSION="${1:?Usage: build-tarball.sh <version> <binary-path>}"
BINARY="${2:?Usage: build-tarball.sh <version> <binary-path>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ARCHIVE_NAME="jobber-${VERSION}-linux-amd64"
STAGE_DIR="${REPO_ROOT}/packaging/build/${ARCHIVE_NAME}"

echo "==> Building ${ARCHIVE_NAME}.tar.gz"

# Clean
rm -rf "${STAGE_DIR}"

# Create staging directory
mkdir -p "${STAGE_DIR}/db"
mkdir -p "${STAGE_DIR}/cron"
mkdir -p "${STAGE_DIR}/agent"

# Binary
cp "${BINARY}" "${STAGE_DIR}/jobber-setup"
chmod 0755 "${STAGE_DIR}/jobber-setup"

# Project files
cp "${REPO_ROOT}/docker-compose.yml" "${STAGE_DIR}/"
cp "${REPO_ROOT}/db/init.sql"        "${STAGE_DIR}/db/"
cp "${REPO_ROOT}/cron/crontab"       "${STAGE_DIR}/cron/"
cp "${REPO_ROOT}/.env.example"       "${STAGE_DIR}/"
cp "${REPO_ROOT}/LICENSE"            "${STAGE_DIR}/"
cp "${REPO_ROOT}/README.md"          "${STAGE_DIR}/"
cp -r "${REPO_ROOT}/agent/"          "${STAGE_DIR}/agent/"

# Include the dependency install helper
cp "${REPO_ROOT}/scripts/install-deps.sh" "${STAGE_DIR}/"
chmod 0755 "${STAGE_DIR}/install-deps.sh"

# Clean up Python caches and tests
find "${STAGE_DIR}/agent" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
rm -rf "${STAGE_DIR}/agent/tests"

# Create tarball
tar -czf "${REPO_ROOT}/packaging/build/${ARCHIVE_NAME}.tar.gz" \
    -C "${REPO_ROOT}/packaging/build" \
    "${ARCHIVE_NAME}"

echo "==> Built: ${REPO_ROOT}/packaging/build/${ARCHIVE_NAME}.tar.gz"
