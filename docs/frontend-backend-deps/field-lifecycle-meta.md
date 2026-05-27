# 数据安全生命周期元字段 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/field-lifecycle-meta`，`name`: `dashboard-field-lifecycle-meta`（`frontend/src/router.js`）
- **页面**：`frontend/src/views/FieldLifecycleMetaPage.vue`
- **动态字段组件**：`FieldConfigManagerTable.vue`、`DynamicFieldInputs.vue` 等
- **只读适配**：`frontend/src/data/lifecycleFieldConfigMock.js`（`spaceConfigCache`；无 sessionStorage 种子）

## 2. 当前实现状态

- **已接 API**（`dsmsSpaceApi.js`）：
  - `GET|POST|PUT|DELETE .../forms/lifecycle-field-config` — 列表与增删改（`syncLifecycleFieldConfigTable`）
  - `GET .../fo-function-bindings/me` — 预览区业务功能列
  - `bootstrapSpaceConfig` 预拉配置；`FoLifecycleFillTable` / 填报工作流读 `loadLifecycleFieldConfigTableRows`
- **内置行**：`data_field`、`business_function` 由 `mergeWithBuiltinLifecycleRows` 固定表首；数据字段选项来自字段目录 API

## 3. 联调检查清单

- [ ] 内置行不可删除；自定义字段 Key 唯一
- [ ] 保存后 `PORTAL_DATA_REFRESH_EVENT` 与填报预览列一致
- [ ] 中文 `detail` / 403
