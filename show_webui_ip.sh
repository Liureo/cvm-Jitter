#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8765}"

sleep 8
IP="$(hostname -I | awk '{print $1}')"
if [ -z "$IP" ]; then
  IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
fi
if [ -z "$IP" ]; then
  IP="127.0.0.1"
fi

URL="http://$IP:$PORT"

if command -v zenity >/dev/null 2>&1; then
  zenity --info --title="cvm Jitter" --text="WebUI address:\n$URL" --width=340
elif command -v xmessage >/dev/null 2>&1; then
  xmessage -center "cvm Jitter WebUI address: $URL"
else
  echo "cvm Jitter WebUI address: $URL"
fi
