#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/media-monitor-bot"
ETC_DIR="/etc/media-monitor-bot"
DATA_DIR="/var/lib/media-monitor-bot"
LOG_DIR="/var/log/media-monitor-bot"
SERVICE_NAME="media-monitor-bot.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install_server.sh"
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

apt-get update
apt-get install -y python3 python3-venv python3-pip rsync ca-certificates

if ! id media-monitor >/dev/null 2>&1; then
  useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin media-monitor
fi

mkdir -p "${APP_DIR}" "${ETC_DIR}" "${DATA_DIR}" "${LOG_DIR}"

rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "config.json" \
  --exclude "data/*.sqlite3*" \
  --exclude "logs" \
  --exclude "reports" \
  "${SOURCE_DIR}/" "${APP_DIR}/"

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"

if [[ ! -f "${ETC_DIR}/config.json" ]]; then
  cp "${APP_DIR}/config.server.example.json" "${ETC_DIR}/config.json"
fi

if [[ ! -f "${ETC_DIR}/media-monitor-bot.env" ]]; then
  cp "${APP_DIR}/deploy/env.example" "${ETC_DIR}/media-monitor-bot.env"
  chmod 600 "${ETC_DIR}/media-monitor-bot.env"
fi

cp "${APP_DIR}/deploy/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"

chown -R media-monitor:media-monitor "${APP_DIR}" "${DATA_DIR}" "${LOG_DIR}"
chown root:media-monitor "${ETC_DIR}" "${ETC_DIR}/config.json" "${ETC_DIR}/media-monitor-bot.env"
chmod 750 "${ETC_DIR}"
chmod 640 "${ETC_DIR}/config.json" "${ETC_DIR}/media-monitor-bot.env"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo "Installed. Edit ${ETC_DIR}/media-monitor-bot.env, then run:"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  sudo systemctl status ${SERVICE_NAME}"
