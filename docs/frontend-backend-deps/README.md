# 前端页面 — 后端依赖清单索引

本目录存放 **各前端页面对后端的依赖说明**，编写规范见 **`../DSMS_FRONTEND_BACKEND_DEPS.md`**。

| 页面（中文） | 路由 `name` / `path` | 主要源码 | 依赖清单 |
|--------------|----------------------|----------|----------|
| 用户管理 | `dashboard-user-management` / `/user-management` | `frontend/src/views/UserManagementPage.vue` | [user-management.md](./user-management.md) |
| 项目管理 | `dashboard-project-management` / `/project-management` | `frontend/src/views/ProjectManagementPage.vue` | [project-management.md](./project-management.md)（**仅系统管理员**可见侧栏与顶栏入口） |
| 控制台壳（顶栏项目菜单、项目切换） | `DashboardPage` 子路由承载 | `frontend/src/views/DashboardPage.vue` | [dashboard-shell.md](./dashboard-shell.md) |
| 填报任务管理 | `dashboard-submission-task` / `/submission-task`；详情 `dashboard-submission-task-detail` / `/submission-task/:taskId` | `SubmissionTaskManagementPage.vue`、`SubmissionTaskDetailPage.vue`、`data/submissionTasksMock.js` | [submission-task-management.md](./submission-task-management.md) |
| 填报情况 | `dashboard-submission-status` / `/submission-status` | `SubmissionStatusPage.vue`、`data/submissionTasksMock.js` | [submission-status.md](./submission-status.md) |
| 数据安全生命周期元字段 | `dashboard-field-lifecycle-meta` / `/field-lifecycle-meta` | `FieldLifecycleMetaPage.vue`、`components/form-config/*`、`data/lifecycleFieldConfigMock.js` | [field-lifecycle-meta.md](./field-lifecycle-meta.md) |
| 数据字段（主数据选项） | `dashboard-field-catalog` / `/field-catalog` | `FieldCatalogPage.vue`、`data/dataFieldCatalogMock.js` | [field-catalog.md](./field-catalog.md) |
| 相关性问卷 | `dashboard-rule-relevance-questionnaire` / `/rule-relevance/questionnaire` | `RelevanceQuestionnairePage.vue`、`data/relevanceQuestionnaireMock.js` | [rule-relevance-questionnaire.md](./rule-relevance-questionnaire.md) |
| 相关性标准 — 表达式配置和验证 | `dashboard-rule-relevance-standard-expression` / `/rule-relevance/expression` | `RelevanceStandardExpressionPage.vue`、`RelevanceFoFillEvaluateCard.vue`、`RelevanceLogicExprBuilder.vue`、`relevanceLogicTree.js`、`relevanceExpressionMock.js` | [rule-relevance-standard-expression.md](./rule-relevance-standard-expression.md) |
| 分类树层级 | `dashboard-rule-taxonomy-levels` / `/rule-taxonomy-levels` | `TaxonomyLevelsPage.vue`、`data/taxonomyLevelMock.js` | [rule-taxonomy-levels.md](./rule-taxonomy-levels.md)（已接 `/taxonomy-levels` + Excel） |
| 分类树节点 | `dashboard-rule-taxonomy-nodes` / `/rule-taxonomy-nodes` | `TaxonomyNodesPage.vue`、`data/taxonomyNodeMock.js` | [rule-taxonomy-nodes.md](./rule-taxonomy-nodes.md) |
| 数据字段分类 | `dashboard-rule-taxonomy-field-classification` / `/rule-taxonomy-field-classification` | `TaxonomyFieldClassificationPage.vue`、`DsmsFilterableSelect.vue`、`fieldTaxonomyClassificationMock.js`、`taxonomyNodeMock.js` | [rule-taxonomy-field-classification.md](./rule-taxonomy-field-classification.md) |
| 分类矩阵与规则 | `dashboard-rule-taxonomy-classification-config` / `/rule-taxonomy/classification-config` | `ClassificationConfigPage.vue` | [rule-taxonomy-classification-config.md](./rule-taxonomy-classification-config.md) |
| 自动分类结果 | `dashboard-rule-taxonomy-classification-results` / `/rule-taxonomy/classification-results` | `ClassificationResultsPage.vue` | [rule-taxonomy-classification-results.md](./rule-taxonomy-classification-results.md) |
| 密级绑定（密级定义 + 数据字段绑定） | `dashboard-rule-classification-levels` / `/rule-classification/levels`；`dashboard-rule-classification-bindings` / `/rule-classification/bindings` | `ClassGradeModuleLayout.vue`、`SensitivityLevelsPage.vue`、`FieldClassGradeBindingPage.vue`、`sensitivityLevelMock.js`、`fieldClassGradeBindingMock.js` | [rule-classification.md](./rule-classification.md) |
| 安全要求（逻辑表达式） | `dashboard-rule-security` / `/rule-security` | `SecurityRequirementPage.vue`、`SecurityLogicExprBuilder.vue`、`securityExpressionMock.js`、`securityConditionCatalog.js` | [rule-security.md](./rule-security.md) |
| 审批管理 | `dashboard-approval` / `/approval` | `ApprovalManagementPage.vue`、`approvalRequestsMock.js`、`approvalChains.js` | [approval-management.md](./approval-management.md) |
| 文档资源 | `dashboard-document-resource` / `/document-resource` | `DocumentResourcePage.vue`、`usePortalTenantContext.js` | [document-resource.md](./document-resource.md) |

**数据模型（全表规划）**：见 **[../DSMS_DATA_MODEL.md](../DSMS_DATA_MODEL.md)**。

**分期联调（规格 §11）**：[phase11-integration-checklist.md](./phase11-integration-checklist.md)

**新增页面时**：在本表新增一行，并创建或链接对应 `<slug>.md`。
