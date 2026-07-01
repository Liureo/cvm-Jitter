#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-headless.txt

echo
echo "Installed headless dependencies in $APP_DIR/.venv"
echo "Run manually with:"
echo "  $APP_DIR/.venv/bin/python $APP_DIR/main_headless.py"
echo
echo "For serial devices, add your user to dialout, then log out and back in:"
echo "  sudo usermod -aG dialout $USER"
echo
echo "Optional boot helpers:"
echo "  ./install_autostart.sh      # start WebUI service on boot"
echo "  ./install_ip_display.sh     # show WebUI IP after desktop login"
