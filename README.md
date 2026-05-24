# DSMS — 数据安全治理独立系统

**Data Secure Management System (DSMS)** 是一套面向企业内部的 Web 应用，用于支撑 **数据字段治理** 与 **分类分级** 相关工作。系统采用多项目（租户）隔离，在项目之下划分 **项目空间**，统一管理问卷、字段主表、填报任务、分类规则与审计记录。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5+-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

---

## 功能概览

| 模块 | 说明 |
|------|------|
| **身份与项目治理** | JWT 登录、平台超管 / 项目管理员 / 成员角色、Excel 批量导入用户、项目与成员管理 |
| **项目空间** | 多空间隔离下的问卷、字段配置与业务数据 |
| **动态表单** | 可配置字段类型与校验（`FieldConfigManagerTable` / `DynamicFieldInputs`） |
| **数据字段主表** | 字段目录维护、新增申请、业务功能选项申请与审核 |
| **填报与审批** | 字段填报任务、填报情况跟踪、负责人审批与导出 |
| **分类分级（Phase 2/3）** | 分类树、显式矩阵、分级规则、重算、人工覆写、安全要求求值、配置导入导出 |
| **门户 UI** | 深浅色主题、毛玻璃控制台壳、Apple 式轻量动效（见 UI 指南） |

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | Python 3.11+ · FastAPI · SQLModel · JWT (python-jose) · bcrypt |
| 前端 | Vue 3 · Vite · Element Plus · pnpm · Axios |
| 数据库 | SQLite（单机部署，WAL 模式） |
| API | REST · JSON；业务前缀 `/api/v1/dsms/`，认证 `/api/v1/auth/` |

---

## 仓库结构

```
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── api/      # 路由（auth、dsms、users 等）
│   │   ├── core/     # 配置、数据库、安全
│   │   ├── services/ # 业务服务层
│   │   └── models.py
│   ├── scripts/      # 数据迁移脚本
│   └── tests/        # pytest 集成测试
├── frontend/         # Vue 3 门户前端
│   └── src/
│       ├── views/    # 页面（登录、控制台、用户/项目/填报/字段等）
│       ├── components/
│       └── styles/portal-theme.css
├── docs/             # 实施规格、UI 指南、前后端依赖清单
├── ref/              # 旧库参考数据与迁移说明
└── .cursor/rules/    # Cursor Agent 开发约束
```

---

## 快速开始

### 环境要求

- **Python** 3.11 及以上
- **Node.js** 18+ 与 **pnpm**
- （可选）Git

### 1. 克隆仓库

```bash
git clone https://github.com/<你的用户名>/Data_Secure_Management_System.git
cd Data_Secure_Management_System
```

### 2. 后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

在 `backend/` 目录创建 `.env`（可选，未设置时使用 `app/core/config.py` 默认值）：

```env
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///./dsms.db
FIRST_SUPERUSER=admin
FIRST_SUPERUSER_PASSWORD=Admin123456
BACKEND_CORS_ORIGINS=["http://127.0.0.1:5173"]
```

启动后端（须在 `backend` 目录、且已激活虚拟环境）：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- 健康检查：<http://127.0.0.1:8000/healthz>
- OpenAPI 文档：<http://127.0.0.1:8000/docs>

首次启动会自动创建数据库表，并种子化超级管理员账号（见上方 `FIRST_SUPERUSER*`）。

### 3. 前端

```bash
cd frontend
pnpm install
pnpm run dev
```

浏览器访问 **<http://127.0.0.1:5173/>**。开发模式下 Vite 会将 `/api` 代理到 `http://127.0.0.1:8000`。

### 4. 默认测试账号

| 用户名 | 默认密码 | 角色 |
|--------|----------|------|
| `admin` | `Admin123456` | 超级管理员 |
| `security_fo` | `SecurityFo123456` | 数据安全 FO（测试） |
| `function_fo` | `FunctionFo123456` | 功能 FO（测试） |

> 生产环境请务必修改 `SECRET_KEY` 与所有默认密码。

---

## 前端页面

