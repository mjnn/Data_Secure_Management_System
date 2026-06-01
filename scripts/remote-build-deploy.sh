#!/usr/bin/env bash
set -euo pipefail
REPO_DIR=/srv/apps/dsms-src
IMAGE=crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/data_secure_management_system:v20260527-01
REMOTE_DIR=/srv/apps/dsms
HOST_PORT=8002

if [[ -f "${REPO_DIR}/Dockerfile" ]]; then
  cd "${REPO_DIR}"
elif [[ -d "${REPO_DIR}/.git" ]]; then
  cd "${REPO_DIR}"
  git fetch origin
  git reset --hard origin/main
else
  rm -rf "${REPO_DIR}"
  git clone https://github.com/mjnn/Data_Secure_Management_System.git "${REPO_DIR}"
  cd "${REPO_DIR}"
fi
if [[ -d "${REPO_DIR}/.git" ]]; then
  git -C "${REPO_DIR}" log -1 --oneline
else
  echo "Using synced source at ${REPO_DIR}"
fi

docker build -f Dockerfile.runtime -t "${IMAGE}" .
docker push "${IMAGE}"

mkdir -p "${REMOTE_DIR}/data"
cp deploy/compose.yaml "${REMOTE_DIR}/compose.yaml"
cp deploy/nginx-dsms-locations.conf /tmp/dsms-locations.conf

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
DSMS_ENVIRONMENT=production
DSMS_SEED_TEST_USERS=false
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_PURGE_INTERVAL_SECONDS=3600
FIRST_SUPERUSER=admin
FIRST_SUPERUSER_PASSWORD=${ADMIN_PW}
TEST_SECURITY_FO_PASSWORD=${SEC_FO_PW}
TEST_FUNCTION_FO_PASSWORD=${FN_FO_PW}
BACKEND_CORS_ORIGINS=["http://47.116.180.173","http://127.0.0.1:${HOST_PORT}"]
ENVEOF
  echo "Created .env.runtime"
else
  sed -i "s|^IMAGE=.*|IMAGE=${IMAGE}|" .env.runtime
fi

docker-compose -p dsms --env-file .env.runtime -f compose.yaml pull
docker-compose -p dsms --env-file .env.runtime -f compose.yaml up -d --remove-orphans
docker-compose -p dsms -f compose.yaml ps

install -m 644 /tmp/dsms-locations.conf /etc/nginx/snippets/dsms-locations.conf
if ! grep -q 'dsms-locations.conf' /etc/nginx/sites-enabled/default; then
  sed -i '/ecs-service-manage-generated-locations.conf/i\    include /etc/nginx/snippets/dsms-locations.conf;' /etc/nginx/sites-enabled/default
fi
nginx -t
systemctl reload nginx

curl -fsS "http://127.0.0.1:${HOST_PORT}/healthz"
curl -fsS "http://127.0.0.1/tools/dsms/healthz"
echo "OK: http://47.116.180.173/tools/dsms/"
