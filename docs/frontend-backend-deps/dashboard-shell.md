# 控制台壳（顶栏项目区）— 后端依赖清单

## 1. 前端入口

- **组件**：`frontend/src/views/DashboardPage.vue`（顶栏 `el-dropdown`、项目切换对话框等）
- **路由**：壳层路由为 `/`，子路由由 `router-view` 承载。

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me`（顶栏用户展示、`menuVisibilityForRole`）。
- **Mock / 仅前端**：
  - **项目切换** 对话框内列表为 **`MOCK_PROJECTS` 常量**，与 `ProjectManagementPage` 的 `sessionStorage` **不同步**。
  - 当前选中项存 **`sessionStorage`** 键 `dsms_portal_mock_current_tenant`；**未**调用项目列表 API。
- **项目管理菜单项**：顶栏下拉中 **「项目管理」** 仅 **`system_admin`** 可见（`v-if`）；侧栏同。导航至 `dashboard-project-management`，依赖见 [project-management.md](./project-management.md)。

## 3. 待对接 API

| 前端能力 | HTTP | 路径 | 说明 |
|----------|------|------|------|
| 当前用户可选项目列表 | GET | 与 `project-management` 列表一致或精简字段 | 用于顶栏展示与切换 |
| 切换「当前工作项目」上下文 | **待定义** | 可仅为前端 `pinia`/路由 `query`，或由 `PATCH /users/me/preferences` 类接口持久化 | 与产品定稿后补表 |

## 4. 与规格的差异 / 缺口

- 规格中 **「当前项目」** 的全局上下文若由后端会话或 JWT 声明，需与前端存储策略对齐。

## 5. 联调检查清单

- [ ] 切换项目后，依赖 `tenant_id` 的子页面请求均带正确上下文
- [ ] 下拉与对话框在无数据、403 时的降级提示
