#!/usr/bin/env bash
# 将 DSMS Nginx 片段安装到 ECS 并重载
# 用法：bash scripts/install-nginx-dsms.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_HOST="${SSH_HOST:-ecs-main}"
SNIPPET="/etc/nginx/snippets/dsms-locations.conf"
DEFAULT="/etc/nginx/sites-enabled/default"
MARKER="dsms-locations.conf"

scp "${ROOT}/deploy/nginx-dsms-locations.conf" "${SSH_HOST}:/tmp/dsms-locations.conf"

ssh "${SSH_HOST}" bash -s <<REMOTE
set -euo pipefail
install -m 644 /tmp/dsms-locations.conf "${SNIPPET}"
if ! grep -q '${MARKER}' "${DEFAULT}"; then
  sed -i '/ecs-service-manage-generated-locations.conf/i\    include /etc/nginx/snippets/dsms-locations.conf;' "${DEFAULT}"
  echo "Added include to ${DEFAULT}"
fi
nginx -t
systemctl reload nginx
curl -fsS http://127.0.0.1/tools/dsms/healthz
echo ""
echo "OK: http://47.116.180.173/tools/dsms/"
REMOTE
