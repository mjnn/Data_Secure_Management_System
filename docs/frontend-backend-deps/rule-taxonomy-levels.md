# 分类树层级 — 后端依赖清单

## 1. 前端入口

- **路由**：`dashboard-rule-taxonomy-levels` / `/rule-taxonomy/levels`
- **页面**：`frontend/src/views/TaxonomyLevelsPage.vue`

## 2. 当前实现状态

- **已接真实 API**
  - `GET/POST/PUT/DELETE .../taxonomy-levels` — 列表与 CRUD
  - Excel：`GET .../documents/modules/taxonomy_level/template`、`POST .../documents/import?module_key=taxonomy_level`、`POST .../documents/export`
- **缓存**：`spaceConfigCache.taxonomyLevels`；`taxonomyLevelMock.loadTaxonomyLevels()` 优先读缓存

## 3. 联调检查清单

- [x] 列表与种子数据（0–3 级）
- [x] 新增/编辑/删除/上移下移
- [x] Excel 导入导出
- [ ] 403 非 tenant_admin 写操作
