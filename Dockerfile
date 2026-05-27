# DSMS 生产镜像：前端 build + FastAPI 单容器（静态资源 + API）
FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine AS frontend-build
WORKDIR /app/frontend
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
ARG VITE_APP_BASE=/tools/dsms/
ENV VITE_APP_BASE=${VITE_APP_BASE}
RUN pnpm run build

FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.12-slim AS runtime
WORKDIR /app/backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static \
    DATABASE_URL=sqlite:////app/data/dsms.db \
    DSMS_UPLOAD_ROOT=/app/data/uploads

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend-build /app/frontend/dist /app/static

RUN mkdir -p /app/data/uploads

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
