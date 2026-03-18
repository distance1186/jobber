#!/bin/bash
# Build a Debian package for Jobber.
# Usage: ./packaging/build-deb.sh <version> <path-to-linux-binary>
# Example: ./packaging/build-deb.sh 0.1.0 dist/linux/jobber-setup
set -euo pipefail

VERSION="${1:?Usage: build-deb.sh <version> <binary-path>}"
BINARY="${2:?Usage: build-deb.sh <version> <binary-path>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PKG_NAME="jobber"
PKG_DIR="${REPO_ROOT}/packaging/build/${PKG_NAME}_${VERSION}_amd64"

echo "==> Building ${PKG_NAME}_${VERSION}_amd64.deb"

# Clean
rm -rf "${PKG_DIR}"

# Create directory structure
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/usr/local/bin"
mkdir -p "${PKG_DIR}/opt/jobber/db"
mkdir -p "${PKG_DIR}/opt/jobber/cron"
mkdir -p "${PKG_DIR}/opt/jobber/agent"

# Copy control files
sed "s/^Version: .*/Version: ${VERSION}/" "${REPO_ROOT}/packaging/debian/control" > "${PKG_DIR}/DEBIAN/control"
cp "${REPO_ROOT}/packaging/debian/postinst" "${PKG_DIR}/DEBIAN/postinst"
chmod 0755 "${PKG_DIR}/DEBIAN/postinst"

# Install binary
cp "${BINARY}" "${PKG_DIR}/usr/local/bin/jobber-setup"
chmod 0755 "${PKG_DIR}/usr/local/bin/jobber-setup"

# Install project files
cp "${REPO_ROOT}/docker-compose.yml" "${PKG_DIR}/opt/jobber/"
cp "${REPO_ROOT}/db/init.sql"        "${PKG_DIR}/opt/jobber/db/"
cp "${REPO_ROOT}/cron/crontab"       "${PKG_DIR}/opt/jobber/cron/"
cp "${REPO_ROOT}/.env.example"       "${PKG_DIR}/opt/jobber/"
cp -r "${REPO_ROOT}/agent/"          "${PKG_DIR}/opt/jobber/agent/"

# Remove Python caches and test files from packaged agent
find "${PKG_DIR}/opt/jobber/agent" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
rm -rf "${PKG_DIR}/opt/jobber/agent/tests"

# Calculate installed size (in KB)
SIZE_KB=$(du -sk "${PKG_DIR}" | cut -f1)
echo "Installed-Size: ${SIZE_KB}" >> "${PKG_DIR}/DEBIAN/control"

# Build the package
dpkg-deb --build --root-owner-group "${PKG_DIR}"

echo "==> Built: ${PKG_DIR}.deb"
