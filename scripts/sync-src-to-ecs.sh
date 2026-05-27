#!/usr/bin/env bash
# 将源码（含 frontend/dist）打包上传到 ECS，并执行远程构建部署（Dockerfile.runtime）
# 用法：在仓库根目录执行 bash scripts/sync-src-to-ecs.sh
# 前置：本地已 VITE_APP_BASE=/tools/dsms/ pnpm run build；ssh 别名 ecs-main 可用

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_HOST="${SSH_HOST:-ecs-main}"
REMOTE_SRC="/srv/apps/dsms-src"
TARBALL="/tmp/dsms-src.tar.gz"

cd "${ROOT}"
tar czf "${TARBALL}" \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='backend/.venv' \
  --exclude='backend/__pycache__' \
  --exclude='backend/**/__pycache__' \
  --exclude='*.pyc' \
  --exclude='backend/dsms.db' \
  --exclude='backend/dsms.db-*' \
  .

scp "${TARBALL}" "${SSH_HOST}:/tmp/dsms-src.tar.gz"
scp "${ROOT}/scripts/remote-build-deploy.sh" "${SSH_HOST}:/tmp/dsms-remote-deploy.sh"

ssh "${SSH_HOST}" bash -s <<'REMOTE'
set -euo pipefail
mkdir -p /srv/apps/dsms-src
rm -rf /srv/apps/dsms-src/*
tar xzf /tmp/dsms-src.tar.gz -C /srv/apps/dsms-src
chmod +x /tmp/dsms-remote-deploy.sh
bash /tmp/dsms-remote-deploy.sh
REMOTE

echo "==> Done. Open http://47.116.180.173/tools/dsms/"
