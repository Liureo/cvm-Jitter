#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
GROUP_NAME="$(id -gn "$USER_NAME")"
SERVICE_FILE="/etc/systemd/system/cvm-jitter.service"

if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
  echo "Missing $APP_DIR/.venv/bin/python"
  echo "Run ./install_raspberry_pi.sh first."
  exit 1
fi

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=cvm Jitter headless WebUI service
After=multi-user.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/main_headless.py --port 8765
Restart=on-failure
RestartSec=3
User=$USER_NAME
Group=$GROUP_NAME
SupplementaryGroups=dialout

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cvm-jitter.service
sudo systemctl restart cvm-jitter.service

echo
echo "Enabled cvm-jitter.service for boot."
echo "Current status:"
systemctl --no-pager --lines=8 status cvm-jitter.service || true
