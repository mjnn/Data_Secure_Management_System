# Phase 1–3 联调自检清单（规格 §11）

自动化基线（每次发版前）：

- [ ] `cd backend && python -m pytest tests/ -q`
- [ ] `cd frontend && pnpm run build`

## Phase 1 — 平台与空间基础

| 项 | 操作 | 期望 |
|----|------|------|
| 登录 | `admin` / 种子密码登录 | 进入控制台，token 有效 |
| 项目列表 | 顶栏「项目切换」 | 列表来自 `GET /api/v1/dsms/tenants` |
| 切换项目 | 选择另一项目 | 空间配置重载，业务页数据随 tenant 变化 |
| 新建项目 | 项目管理 → 新建 → seeds | 出现 `default-space`，问卷/生命周期有种子 |
| 复制已审核填报 | 新建时勾选「完成审核的填报数据」 | `copy-approved-from` 返回 `copied_count` |
| 删除项目 | 项目管理 → 删除非 default 项目 | `DELETE /tenants/{id}` 成功；default 不可删 |
| 成员 | 用户管理 → 批量加入 | `members/batch` 成功 |
| 问卷 | 相关性问卷 CRUD | 题目保存后表达式页可见 |
| 分类树 | 层级 + 节点 | API 列表与编辑一致 |

## Phase 2 — 分类 / 密级 / 安全要求 / 审批 / 填报

| 项 | 操作 | 期望 |
|----|------|------|
| 字段目录 | 字段管理 CRUD | 与 `field-catalog` API 一致 |
| 分类矩阵/规则 | 配置页保存 | 审计 `behavior_key` 与附录 A 一致 |
| 分类结果 | 重算 / 手调 / 导出 | 列表与 CSV 可下载 |
| 密级与绑定 | 密级定义 + 字段绑定 | 只读/写与 API 一致 |
| 安全要求 | 规则 CRUD + 试算 | `evaluate` 返回要求项 |
| FO 绑定 | 填报任务页绑定卡片 | 申请 → 审批管理通过 |
| 填报任务 | 下发 / FO 工作流 / 提交 | PATCH 持久化；提交后 `submission_fill_review` |
| 审批 | 审批管理通过/驳回 | 中文 `detail`；待办数红点更新 |

## Phase 3 — 治理导出 / 文档

| 项 | 操作 | 期望 |
|----|------|------|
| 配置导出导入 | 项目管理复制字段/规则 | `config/export` + `import` 计数合理 |
| 治理变更日志 | `governance/change-logs` | 写操作后有记录 |
| 文档资源 | 上传 / 下载 / 模块模板 | 租户级文档 API 可用 |

## 已知缺口（产品待办）

- 服务端持久化「当前工作项目」偏好（可选）
