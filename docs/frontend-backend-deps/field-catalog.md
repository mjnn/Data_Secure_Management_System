# 数据字段 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/field-catalog`，`name`: `dashboard-field-catalog`（`frontend/src/router.js`）
- **页面**：`frontend/src/views/FieldCatalogPage.vue`
- **只读适配**：`frontend/src/data/dataFieldCatalogMock.js`（从 `spaceConfigCache` 读取，由 `fetchFieldCatalog` 填充；已移除 sessionStorage 种子）
- **与填报/元字段联动**：`data/submissionTasksMock.js`（已审核任务的 **`foFillLifecycleRows`**）、`data/lifecycleFieldConfigMock.js`（内置 **`data_field`** 的 **`allowed_values`** 取自目录排序结果）

## 2. 当前实现状态

- **已接 API**（`portalApi.js`）：
  - `GET .../field-catalog` — 目录列表
  - `POST|PUT|DELETE .../field-catalog` — 数据安全 FO / 超管直接 CRUD
  - `POST .../field-catalog-change-requests` — 功能 FO 增删申请
  - 待办/我的申请：`GET .../approval-requests`（`field_catalog_create|delete`）
  - 审核：`POST .../approval-requests/{id}/approve|reject`
  - `GET .../fo-function-bindings/me` — 功能 FO 绑定范围
- **仍 Mock**：关联业务功能列从已审核填报（`portalTaskCache` 或 `submissionTasksMock` 的 `foFillLifecycleRows`）聚合，非服务端汇总。

## 3. 待对接 API

| 前端能力 | 说明 | 状态 |
|----------|------|------|
| 数据字段主数据 CRUD | `.../field-catalog` | **已接** |
| 功能 FO 申请与审核 | change-requests + approval-requests | **已接** |
| 关联业务功能聚合 | 基于已审核填报明细 | **待接**（仍 mock） |

## 4. 与规格的差异 / 缺口

- 未传 **`tenant_id` / `space_id`**；功能 FO 绑定关系为前端常量模拟；申请人仅写 `username` 字符串。

## 5. 联调检查清单

- [ ] 403 与中文 `detail`
- [ ] 与生命周期 **`data_field`** 下拉选项同源
- [ ] 审计 `behavior_key` 与附录 A 定稿一致（实现时补充）
