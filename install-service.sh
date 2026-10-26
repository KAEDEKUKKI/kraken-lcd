#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="kraken-lcd.service"
SERVICE_SRC="${SCRIPT_DIR}/${SERVICE_NAME}"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"

if [ ! -f "$SERVICE_SRC" ]; then
    echo "ERROR: Service file not found at $SERVICE_SRC"
    exit 1
fi

echo "Installing $SERVICE_NAME..."
sed "s|/home/kukki/kraken-lcd|${SCRIPT_DIR}|g" "$SERVICE_SRC" > "$SERVICE_DST"
chmod 644 "$SERVICE_DST"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "Service installed and started."
echo ""
echo "Useful commands:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "  sudo systemctl stop $SERVICE_NAME"
echo "  sudo systemctl disable $SERVICE_NAME"
