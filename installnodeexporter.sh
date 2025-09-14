#!/usr/bin/env bash
# install-node-exporter.sh
# Installs Prometheus node_exporter on x86_64 Linux with systemd.

set -euo pipefail

#--- Config (you can pin a version by uncommenting the next line) -------------
# PINNED_VERSION="1.8.2"   # example; if set, we install this instead of "latest"
SERVICE_USER="nodeexp"
SERVICE_GROUP="$SERVICE_USER"
LISTEN_ADDR=":9100"

#--- Root check ----------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (e.g. sudo bash $0)"; exit 1
fi

#--- Arch check ----------------------------------------------------------------
arch="$(uname -m)"
case "$arch" in
  x86_64) PLATFORM="linux-amd64" ;;
  amd64)  PLATFORM="linux-amd64" ;;
  *)
    echo "Unsupported architecture: $arch (this script is for x86_64 only)"; exit 1;;
esac

#--- Create system user/group --------------------------------------------------
if ! getent group "$SERVICE_GROUP" >/dev/null; then
  groupadd -r "$SERVICE_GROUP"
fi
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd -r -s /usr/sbin/nologin -g "$SERVICE_GROUP" "$SERVICE_USER"
fi

#--- Download latest (or pinned) tarball --------------------------------------
workdir="$(mktemp -d)"; cd "$workdir"

if [[ -n "${PINNED_VERSION:-}" ]]; then
  TAG="v${PINNED_VERSION#v}"  # ensure leading v
  TAR_URL="https://github.com/prometheus/node_exporter/releases/download/${TAG}/node_exporter-${TAG#v}.${PLATFORM}.tar.gz"
  SUMS_URL="https://github.com/prometheus/node_exporter/releases/download/${TAG}/sha256sums.txt"
else
  # Grab URLs from GitHub API (latest)
  api="$(curl -fsSL https://api.github.com/repos/prometheus/node_exporter/releases/latest)"
  TAR_URL="$(printf '%s\n' "$api" | grep -Eo "https://[^\" ]*node_exporter-[0-9.]+\.${PLATFORM}\.tar\.gz" | head -n1)"
  SUMS_URL="$(printf '%s\n' "$api" | grep -Eo "https://[^\" ]*sha256sums.txt" | head -n1)"
fi

echo "Downloading: $TAR_URL"
curl -fsSL -o ne.tgz "$TAR_URL"

# Optional checksum verification
if command -v sha256sum >/dev/null 2>&1 && [[ -n "${SUMS_URL:-}" ]]; then
  echo "Verifying checksum..."
  curl -fsSL -o sums.txt "$SUMS_URL"
  # Keep only matching line for our tarball
  fname="$(basename "$TAR_URL")"
  grep "  $fname\$" sums.txt > sums.filtered || { echo "Checksum entry not found for $fname"; exit 1; }
  sha256sum -c sums.filtered
fi

#--- Install binary ------------------------------------------------------------
tar -xzf ne.tgz
binpath="$(echo node_exporter-*/node_exporter)"
install -m 0755 -o root -g root "$binpath" /usr/local/bin/node_exporter

#--- systemd unit --------------------------------------------------------------
cat >/etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Prometheus Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=${LISTEN_ADDR}
Restart=on-failure
AmbientCapabilities=
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true
ProtectControlGroups=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectKernelLogs=true

[Install]
WantedBy=multi-user.target
EOF

#--- Enable & start ------------------------------------------------------------
systemctl daemon-reload
systemctl enable --now node_exporter

#--- Show status & a quick check ----------------------------------------------
systemctl --no-pager --full status node_exporter || true
echo
echo "Try:   curl -s http://localhost${LISTEN_ADDR}/metrics | head"
echo "Done."
