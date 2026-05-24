# 填报任务管理 — 后端依赖清单

## 1. 前端入口

- **列表路由**：`path`: `/submission-task`，`name`: `dashboard-submission-task`（`frontend/src/router.js`）
- **详情路由**：`path`: `/submission-task/:taskId`，`name`: `dashboard-submission-task-detail`（`frontend/src/views/SubmissionTaskDetailPage.vue`）
- **共享模拟数据**：`frontend/src/data/submissionTasksMock.js`（`sessionStorage` 键名、业务功能表、任务归一化）
- **列表组件**：`frontend/src/views/SubmissionTaskManagementPage.vue`

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — 用于 `effectivePlatformRole`；**列表**允许 **`system_admin`**、**`security_fo`**、**`function_fo`**（含超管视为管理员）；**详情（审核）** 仅 **`system_admin`** 与 **`security_fo`**，功能 FO 访问详情将被重定向回列表。
- **Mock / sessionStorage / 仅前端**：
  - **业务功能列表**（含是否已绑定功能 FO）为共享模块 **`submissionTasksMock.js`** 中常量，未请求后端。
  - **填报任务**列表与写操作使用 **`sessionStorage`** 键 **`dsms_mock_submission_tasks_v1`**；首次无数据时注入种子数据；持久化后派发 **`dsms-submission-tasks-persisted`** 事件，供侧栏红点刷新（见 `useSubmissionTaskFoReminderCount.js`）。
  - **功能 FO 绑定功能**：与红点计数共用导出常量 **`MOCK_FO_BOUND_FUNCTION_IDS`**（`frontend/src/composables/useSubmissionTaskFoReminderCount.js`），后续改为接口字段。
  - **数据安全侧**：支持**多选业务功能**汇总列表、**跨功能多选草稿批量下发**（逐条校验已绑功能 FO）；可进入**任务详情**查看功能 FO **填报表单只读快照**（`foFillFormSnapshot`，待填报流程与接口定稿）、填报情况汇总（含主责 + 模拟协同行）并对**已提交**任务做**审核通过 / 退回修改**（模拟）。下发、任务增删改、审核均为前端状态 + `ElMessage`，无 HTTP 写接口。
  - **功能 FO 侧**：列表支持**关键词搜索**与**我的进度**筛选。填报正文为 **`FoLifecycleFillTable`** 明细表：列来自 **`lifecycleFieldConfigMock.js`**（与「数据安全生命周期元字段」配置同源），首列为 **数据字段**、第二列为 **业务功能**（绑定多项时 `el-select` 可筛选单选，仅一项时只读带出），其后为数据安全 FO 配置的动态列；支持 **新增条目** 多行。草稿写入任务字段 **`foFillLifecycleRows`**；提交生成 **`foFillFormSnapshot`**（含 **`formTable`** 供只读展示，与 `SubmissionFillFormReadonly` 对齐）。绑定功能 ID 仍用 **`MOCK_FO_BOUND_FUNCTION_IDS`**（`useSubmissionTaskFoReminderCount.js`），后续改接口。
- **角色与拦截**（与 `usePortalMenuVisibility` 一致）：
  - **系统管理员 / 数据安全 FO**：侧栏「填报管理」含「填报情况」+「填报任务管理」；列表为**管理端**（多选功能、CRUD、跨功能批量下发）；**详情**为审核、填报情况汇总与**填报表单只读快照**。
  - **功能 FO**：侧栏「填报管理」下**仅**「填报任务管理」（无「填报情况」）；本页为**执行端**（本人绑定功能已下发任务列表、搜索与筛选、红点提醒、填报与查看操作）。

## 3. 待对接 API（按能力块）

规格与 OpenAPI 中尚未单列「填报任务」资源时，以下路径为 **占位**，定稿后替换为真实路径与字段名。

| 前端能力 | HTTP | 路径（相对 `/api/v1/...`） | Query / Body 要点 | 响应字段要点 | 权限（约定） | 附录 A `behavior_key`（若有） |
|----------|------|------------------------------|-------------------|--------------|----------------|--------------------------------|
| 当前项目空间下可选业务功能（含是否已绑定功能 FO） | GET | **`待规格`** 例如 `dsms/.../business-functions` 或复用现有空间配置接口 | `tenant_id` / `space_id` 与上下文一致 | 功能 id、名称、`function_fo_bound` 等 | `security_fo` 或 `tenant_admin` / `super_admin`（以定稿为准） | — |
| 填报任务列表 | GET | **`待规格`** `.../submission-tasks` | `skip`,`limit`，筛选 `function_id`、状态 | `total`,`items` | 同上 | — |
| 创建填报任务 | POST | **`待规格`** | `function_id`,`title`, 可选 `internal_note` | 新建实体 | 数据安全侧角色 | **`待规格`**（定稿后须与附录 A 逐字一致） |
| 更新填报任务（草稿） | PATCH | **`待规格`** `.../{task_id}` | 可改字段以定稿为准 | 更新后实体 | 同上 | 同上 |
| 删除填报任务（草稿） | DELETE | **`待规格`** `.../{task_id}` | — | 204 或约定体 | 同上 | 同上 |
| 批量下发 | POST | **`待规格`** 例如 `.../submission-tasks/dispatch` | `task_ids[]`，**必填** `dispatch_note`（填报任务说明）；服务端须校验对应 **业务功能已绑定功能 FO** | 成功计数、失败项与 `reason`（中文） | 同上 | **`待规格`** |
| 功能 FO：我的待办任务列表 | GET | **`待规格`** | 当前用户绑定功能、`status=dispatched`、填报进度等 | `total`,`items` | `function_fo` | — |
| 功能 FO：待办提醒计数（侧栏红点） | GET | **`待规格`** 或与上表合并为 unread 字段 | — | 整数 | `function_fo` | — |
| 填报执行（开始 / 暂存 / 提交 / 申请取消） | POST/PATCH | **`待规格`** | 与填报子功能、审批流对齐 | 以定稿为准 | `function_fo` | **`待规格`** |

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
