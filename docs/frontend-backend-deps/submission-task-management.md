# 填报任务管理 — 后端依赖清单

## 1. 前端入口

- **列表路由**：`path`: `/submission-task`，`name`: `dashboard-submission-task`（`frontend/src/router.js`）
- **详情路由**：`path`: `/submission-task/:taskId`，`name`: `dashboard-submission-task-detail`（`frontend/src/views/SubmissionTaskDetailPage.vue`）
- **任务工具**：`frontend/src/data/submissionTasksMock.js`（归一化、`hasRenderableFormSnapshot`、业务功能名称缓存；**无** sessionStorage 种子）
- **列表组件**：`frontend/src/views/SubmissionTaskManagementPage.vue`

## 2. 当前实现状态

- **已接真实 API**（`frontend/src/api/portalApi.js`，租户/空间由 `usePortalTenantContext` 解析）：
  - `GET /api/v1/users/me` — 角色与路由守卫
  - `GET .../business-functions` — 业务功能列表（含 `has_active_fo_binding`）；写入 `setBusinessFunctionCatalog`
  - `GET|POST .../submission-tasks`、`PATCH .../submission-tasks/{id}`、`POST .../submission-tasks/dispatch`
  - `POST .../submission-tasks/{id}/cancel-request` — 功能 FO 取消申请
  - `GET .../fo-function-bindings/me` — 当前用户生效绑定
  - 工作流步骤仍写回后端：`portalTaskSync.js` → `PATCH`；**`foFillStatus=submitted` 时后端自动创建 `submission_fill_review`**
  - `portalTaskCache`：列表/详情拉取后供字段目录「关联业务功能」聚合
- **工作流（已接 API 配置 + 任务 PATCH）**：
  - 相关性 / 表达式 / 生命周期列定义：`bootstrapSpaceConfig` + `submissionFoWorkflowMock.js`
  - 治理识别：`evaluateSecurityRequirements` + 规则缓存（`foSubmissionGovernanceMock.js`）
  - 「数据安全不相关」：由已提交任务 `foRelevanceConclusion` 推导（`foFunctionSecurityTagMock.js`）
- **仍 Mock / 本地**：
  - **删除草稿任务**：后端暂无 DELETE，前端提示不可用
  - 侧栏 FO 红点：`computeFoSubmissionReminderCount` 读 `getPortalTaskCache()`（须先拉取任务列表）

## 3. 待对接 API（按能力块）

| 前端能力 | HTTP | 路径 | 状态 |
|----------|------|------|------|
| 业务功能列表 | GET | `.../business-functions` | **已接** |
| 填报任务 CRUD/下发 | GET/POST/PATCH/POST dispatch | `.../submission-tasks*` | **已接**（无 DELETE） |
| 取消填报申请 | POST | `.../submission-tasks/{id}/cancel-request` | **已接** |
| FO 绑定 | GET/POST | `.../fo-function-bindings/me`、`.../fo-function-binding-requests` | **已接**（绑定卡片） |
| 填报审核 | POST approve/reject | `.../approval-requests/{id}/*` | **已接**（详情页） |
| 工作流中间态（相关性/生命周期/治理） | — | 规则与元字段 API | **待接** |

## 4. 与规格的差异 / 缺口

- 主规格 **`docs/DSMS_IMPLEMENTATION_SPEC.md`** 当前未单独定义「填报任务管理」数据模型与 URL；本页为门户先行实现，**业务契约以后端定稿为准**。
- 前端 **项目** 文案对应规格中的 **`tenant`**；任务与功能实际作用域应为 **`tenant_id` + 项目空间**（见规格多租户章节）。

## 5. 联调检查清单

- [ ] 列表分页 `skip`/`limit`、`total`/`items`
- [ ] 未绑定功能 FO 的功能：**禁止下发**（后端与前端双重校验）
- [ ] 下发请求体 **`dispatch_note`** 必填；空串 422 与中文 `detail`
- [ ] 仅草稿可编辑、删除、下发；已下发任务不可回退（若产品如此约定）
- [ ] 中文 `detail` / 错误提示
- [ ] 401/403 与全局 token 行为
- [ ] 需审计的操作：`behavior_key` 与附录 A 的 key **逐字相同**
