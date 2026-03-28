#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root"
  exit 1
fi

install -d /opt/kome
install -d /etc/kome
cp -r . /opt/kome/
python3 -m venv /opt/kome/.venv
/opt/kome/.venv/bin/pip install -e /opt/kome

if [[ ! -f /etc/kome/kome.env ]]; then
  cp /opt/kome/deploy/kome.env.example /etc/kome/kome.env
fi

cp /opt/kome/deploy/systemd/kome-assistant.service /etc/systemd/system/kome-assistant.service
systemctl daemon-reload
systemctl enable kome-assistant
systemctl restart kome-assistant

echo "Installed and started kome-assistant.service"
