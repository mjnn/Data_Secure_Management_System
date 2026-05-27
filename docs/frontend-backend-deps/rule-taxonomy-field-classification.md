# 数据字段分类 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/rule-taxonomy-field-classification`，`name`: `dashboard-rule-taxonomy-field-classification`
- **页面**：`frontend/src/views/TaxonomyFieldClassificationPage.vue`
- **组件**：`frontend/src/components/DsmsFilterableSelect.vue`
- **依赖 mock 只读**：`taxonomyLevelMock.js`（层级 0/1/2/3 注册表，暂无 REST）；`taxonomyNodeMock.js` / `dataFieldCatalogMock.js` 优先读 API 缓存

## 2. 当前实现状态

- **已接真实 API**
  - `GET /api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}/field-catalog` — 列表含 `taxonomy_code`
  - `PUT .../field-catalog/{entry_id}` — 保存/清除 `taxonomy_code`
  - `GET .../taxonomy/nodes` — 逐级下拉建树
- **Mock / 本地**
  - 分类树层级定义仍来自 `taxonomyLevelMock.js`（Excel 导入路径待接）
- **角色**：系统管理员 / 数据安全 FO（`secOrAdmin`）

## 3. 待对接 API

| 前端能力 | HTTP | 路径 | 要点 | 状态 |
|----------|------|------|------|------|
| 分类树层级 | Excel 导入 | 文档资源 `taxonomy_level` 模块 | 与节点 depth 对齐 | 待接 |
| 自动分类结果 | GET | `/classification/results` | phase23 规则求值结果 | 本页未用 |

## 4. 与规格的差异 / 缺口

- 本页为**人工**绑定 `taxonomy_code`；phase23 自动分类矩阵/规则/重算为独立能力。
- 前端 `label` 映射后端 `field_name`；`identifier_key` 原样提交。

## 5. 联调检查清单

- [x] 列表读取 `field-catalog` 缓存
- [x] PUT 更新 `taxonomy_code` 后刷新列表
- [ ] 403 与中文 `detail`（非 tenant_admin 保存）
- [ ] `taxonomy_code` 与空间内节点 `code` 一致
- [ ] 逐级选择：子节点 `parent_id` 与 API 返回 id 一致
