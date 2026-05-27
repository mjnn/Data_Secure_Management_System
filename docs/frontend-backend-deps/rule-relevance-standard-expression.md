# 相关性标准表达式 — 后端依赖清单

## 1. 前端入口

- **路由**：`dashboard-rule-relevance-standard-expression`
- **页面**：`frontend/src/views/RelevanceStandardExpressionPage.vue`
- **试算卡片**：`frontend/src/components/relevance/RelevanceFoFillEvaluateCard.vue`
- **表达式适配**：`frontend/src/data/relevanceExpressionMock.js`（`spaceConfigCache`；无 sessionStorage）

## 2. 当前实现状态

- **已接 API**：
  - `GET|PUT .../relevance/rules` — 逻辑树与相关/不相关结论（`fetchRelevanceExpression` / `saveRelevanceExpression`）
  - 问卷题目来自 `fetchQuestionnaireQuestions`（见问卷页清单）
  - 填报工作流步骤写回 `PATCH .../submission-tasks/{id}`（`submissionFoWorkflowMock` → `portalTaskSync`）
- **仍本地**：逻辑树 UI 组件（`relevanceLogicTree.js`）；门户规则试算仍可读 `securityRequirementRulesMock` 缓存

## 3. 联调检查清单

- [ ] 保存表达式后刷新步骤条状态（`PORTAL_DATA_REFRESH_EVENT`）
- [ ] FO 试算：必填题目、表达式求值、相关→生命周期 / 不相关→任务结束
- [ ] 中文 `detail` 与 403
