# 填报情况 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/submission-status`，`name`: `dashboard-submission-status`（`frontend/src/router.js`）
- **页面**：`frontend/src/views/SubmissionStatusPage.vue`
- **数据与口径**：与填报任务管理共用 **`frontend/src/data/submissionTasksMock.js`**（`loadSubmissionTasksMerged`、`MOCK_SUBMISSION_FUNCTIONS` 等）；统计与明细表为前端推导，与 **`sessionStorage`** 中任务数据一致；持久化事件 **`dsms-submission-tasks-persisted`**（`useSubmissionTaskFoReminderCount.js` 导出常量）触发本页刷新任务列表与图表。

## 2. 当前实现状态

- **已接真实 API**（`portalApi.js` + `usePortalTenantContext`）：
  - `GET .../business-functions` — 业务功能与 FO 绑定状态
  - `GET .../submission-tasks` — 任务全量（limit 500）
- **Mock / 仅前端**：六类看板指标、ECharts 图表、明细表行归类逻辑仍为前端推导（基于 API 数据）。

## 3. 待对接 API

| 前端能力 | 说明 | 状态 |
|----------|------|------|
| 业务功能 + 任务列表 | 同上两接口 | **已接** |
| 服务端聚合统计 | 可选专用 dashboard 接口 | **待规格** |

## 4. 与规格的差异 / 缺口

- 主规格 **`docs/DSMS_IMPLEMENTATION_SPEC.md`** 未单独定义「填报情况」资源；本页为管理端先行看板，**契约以后端定稿为准**。

## 5. 联调检查清单

- [ ] 与任务列表同一租户/项目空间上下文下的功能与任务数据一致
- [ ] 各桶统计口径与产品/规格一致
- [ ] 中文 `detail` / 403 行为与门户一致
