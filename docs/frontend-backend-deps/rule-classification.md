# 密级绑定 — 后端依赖清单

## 1. 前端入口

- **路由**：`/rule-classification/levels`（兼容 `/rule-classification-levels`）、`/rule-classification/bindings`（兼容 `/rule-classification-bindings`）
- **布局**：`ClassGradeModuleLayout.vue` + `ClassGradeModuleShell.vue`（步骤壳固定，子路由仅刷新下方内容区）
- **页面**：
  - 密级定义：`SensitivityLevelsPage.vue` → `sensitivityLevelMock.js`（`dsms_mock_sensitivity_levels_v1`）
  - 数据字段绑定：`FieldClassGradeBindingPage.vue` → `fieldClassGradeBindingMock.js`（`dsms_mock_field_class_grade_bindings_v1`）
- **权限**：`system_admin` / `security_fo`（`secOrAdmin`）；非授权角色重定向控制台首页

## 2. 当前实现状态

| 能力 | 状态 |
|------|------|
| 密级定义 CRUD、排序 | **Mock**（sessionStorage） |
| 字段 ↔ `grade_label` 绑定、清除 | **Mock**；依赖「数据字段」主表 `dataFieldCatalogMock.js` |
| 密级名称变更 | Mock 内 `rebindGradeLabel` 同步绑定表 |
| 删除密级 | 若仍有字段绑定该 `label`，禁止删除 |

## 3. 待对接 API（规格 §6 / 附录 A）

| 能力 | 方法 | 路径 | `behavior_key` |
|------|------|------|----------------|
| 列表/批量保存绑定 | GET, PUT | `/api/v1/dsms/fields/class-grade` | `field-class-grade` |
| 删除单字段绑定 | DELETE | `/api/v1/dsms/fields/class-grade/{catalog_entry_id}` | `field-class-grade` |

**说明**：当前前端将「密级定义」独立为 Mock 表；规格中 `FieldCatalogEntry.sensitivity_level` 与 `FieldClassGrade.grade_label` 关系以定稿 OpenAPI 为准。联调时若后端仅暴露 `class-grade` 而无独立密级字典，本页「密级定义」需改为配置项或枚举接口。

## 4. 与规格的差异 / 缺口

- 未传 `tenant_id` / `space_id`；密级字典与绑定均存 sessionStorage。
- 「密级定义」无对应附录 A 键（待产品确认是否纳入配置中心）。

## 5. 联调检查清单

- [ ] 403 与中文 `detail`（非 FO/管理员）
- [ ] PUT body：`field_catalog_entry_id`、`grade_label`、`notes`（以 OpenAPI 为准）
- [ ] 删除绑定后列表与主表展示一致
- [ ] 审计 `field-class-grade` 与操作一致
- [ ] 重命名密级标签时绑定表是否由后端级联（或需前端二次 PUT）
