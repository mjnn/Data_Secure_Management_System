# 相关性问卷 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/rule-relevance/questionnaire`（兼容重定向 `/rule-relevance-questionnaire`），`name`: `dashboard-rule-relevance-questionnaire`
- **布局**：`RelevanceModuleLayout.vue` + `RelevanceStandardModuleShell`（步骤条固定，仅子页切换）（`frontend/src/router.js`）
- **页面**：`frontend/src/views/RelevanceQuestionnairePage.vue`
- **只读适配**：`frontend/src/data/relevanceQuestionnaireMock.js`（`spaceConfigCache`；无 sessionStorage 种子）

## 2. 当前实现状态

- **已接真实 API**（`dsmsSpaceApi.js` + `usePortalTenantContext`）：
  - `GET /api/v1/users/me` — **`system_admin`（含 `is_superuser`）** 与 **`security_fo`** 可停留本页
  - `GET|POST|PUT .../questionnaires/questions`、`POST .../questions/delete`
  - `bootstrapSpaceConfig` 预拉问卷写入缓存；工作流/表达式页通过 `loadRelevanceQuestionnaireQuestions` 读取
- **功能 FO 试填与相关性判定**：见 [rule-relevance-standard-expression.md](./rule-relevance-standard-expression.md)（`RelevanceFoFillEvaluateCard`）

## 3. 待对接 / 收敛项

- 选项子表与后端 `options_json` 映射以 OpenAPI 为准（当前 API 已承载选项）

## 4. 与规格的差异 / 缺口

- 权限：后端题目写接口为 **tenant_admin**；门户以 **security_fo** 为产品角色，联调时需统一鉴权策略。

## 5. 联调检查清单

- [ ] 403 与中文 `detail`
- [ ] 分页 `skip`/`limit`、`total`/`items`
- [ ] 写操作审计 `behavior_key`：`questionnaire/questions`、`questionnaire/questions/delete`
- [ ] 题目 `key` 空间内唯一约束
