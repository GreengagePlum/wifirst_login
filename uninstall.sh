#!/usr/bin/env bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this uninstaller as root (e.g., sudo ./uninstall.sh)"
    exit 1
fi

PY_SCRIPT="login.py"
ENV_FILE="/etc/wifirst.env"
SERVICE_FILE="/etc/systemd/system/wifirst-login.service"
TIMER_FILE="/etc/systemd/system/wifirst-login.timer"

echo "Uninstalling Wifirst Auto-Login Agent..."

# 1. Stop and disable systemd units
echo "Stopping and disabling timer and service..."
# 2>/dev/null suppresses errors if the service is already stopped/deleted
systemctl disable --now wifirst-login.timer 2>/dev/null
systemctl stop wifirst-login.service 2>/dev/null

# 2. Remove files
echo "Removing system files..."
rm -f "$TIMER_FILE"
rm -f "$SERVICE_FILE"
rm -f /usr/local/bin/$PY_SCRIPT

# 3. Handle credentials
if [ -f "$ENV_FILE" ]; then
    read -p "Do you want to delete your saved credentials in $ENV_FILE? (y/N) " DEL_ENV
    if [[ "$DEL_ENV" =~ ^[Yy]$ ]]; then
        rm -f "$ENV_FILE"
        echo " - Credentials file removed."
    else
        echo " - Credentials file retained."
    fi
fi

# 4. Reload systemd to clear deleted units from memory
systemctl daemon-reload

echo "Uninstallation complete."
