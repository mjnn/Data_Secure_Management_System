#!/usr/bin/env bash
# DSMS → 阿里云 ACR + ECS docker compose 部署
# 用法：bash scripts/deploy-to-ecs.sh [tag]
# 示例：bash scripts/deploy-to-ecs.sh v20260527-01

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com"
NAMESPACE="mirror_ns"
REPO="data_secure_management_system"
TAG="${1:-v$(date +%Y%m%d-%H%M)}"
IMAGE="${REGISTRY}/${NAMESPACE}/${REPO}:${TAG}"
SSH_HOST="${SSH_HOST:-ecs-main}"
SERVICE="dsms"
REMOTE_DIR="/srv/apps/${SERVICE}"
HOST_PORT="${HOST_PORT:-8002}"

echo "==> Image: ${IMAGE}"
echo "==> ECS:   ${SSH_HOST}:${REMOTE_DIR}"

docker build -t "${IMAGE}" "${ROOT}"
docker push "${IMAGE}"

ssh "${SSH_HOST}" "mkdir -p ${REMOTE_DIR}/data"
scp "${ROOT}/deploy/compose.yaml" "${SSH_HOST}:${REMOTE_DIR}/compose.yaml"
scp "${ROOT}/deploy/.env.runtime.example" "${SSH_HOST}:${REMOTE_DIR}/.env.runtime.example"
scp "${ROOT}/deploy/nginx-dsms-locations.conf" "${SSH_HOST}:/tmp/dsms-locations.conf"

ssh "${SSH_HOST}" "IMAGE='${IMAGE}' HOST_PORT='${HOST_PORT}' SERVICE='${SERVICE}' REMOTE_DIR='${REMOTE_DIR}' bash -s" <<'REMOTE'
set -euo pipefail
cd "${REMOTE_DIR}"

if [[ ! -f .env.runtime ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
  ADMIN_PW="$(openssl rand -hex 8)"
  SEC_FO_PW="$(openssl rand -hex 8)"
  FN_FO_PW="$(openssl rand -hex 8)"
  cat > .env.runtime <<ENVEOF
SERVICE_NAME=dsms
IMAGE=${IMAGE}
HOST_PORT=${HOST_PORT}
CONTAINER_PORT=8000
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=7
FIRST_SUPERUSER=admin
FIRST_SUPERUSER_PASSWORD=${ADMIN_PW}
TEST_SECURITY_FO_PASSWORD=${SEC_FO_PW}
TEST_FUNCTION_FO_PASSWORD=${FN_FO_PW}
BACKEND_CORS_ORIGINS=["http://47.116.180.173","http://127.0.0.1:${HOST_PORT}"]
ENVEOF
  echo "Created .env.runtime with generated secrets on ECS."
else
  if grep -q '^IMAGE=' .env.runtime; then
    sed -i "s|^IMAGE=.*|IMAGE=${IMAGE}|" .env.runtime
  else
    echo "IMAGE=${IMAGE}" >> .env.runtime
  fi
fi

docker-compose -p "${SERVICE}" --env-file .env.runtime -f compose.yaml pull
docker-compose -p "${SERVICE}" --env-file .env.runtime -f compose.yaml up -d --remove-orphans
docker-compose -p "${SERVICE}" -f compose.yaml ps

install -m 644 /tmp/dsms-locations.conf /etc/nginx/snippets/dsms-locations.conf
if ! grep -q 'dsms-locations.conf' /etc/nginx/sites-enabled/default; then
  sed -i '/ecs-service-manage-generated-locations.conf/i\    include /etc/nginx/snippets/dsms-locations.conf;' /etc/nginx/sites-enabled/default
fi
nginx -t
systemctl reload nginx

curl -fsS "http://127.0.0.1:${HOST_PORT}/healthz"
curl -fsS "http://127.0.0.1/tools/dsms/healthz"
REMOTE

echo "==> Deployed: http://47.116.180.173/tools/dsms/"
