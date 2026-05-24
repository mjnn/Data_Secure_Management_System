# 数据安全生命周期元字段 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/field-lifecycle-meta`，`name`: `dashboard-field-lifecycle-meta`（`frontend/src/router.js`）
- **页面**：`frontend/src/views/FieldLifecycleMetaPage.vue`
- **动态字段组件（对齐 `ref/dynamic field`）**：`frontend/src/components/form-config/FieldConfigManagerTable.vue`、`DynamicFieldInputs.vue`、`SelectOptionValuesEditor.vue`、`fieldConfigManagerConstants.js`
- **模拟持久化**：`frontend/src/data/lifecycleFieldConfigMock.js`（`sessionStorage` 键 **`dsms_mock_lifecycle_field_config_v1`**）

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — 用于角色判断；仅 **`system_admin`** 与 **`security_fo`** 可停留本页（与 `usePortalMenuVisibility` 中 `fieldLifecycle` 一致），其余角色提示后重定向至控制台首页。
- **Mock / sessionStorage / 仅前端**：
  - 字段定义列表的增删改、顺序、校验规则与选项均为 **浏览器本地存储**；保存时做 **字段 Key 唯一性**、蛇形命名、正则合法性、单选/多选须配置选项等前端校验（**内置「业务功能」行可不维护选项**，填报时由功能 FO 绑定关系注入）。
  - **默认内置**（`mergeWithBuiltinLifecycleRows`）：**`data_field`（数据字段）**、**`business_function`（业务功能）** 两条必填单选，固定于表首且结构锁定、不可删除。**`data_field` 的允许值列表**以 **`数据字段`** 页（`dataFieldCatalogMock` / `getCatalogLabelsSorted`）为权威来源，元字段配置表内**不可直接编辑**该项的选项文本（见 `FieldConfigManagerTable` 的 `allowedValuesLockedFieldKeys`）。
  - 页内 **「填报预览」** 使用与功能 FO 填报任务相同的 **`FoLifecycleFillTable`**，按当前配置表（含未保存的编辑态）实时展示**完整明细表**（数据字段、业务功能、动态列、新增条目）；列结构关键字段变化时重置为 1 行示例以防错位。
- **角色与拦截**：数据安全 FO、系统管理员；功能 FO 无侧栏入口，直链访问将被重定向。

## 3. 待对接 API（按能力块）

规格 **Phase 1**（`docs/DSMS_IMPLEMENTATION_SPEC.md` 7.1）：`{空间内前缀}/forms/lifecycle-field-config`，附录 A **`lifecycle-field-config`**，方法 **GET, POST, PUT, DELETE**。

| 前端能力 | HTTP | 路径（相对空间内前缀） | Query / Body 要点 | 响应字段要点 | 权限（约定） | 附录 A `behavior_key` |
|----------|------|------------------------|-------------------|--------------|--------------|------------------------|
| 列表字段定义 | GET | `/forms/lifecycle-field-config` | `skip`,`limit`（若分页） | `total`,`items` 或等价结构 | `security_fo` / `system_admin`（以定稿为准） | `lifecycle-field-config` |
| 创建 / 更新 / 删除 | POST, PUT, DELETE | 同上（含子路径以 OpenAPI 为准） | 与 `lifecycle_field_definition` / `lifecycle_field_config` 对齐 | 以定稿为准 | 同上 | `lifecycle-field-config` |

## 4. 与规格的差异 / 缺口

- 当前未传 **`tenant_id` / `space_id`**，未接真实 URL；持久化仅为 **`sessionStorage`** 模拟。
- 规格实体 **`lifecycle_field_definition`** 与 **`lifecycle_field_config`** 的字段级契约以实现时 OpenAPI 为准；本页表格行结构参考 **`ref/dynamic field`** 中 `FormFieldConfigItem` 形态，联调时需与后端 **对齐字段名与枚举**。

## 5. 联调检查清单

- [ ] 列表分页 `skip`/`limit`、`total`/`items`（若接口分页）
- [ ] 403 与中文 `detail`
- [ ] 写操作审计 `behavior_key` 与附录 A **逐字一致**：`lifecycle-field-config`
- [ ] 与功能 FO 填报任务中的 **`FoLifecycleFillTable`** 明细表及任务上 **`foFillLifecycleRows` / `foFillFormSnapshot.formTable`** 使用同一套字段定义数据源
