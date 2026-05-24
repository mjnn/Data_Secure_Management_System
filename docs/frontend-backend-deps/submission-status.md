# 填报情况 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/submission-status`，`name`: `dashboard-submission-status`（`frontend/src/router.js`）
- **页面**：`frontend/src/views/SubmissionStatusPage.vue`
- **数据与口径**：与填报任务管理共用 **`frontend/src/data/submissionTasksMock.js`**（`loadSubmissionTasksMerged`、`MOCK_SUBMISSION_FUNCTIONS` 等）；统计与明细表为前端推导，与 **`sessionStorage`** 中任务数据一致；持久化事件 **`dsms-submission-tasks-persisted`**（`useSubmissionTaskFoReminderCount.js` 导出常量）触发本页刷新任务列表与图表。

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — 用于 `effectivePlatformRole`；仅 **`system_admin`** 与 **`security_fo`** 可停留本页，其余角色提示后重定向至控制台首页（与侧栏「填报情况」可见性一致）。
- **Mock / 仅前端**：六类看板指标（未绑定 FO、未创建任务、未下发任务、填报未完成、填报完成未审核、填报审核完成）、ECharts 饼图/柱状图、任务明细表均为前端计算；**无**列表类 HTTP 接口。

## 3. 待对接 API（占位）

| 前端能力 | 说明 |
|----------|------|
| 项目空间下业务功能与 FO 绑定、任务全量及状态 | 与 [submission-task-management.md](./submission-task-management.md) 中列表/功能接口规划一致；本页可复用聚合接口或由前端组合多请求。 |

## 4. 与规格的差异 / 缺口

- 主规格 **`docs/DSMS_IMPLEMENTATION_SPEC.md`** 未单独定义「填报情况」资源；本页为管理端先行看板，**契约以后端定稿为准**。

## 5. 联调检查清单

- [ ] 与任务列表同一租户/项目空间上下文下的功能与任务数据一致
- [ ] 各桶统计口径与产品/规格一致
- [ ] 中文 `detail` / 403 行为与门户一致