| 路由 | 页面 |
|------|------|
| `/login` | 登录 |
| `/` | 控制台首页 |
| `/user-management` | 用户管理 |
| `/project-management` | 项目管理（系统管理员） |
| `/submission-task` | 填报任务管理 |
| `/submission-task/:taskId` | 填报任务详情 |
| `/submission-status` | 填报情况 |
| `/field-lifecycle-meta` | 数据安全生命周期元字段 |
| `/field-catalog` | 数据字段主表 |

---

## 测试

在 `backend` 目录执行：

```bash
python -m pytest tests/ -v
```

集成测试使用独立 SQLite 文件（`tests/integration_session.sqlite`），与开发库 `dsms.db` 隔离。

前端构建验证：

```bash
cd frontend
pnpm run build
```

---

## 从旧库迁移

若需从旧版 `tool_id + project_space` 模型 SQLite 迁移数据，请参考：

- [`ref/README.md`](ref/README.md)
- [`docs/MIGRATION_REF_SQLITE.md`](docs/MIGRATION_REF_SQLITE.md)

```bash
cd backend
set PYTHONPATH=.
python scripts/migrate_from_ref_sqlite.py --ref ../ref/data_secure_from_rds.sqlite --dry-run
python scripts/migrate_from_ref_sqlite.py --ref ../ref/data_secure_from_rds.sqlite
```

**正式迁移前请备份目标数据库文件。**

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [`docs/DSMS_IMPLEMENTATION_SPEC.md`](docs/DSMS_IMPLEMENTATION_SPEC.md) | **唯一权威**产品与技术实施规格 |
| [`docs/DSMS_PORTAL_UI_GUIDE.md`](docs/DSMS_PORTAL_UI_GUIDE.md) | 门户 UI 风格与令牌约定 |
| [`docs/DSMS_FRONTEND_BACKEND_DEPS.md`](docs/DSMS_FRONTEND_BACKEND_DEPS.md) | 前端页面对后端依赖规范 |
| [`docs/frontend-backend-deps/README.md`](docs/frontend-backend-deps/README.md) | 各页面依赖清单索引 |
| [`docs/PHASE23_E2E.md`](docs/PHASE23_E2E.md) | Phase 2/3 分类分级端到端演示 |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | 架构与实现决策记录 |

---

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `SECRET_KEY` | JWT 签名密钥 | `change-me-in-production` |
| `ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 访问令牌有效期（分钟） | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 刷新令牌有效期（天） | `7` |
| `FIRST_SUPERUSER` | 首次初始化超管用户名 | `admin` |
| `FIRST_SUPERUSER_PASSWORD` | 超管初始密码 | `Admin123456` |
| `DATABASE_URL` | SQLite 连接串 | `sqlite:///./dsms.db` |
| `BACKEND_CORS_ORIGINS` | 允许的前端源（JSON 数组） | `["http://127.0.0.1:5173"]` |

完整列表见 [`docs/DSMS_IMPLEMENTATION_SPEC.md`](docs/DSMS_IMPLEMENTATION_SPEC.md) 第 2 节。

---

## 开发约定

- 业务 API 统一前缀 **`/api/v1/dsms/`**，认证 **`/api/v1/auth/`**
- 列表接口：`skip` / `limit` 请求，`total` / `items` 响应（默认 `limit=20`，最大 `500`）
- 面向用户的错误信息使用 **简体中文**
- 业务审计 `behavior_key` 须与规格附录 A **逐字一致**
- 多项目数据须携带 **`tenant_id`** 并与所属空间一致

---

## 许可证

本项目尚未指定开源许可证。如需对外发布或二次分发，请先补充 `LICENSE` 文件并确认合规要求。

---

## 贡献

1. Fork 本仓库并创建特性分支
2. 遵循 [`docs/DSMS_IMPLEMENTATION_SPEC.md`](docs/DSMS_IMPLEMENTATION_SPEC.md) 中的约定
3. 提交前运行 `pnpm run build`（前端）与 `pytest`（后端）
4. 发起 Pull Request 并说明变更范围与验证步骤
