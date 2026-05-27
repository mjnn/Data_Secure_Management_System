# 分类树节点 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/rule-taxonomy-nodes`，`name`: `dashboard-rule-taxonomy-nodes`
- **页面**：`frontend/src/views/TaxonomyNodesPage.vue`
- **模拟持久化**：`frontend/src/data/taxonomyNodeMock.js`（`dsms_mock_taxonomy_nodes_v1`）

## 2. 当前实现状态

- **已接真实 API**：`GET /api/v1/users/me` — **系统管理员** / **数据安全 FO**（`secOrAdmin`）。
- **侧栏**：`ruleTaxonomyNodes`。
- **能力**：树形列表；根/子节点新增；编辑名称与上级（code 编辑时锁定）；同级上移/下移；删除前校验无子节点且无字段引用 `taxonomy_code`；深度受「分类树层级」最大级约束。
- **上级选择**：`DsmsFilterableSelect` 模糊搜索。

## 3. 待对接 API

规格：`{空间内前缀}/taxonomy/nodes`（GET, POST, PUT, DELETE）；附录 A `taxonomy-nodes`、`taxonomy-nodes/delete`。

| 前端能力 | HTTP | 路径 | 要点 |
|----------|------|------|------|
| 节点列表 | GET | `/taxonomy/nodes` | `skip`/`limit` 或全量 |
| 创建 | POST | 同上 | `code`, `name`, `parent_id`, `sort_order` |
| 更新 | PUT | `/taxonomy/nodes/{node_id}` | |
| 删除 | DELETE | `/taxonomy/nodes/{node_id}` 或 `.../delete` | 子节点与字段引用约束 |

## 4. 与规格的差异 / 缺口

- Mock 节点 `id` 为字符串；后端为整数。
- 未传 `tenant_id` / `space_id`。

## 5. 联调检查清单

- [ ] `code` 空间内唯一
- [ ] 删除有子节点或字段引用时 400 + 中文 `detail`
- [ ] 审计 `behavior_key`：`taxonomy-nodes`、`taxonomy-nodes/delete`
