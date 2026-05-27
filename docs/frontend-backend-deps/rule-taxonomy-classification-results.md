# 自动分类结果 — 后端依赖清单

## 1. 前端入口

- **路由**：`dashboard-rule-taxonomy-classification-results` / `/rule-taxonomy/classification-results`
- **页面**：`frontend/src/views/ClassificationResultsPage.vue`

## 2. 当前实现状态

- **已接真实 API**
  - `GET .../classification/results` — 分页列表
  - `POST .../classification/recompute` — 全量重算
  - `PUT .../classification/results/{id}/manual` — 人工覆写密级
  - `POST .../classification/results/{id}/revert-auto` — 恢复自动
  - `GET .../classification/audit` — 操作审计（Tab「操作审计」，支持 `behavior_key` 筛选）
  - `GET .../classification/export` — 导出 CSV（Tab「分类结果」工具栏）
- **关联页**：矩阵/规则配置见 [rule-taxonomy-classification-config.md](./rule-taxonomy-classification-config.md)

## 3. 联调检查清单

- [ ] 配置规则后重算产生结果行
- [ ] 人工覆写与恢复自动
- [ ] 中文 `detail` 错误提示
