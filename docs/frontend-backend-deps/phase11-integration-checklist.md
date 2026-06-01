# Phase 1–3 联调自检清单（规格 §11）

自动化基线（每次发版前）：

- [x] `cd backend && python -m pytest tests/ -q` — **2026-05-28：15 passed**
- [x] `cd frontend && pnpm run build` — **2026-05-28：成功**（含安全要求试算改动后 rebuild）

**API 代跑**：`cd backend && python scripts/run_phase11_checklist.py` — **2026-05-28：26/26 通过**

**UI 依赖 API 代跑**（需先启动后端 `uvicorn`）：`cd backend && python scripts/run_phase11_ui_smoke.py` — **2026-05-28：9/9 通过**（对 `dsms.db` 开发库）

## Phase 1 — 平台与空间基础

| 项 | 操作 | 期望 | 代跑结果 |
|----|------|------|----------|
| 登录 | `admin` / 种子密码登录 | 进入控制台，token 有效 | [x] API |
| 项目列表 | 顶栏「项目切换」 | 列表来自 `GET /api/v1/dsms/tenants` | [x] API + UI 冒烟 |
| 切换项目 | 选择另一项目 | 空间配置重载，业务页数据随 tenant 变化 | [x] API + UI 冒烟 |
| 新建项目 | 项目管理 → 新建 → seeds | 出现 `default-space`，问卷/生命周期有种子 | [x] API |
| 复制已审核填报 | 新建时勾选「完成审核的填报数据」 | `copy-approved-from` 返回 `copied_count` | [x] API |
| 删除项目 | 项目管理 → 删除非 default 项目 | `DELETE /tenants/{id}` 成功；default 不可删 | [x] API |
| 成员 | 用户管理 → 批量加入 | `members/batch` 成功 | [x] API |
| 问卷 | 相关性问卷 CRUD | 题目保存后表达式页可见 | [x] API |
| 分类树 | 层级 + 节点 | API 列表与编辑一致 | [x] API |

## Phase 2 — 分类 / 密级 / 安全要求 / 审批 / 填报

| 项 | 操作 | 期望 | 代跑结果 |
|----|------|------|----------|
| 字段目录 | 字段管理 CRUD | 与 `field-catalog` API 一致 | [x] API |
| 分类矩阵/规则 | 配置页保存 | 审计 `behavior_key` 与附录 A 一致 | [x] API |
| 分类结果 | 重算 / 手调 / 导出 | 列表与 CSV 可下载 | [x] API |
| 密级与绑定 | 密级定义 + 字段绑定 | 只读/写与 API 一致 | [x] API |
| 安全要求 | 规则 CRUD + 试算 | `evaluate` 返回要求项 | [x] API + **前端已接 evaluate** |
| FO 绑定 | 填报任务页绑定卡片 | 申请 → 审批管理通过 | [x] API |
| 填报任务 | 下发 / FO 工作流 / 提交 | PATCH 持久化；提交后 `submission_fill_review` | [x] API |
| 审批 | 审批管理通过/驳回 | 中文 `detail`；待办数红点更新 | [x] API + UI 冒烟 |

## Phase 3 — 治理导出 / 文档

| 项 | 操作 | 期望 | 代跑结果 |
|----|------|------|----------|
| 配置导出导入 | 项目管理复制字段/规则 | `config/export` + `import` 计数合理 | [x] API |
| 治理变更日志 | `governance/change-logs` | 写操作后有记录 | [x] API |
| 文档资源 | 上传 / 下载 / 模块模板 | 租户级文档 API 可用 | [x] API |

## 浏览器目视（约 5 分钟，开发服已起）

开发地址：**http://127.0.0.1:5173/**（后端 **http://127.0.0.1:8000**）

- [ ] **顶栏**：项目下拉 →「切换项目」对话框 → 选另一项目 → 顶栏名称变化，进入「数据字段」列表条数变化
- [ ] **填报情况** `/submission-status`：六张统计卡 + 饼/柱图随任务数据渲染（无任务时为空态正常）
- [ ] **控制台首页**：`security_fo` 登录时侧栏「审批管理」红点 = 待办数；`function_fo` 登录时「填报任务」红点（需已下发任务）
- [x] **安全要求** `/rule-security`：选字段试算 → 门户规则 + 后端 `evaluate` 合并展示（已实现）

## 已知缺口（产品待办）

- 服务端持久化「当前工作项目」偏好（可选）
- `seeds/import` 不种生命周期字段配置（与清单原文「生命周期有种子」表述不一致，以 API 为准）
