#!/usr/bin/env bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this installer as root (e.g., sudo ./install.sh)"
    exit 1
fi

# Resolve the absolute path of the directory containing this script
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PY_SCRIPT="wifirst_login.py"
ENV_FILE="/etc/wifirst.env"
SERVICE_FILE="/etc/systemd/system/wifirst-login.service"
TIMER_FILE="/etc/systemd/system/wifirst-login.timer"

echo "Installing Wifirst Auto-Login Agent..."

# 1. Install the Python script
if [ ! -f "$SCRIPT_DIR/$PY_SCRIPT" ]; then
    echo "Error: $PY_SCRIPT not found in $SCRIPT_DIR."
    exit 1
fi

cp "$SCRIPT_DIR/$PY_SCRIPT" /usr/local/bin/
chmod +x /usr/local/bin/$PY_SCRIPT
echo " - Copied Python script to /usr/local/bin/"

# 2. Set up the Secure Environment File
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "Setting up credentials..."
    read -p "Enter your Wifirst Email: " WIFIRST_EMAIL
    # -s flag hides the password input from the terminal
    read -s -p "Enter your Wifirst Password: " WIFIRST_PASSWD
    echo ""

    cat <<EOF >"$ENV_FILE"
WIFIRST_EMAIL=$WIFIRST_EMAIL
WIFIRST_PASSWD=$WIFIRST_PASSWD
EOF
    # Lock down the file immediately
    chmod 600 "$ENV_FILE"
    chown root:root "$ENV_FILE"
    echo " - Created secure credentials file at $ENV_FILE"
else
    echo " - Credentials file $ENV_FILE already exists, skipping creation."
fi

# 3. Generate the Systemd Service File
cat <<EOF >"$SERVICE_FILE"
[Unit]
Description=Wifirst Captive Portal Auto-Login Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/python /usr/local/bin/$PY_SCRIPT
User=root
EOF
echo " - Generated service file at $SERVICE_FILE"

# 4. Generate the Systemd Timer File
cat <<EOF >"$TIMER_FILE"
[Unit]
Description=Run Wifirst Login Connectivity Check Periodically

[Timer]
OnBootSec=1min
OnUnitActiveSec=2min
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF
echo " - Generated timer file at $TIMER_FILE"

# 5. Enable and Start the Services
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling and starting the systemd timer..."
systemctl enable --now wifirst-login.timer

echo "Triggering an initial login check..."
systemctl start wifirst-login.service

echo ""
echo "Installation complete! The agent is now monitoring your connection in the background."
