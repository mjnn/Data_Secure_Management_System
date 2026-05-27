# 控制台壳（顶栏项目区）— 后端依赖清单

## 1. 前端入口

- **组件**：`frontend/src/views/DashboardPage.vue`（顶栏 `el-dropdown`、项目切换对话框等）
- **租户上下文**：`frontend/src/composables/usePortalTenantContext.js`
- **路由**：壳层路由为 `/`，子路由由 `router-view` 承载。

## 2. 当前实现状态

- **已接真实 API**
  - `GET /api/v1/users/me` — 顶栏用户展示、`menuVisibilityForRole`
  - `GET /api/v1/dsms/tenants` — 项目切换列表（与项目管理页同源）
  - 当前选中项目：`localStorage` 键 `dsms_portal_selected_tenant_v1`；切换时 `switchTenant` 重拉空间、`bootstrapSpaceConfig`
- **已移除**：`portalProjectsMock.js` 与 `sessionStorage` 项目种子

## 3. 待对接 / 缺口

- 若产品要求服务端持久化「当前工作项目」，需规格定义偏好接口；当前为前端 localStorage

## 4. 联调检查清单

- [ ] 切换项目后，依赖 `tenant_id` / `space_id` 的子页面请求均正确
- [ ] 新建项目后顶栏列表刷新（`refreshTenants`）
- [ ] 下拉与对话框在无数据、403 时的降级提示
