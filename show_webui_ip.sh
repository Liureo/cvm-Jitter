#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8765}"
MAX_WAIT_SECONDS="${2:-0}"

get_ip() {
  local ip_addr
  ip_addr="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [ -z "$ip_addr" ] || [ "$ip_addr" = "127.0.0.1" ]; then
    ip_addr="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
  fi
  if [ "$ip_addr" = "127.0.0.1" ]; then
    ip_addr=""
  fi
  printf '%s' "$ip_addr"
}

IP=""
attempt=0
while true; do
  IP="$(get_ip)"
  if [ -n "$IP" ]; then
    break
  fi
  attempt=$((attempt + 1))
  if [ "$MAX_WAIT_SECONDS" -gt 0 ] && [ "$attempt" -ge "$MAX_WAIT_SECONDS" ]; then
    break
  fi
  sleep 1
done

if [ -z "$IP" ]; then
  MESSAGE="Network is not connected yet.\nOpen this after WiFi connects:\nhttp://raspberrypi.local:$PORT\n\nOr run: hostname -I"
else
  MESSAGE="WebUI address:\nhttp://$IP:$PORT\n\nHostname address:\nhttp://$(hostname).local:$PORT"
fi

if command -v zenity >/dev/null 2>&1; then
  zenity --info --title="cvm Jitter" --text="$MESSAGE" --width=380
elif command -v xmessage >/dev/null 2>&1; then
  xmessage -center "$MESSAGE"
else
  printf '%b\n' "cvm Jitter $MESSAGE"
fi
