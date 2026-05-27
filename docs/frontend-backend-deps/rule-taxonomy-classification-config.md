# 分类矩阵与规则 — 后端依赖清单

## 1. 前端入口

- **路由**：`dashboard-rule-taxonomy-classification-config` / `/rule-taxonomy/classification-config`
- **页面**：`frontend/src/views/ClassificationConfigPage.vue`

## 2. 当前实现状态

- **已接真实 API**
  - `GET/POST/PUT/DELETE .../classification/matrix` — 矩阵 CRUD
  - `GET/POST/PUT/DELETE .../classification/rules` — 规则 CRUD
- **本地依赖（bootstrap 缓存）**
  - 分类节点选项：`loadTaxonomyNodes()`（`/taxonomy/nodes` 缓存）
  - 密级选项：`loadSensitivityLevels()`（`/sensitivity-levels` 缓存）
- **待接**
  - `POST .../classification/matrix/batch-import` — 批量导入（可选）

## 3. 规则条件 JSON（与后端 `classification_service.rule_matches` 一致）

| type | 说明 |
|------|------|
| `default` | 匹配全部字段 |
| `identifier_contains` | 标识符包含 `value` |
| `field_name_contains` | 字段名包含 `value` |
| `data_type_equals` | 数据类型等于 `value` |

矩阵 `cells_json`：`[{ "taxonomy_code": "...", "sensitivity_level": "..." }]`

## 4. 联调检查清单

- [ ] 创建矩阵映射后，字段带对应 `taxonomy_code` 重算应用矩阵密级
- [ ] 创建规则后，匹配字段重算输出规则密级
- [ ] 矩阵覆盖规则（同字段既有规则又有 taxonomy_code 时矩阵优先）
- [ ] 中文 `detail` 错误提示
