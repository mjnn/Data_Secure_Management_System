# 项目管理 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/project-management`，`name`: `dashboard-project-management`（`frontend/src/router.js`）
- **主要组件**：`frontend/src/views/ProjectManagementPage.vue`

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — 用于校验 **仅 `system_admin`（含超管映射）** 可进入；其余角色重定向首页。
- **Mock / sessionStorage**：
  - 项目列表存 **`sessionStorage`** 键 `dsms_portal_mock_projects_v1`；种子数据见源码 `SEED_PROJECTS`。
  - **新建 / 删除** 仅改本地数组并回写 `sessionStorage`，**未**调用 `POST/DELETE /tenants`。
  - 新建时勾选的 **字段/规则/人员/完成审核的填报数据** 复制仅写入行内 `copyMeta` 对象（布尔字段 `fields` / `rules` / `members` / `submissionAudited`），**未**调用任何克隆接口。
- **角色与拦截**：侧栏「项目管理」与顶栏下拉「项目管理」**仅** `menuVisibilityForRole` 中 `projectManagement: isAdmin`；**数据安全 FO、功能 FO** 不可见入口；直链进入页时非 `system_admin` 即重定向。

## 3. 待对接 API（按能力块）

### 3.1 项目列表与搜索

| 前端能力 | HTTP | 路径 | Query 要点 | 响应要点 | 权限（规格） | behavior_key |
|----------|------|------|------------|----------|--------------|----------------|
| 列表（当前用户可见项目） | GET | `/api/v1/dsms/tenants` 或等价列表接口 | `skip`,`limit`，搜索字段以 OpenAPI 为准 | `total`,`items` | 已登录且符合成员关系；具体以 OpenAPI 为准 | — |
| 搜索 | 同上 | 若后端支持 `q` / `name` 筛选则在 Query 中体现 | 与规格一致 | — | — |

（注：规格 §6.3 列成员与项目详情；**列表分页**须满足全局 `skip`/`limit` 约定。）

### 3.2 新建项目

| 前端能力 | HTTP | 路径 | Body 要点 | 权限 | behavior_key |
|----------|------|------|-----------|------|----------------|
| 创建项目 | POST | `/api/v1/dsms/tenants/` | `name`, `slug`（可选）等以模型为准 | `super_admin` 或 `tenant_creator` allowlist | 见附录 A 若已有「项目创建」类键 |
| 从已有项目克隆配置 | **待定义** | 可为同一 `POST` 扩展字段或子路径 `.../clone` | `source_tenant_id` + `copy_fields`,`copy_rules`,`copy_members`,`copy_submission_audited`（完成审核的填报数据）等布尔 | 与产品一致后补全 | 待定 |

### 3.3 删除 / 归档项目

| 前端能力 | HTTP | 路径 | 说明 |
|----------|------|------|------|
| 删除或归档 | **待规格明确** | 可能为 `DELETE` 或 `PATCH is_archived` | 与「至少一名 tenant_admin」等约束对齐后再接 |

## 4. 与规格的差异 / 缺口

- 前端 **「复制字段/规则/人员/完成审核的填报数据」** 为产品交互预留；**规格尚未定义** 克隆载荷与事务边界，需单独立项后更新本清单与 `DSMS_IMPLEMENTATION_SPEC.md`。
- 顶栏 **项目切换**（`DashboardPage` 内模拟列表）与本案列表 **数据源未统一**；对接后建议共用同一列表 API。

## 5. 联调检查清单

- [ ] 创建成功后刷新列表、`slug` 唯一性由后端返回 409 等时前端中文提示
- [ ] 无权限返回 403 与菜单可见性一致
- [ ] 分页 `skip`/`limit`
