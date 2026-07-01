#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="${HOME:-$(getent passwd "$USER" | cut -d: -f6)}"
AUTOSTART_DIR="$USER_HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/cvm-jitter-ip.desktop"

chmod +x "$APP_DIR/show_webui_ip.sh"
mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=cvm Jitter WebUI Address
Exec=$APP_DIR/show_webui_ip.sh 8765
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo
echo "Installed desktop IP display autostart:"
echo "  $DESKTOP_FILE"
echo
echo "If no popup appears after login, install zenity:"
echo "  sudo apt install -y zenity"
