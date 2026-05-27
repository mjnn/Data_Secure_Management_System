# 用户管理 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/user-management`，`name`: `dashboard-user-management`（`frontend/src/router.js`）
- **主要组件**：`frontend/src/views/UserManagementPage.vue`

## 2. 当前实现状态

- **已接真实 API**
  - `GET /api/v1/users/me` — 角色与页内拦截
  - `GET /api/v1/dsms/users` — 分页列表与筛选
  - `POST .../tenants/{id}/members/batch` — 批量加入项目
  - `POST .../tenants/{id}/members/batch-remove` — 批量移除
  - `PUT .../tenants/{id}/members/{user_id}/role` — 升为项目管理员
  - `GET/PUT /api/v1/dsms/platform/tenant-creators` — 项目创建权名单
  - `GET/POST /api/v1/dsms/platform/users/import-excel`（及 template）— Excel 导入
  - `POST /api/v1/dsms/platform/users/batch-deactivate` — 批量停用
  - `PUT /api/v1/dsms/platform/users/batch-platform-role` — 批量设置 `platform_role`
- **已接（管理员代绑）**
  - `GET/PUT .../fo-function-bindings/users/{user_id}` — 用户管理页「负责功能」抽屉
- **角色与拦截**
  - **系统管理员**：全部分组与写操作
  - **数据安全 FO**：列表 + 筛选 + 项目角色只读（须后端 `GET /users` 权限通过）
  - **功能 FO**：侧栏不可达

## 3. 待对接 API

（当前无阻塞项；FO 自助绑定变更仍走 `fo-function-binding-requests` + 审批。）

## 4. 与规格的差异 / 缺口

- `batch-deactivate`、`batch-platform-role` 为联调补充接口，behavior_key 分别为 `dsms-platform-users-batch-deactivate`、`dsms-platform-users-batch-platform-role`（规格附录可后续补录）。

## 5. 联调检查清单

- [ ] Excel 导入返回 `created_count` / `skipped_items`
- [ ] 批量停用不可停当前账号与超管
- [ ] 项目创建权 PUT 全量替换
- [ ] 中文错误 `detail`
