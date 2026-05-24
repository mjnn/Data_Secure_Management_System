# 数据字段 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/field-catalog`，`name`: `dashboard-field-catalog`（`frontend/src/router.js`）
- **页面**：`frontend/src/views/FieldCatalogPage.vue`
- **模拟持久化**：`frontend/src/data/dataFieldCatalogMock.js`（`sessionStorage` 键 **`dsms_mock_data_field_catalog_v1`**、申请列表 **`dsms_mock_data_field_catalog_requests_v1`**）
- **与填报/元字段联动**：`data/submissionTasksMock.js`（已审核任务的 **`foFillLifecycleRows`**）、`data/lifecycleFieldConfigMock.js`（内置 **`data_field`** 的 **`allowed_values`** 取自目录排序结果）

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — 用于区分数据安全 FO / 系统管理员与功能 FO。
- **Mock / sessionStorage**：
  - **数据安全 FO / 系统管理员**：目录全量增删改查；展示每条字段在已审核通过填报中的关联业务功能；审核功能 FO 提交的**新增 / 删除**申请。
  - **功能 FO**：仅展示与 `MOCK_FO_BOUND_FUNCTION_IDS` 绑定业务功能相关、且出现在已审核通过填报中的目录项；新增、删除走申请；**我的申请**按 `requestedBy`（当前登录 `username`）过滤。
- **事件**：目录或申请变更后派发 **`DATA_FIELD_CATALOG_PERSIST_EVENT`**，生命周期元字段页预览与填报任务页明细列会刷新选项。

## 3. 待对接 API（按能力块）

| 前端能力 | 说明 |
|----------|------|
| 数据字段主数据 CRUD | 空间内主数据或字典接口（以定稿 OpenAPI 为准） |
| 功能 FO 申请与审核 | 工作流/审批单与目录写回 |
| 关联业务功能聚合 | 基于已审核填报明细或关系表的服务端汇总 |

## 4. 与规格的差异 / 缺口

- 未传 **`tenant_id` / `space_id`**；功能 FO 绑定关系为前端常量模拟；申请人仅写 `username` 字符串。

## 5. 联调检查清单

- [ ] 403 与中文 `detail`
- [ ] 与生命周期 **`data_field`** 下拉选项同源
- [ ] 审计 `behavior_key` 与附录 A 定稿一致（实现时补充）
