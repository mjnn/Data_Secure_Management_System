# 前端页面 — 后端依赖清单索引

本目录存放 **各前端页面对后端的依赖说明**，编写规范见 **`../DSMS_FRONTEND_BACKEND_DEPS.md`**。

| 页面（中文） | 路由 `name` / `path` | 主要源码 | 依赖清单 |
|--------------|----------------------|----------|----------|
| 用户管理 | `dashboard-user-management` / `/user-management` | `frontend/src/views/UserManagementPage.vue` | [user-management.md](./user-management.md) |
| 项目管理 | `dashboard-project-management` / `/project-management` | `frontend/src/views/ProjectManagementPage.vue` | [project-management.md](./project-management.md)（**仅系统管理员**可见侧栏与顶栏入口） |
| 控制台壳（顶栏项目菜单、项目切换模拟等） | `DashboardPage` 子路由承载 | `frontend/src/views/DashboardPage.vue` | [dashboard-shell.md](./dashboard-shell.md) |
| 填报任务管理 | `dashboard-submission-task` / `/submission-task`；详情 `dashboard-submission-task-detail` / `/submission-task/:taskId` | `SubmissionTaskManagementPage.vue`、`SubmissionTaskDetailPage.vue`、`data/submissionTasksMock.js` | [submission-task-management.md](./submission-task-management.md) |
| 填报情况 | `dashboard-submission-status` / `/submission-status` | `SubmissionStatusPage.vue`、`data/submissionTasksMock.js` | [submission-status.md](./submission-status.md) |
| 数据安全生命周期元字段 | `dashboard-field-lifecycle-meta` / `/field-lifecycle-meta` | `FieldLifecycleMetaPage.vue`、`components/form-config/*`、`data/lifecycleFieldConfigMock.js` | [field-lifecycle-meta.md](./field-lifecycle-meta.md) |
| 数据字段（主数据选项） | `dashboard-field-catalog` / `/field-catalog` | `FieldCatalogPage.vue`、`data/dataFieldCatalogMock.js` | [field-catalog.md](./field-catalog.md) |

**新增页面时**：在本表新增一行，并创建或链接对应 `<slug>.md`。
