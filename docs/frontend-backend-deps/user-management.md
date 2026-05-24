# 用户管理 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/user-management`，`name`: `dashboard-user-management`（`frontend/src/router.js`）
- **主要组件**：`frontend/src/views/UserManagementPage.vue`

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — 用于 `effectivePlatformRole`、功能 FO 无权重定向等。
- **Mock / 仅前端**：
  - 用户表格数据为组件内 **SEED**，未调用 `GET /api/v1/dsms/users`。
  - 所有写操作（Excel、批量停用、加入/移出项目、平台角色、项目创建权名单、升为项目管理员、功能 FO 绑定）当前为 **`ElMessage` 模拟「正在开发中」** 或仅前端校验，**未**调用后端。
- **角色与拦截**（与 `usePortalMenuVisibility` + 页内逻辑一致）：
  - **系统管理员（含超管）**：全部分组与操作入口。
  - **数据安全 FO**：仅列表 + 筛选 +「项目角色」只读（无「设为项目管理员」）+「负责功能」对 `function_fo` 行；无多选列、无批量与 Excel、无创建权折叠区。
  - **功能 FO**：侧栏不可达；直链进入会重定向首页。

## 3. 待对接 API（按能力块）

### 3.1 用户目录与筛选

| 前端能力 | HTTP | 路径 | Query / Body 要点 | 响应字段要点 | 权限（规格） | behavior_key |
|----------|------|------|-------------------|--------------|--------------|--------------|
| 列表与筛选 | GET | `/api/v1/dsms/users` | `skip`,`limit`,`q`,`is_active`,`membership_preview_tenant_id`,`only_unassigned_to_tenant` | `total`,`items`；项内白名单字段见 §6.2 | `super_admin` 或任一项为 `tenant_admin` | — |

### 3.2 批量创建用户

| 前端能力 | HTTP | 路径 | Query / Body 要点 | 响应字段要点 | 权限 | behavior_key |
|----------|------|------|-------------------|--------------|------|----------------|
| Excel 导入 | POST | `/api/v1/dsms/platform/users/import-excel` | `multipart/form-data`，字段名 `file` | `total_rows`,`created_count`,`skipped_count`,… | `super_admin` | `dsms-platform-users-import-excel` |
| 下载模板 | GET | `/api/v1/dsms/platform/users/import-excel/template` | — | 文件流 | `super_admin` | — |

### 3.3 批量停用账号

| 前端能力 | HTTP | 路径 | 说明 |
|----------|------|------|------|
| 批量停用 | **待规格/实现明确** | 可能为 `PATCH` 批量或逐条更新 `is_active` | 规格 §6 未单列时，在 OpenAPI/README 定稿后补全 |

### 3.4 项目成员

| 前端能力 | HTTP | 路径 | Body 要点 | 权限 | behavior_key |
|----------|------|------|-----------|------|----------------|
| 批量加入 | POST | `/api/v1/dsms/tenants/{tenant_id}/members/batch` | `user_ids`, `role` 默认 `tenant_member` | `tenant_admin` 同项目或 `super_admin` | `dsms-tenant-members-batch-add` |
| 批量移除 | POST | `/api/v1/dsms/tenants/{tenant_id}/members/batch-remove` | `user_ids` 等（以 OpenAPI 为准） | 同上 | `dsms-tenant-members-batch-remove` |
| 升为项目管理员 | PUT | `/api/v1/dsms/tenants/{tenant_id}/members/{user_id}/role` | `tenant_admin` / `tenant_member` | 策略见规格 §3.3 | `dsms-tenant-member-role-promote` |

### 3.5 平台与项目创建权

| 前端能力 | HTTP | 路径 | 说明 | 权限 | behavior_key |
|----------|------|------|------|------|----------------|
| 项目创建权名单 | GET | `/api/v1/dsms/platform/tenant-creators` | 读当前名单 | `super_admin` | — |
| 全量更新名单 | PUT | `/api/v1/dsms/platform/tenant-creators` | `user_ids` 全量替换 | `super_admin` | `dsms-platform-tenant-creators-update` |

### 3.6 平台角色（门户 `platform_role`）

| 前端能力 | HTTP | 说明 |
|----------|------|------|
| 批量/单用户设置 `platform_role` | **待实现** | 需在规格或独立 OpenAPI 中定义后补表 |

### 3.7 功能 FO 负责功能绑定

| 前端能力 | HTTP | 说明 |
|----------|------|------|
| 列表可选业务功能、保存绑定 | **待规格** | 与 `{tenant_id}/{space_id}` 下业务功能选项等接口对齐后补表 |

## 4. 与规格的差异 / 缺口

- 前端 **项目** 文案对应规格中 **`tenant`** 实体；路径仍为 `/tenants/...`。
- **批量停用**、**平台角色写入**、**功能 FO 绑定** 需后端与规格定稿后，在本清单补全并改页面为真实请求。

## 5. 联调检查清单

- [ ] `GET /users` 分页与筛选与表格列一致
- [ ] `members/batch` 跳过项中文 `reason` 展示（若 UI 保留跳过表）
- [ ] 仅 `super_admin` 可调用的按钮在后端再次校验
- [ ] 中文错误 `detail`
