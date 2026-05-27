import { createRouter, createWebHistory } from "vue-router";
import LoginPage from "./views/LoginPage.vue";
import DashboardPage from "./views/DashboardPage.vue";
import DashboardHomeView from "./views/DashboardHomeView.vue";
import UserManagementPage from "./views/UserManagementPage.vue";
import ProjectManagementPage from "./views/ProjectManagementPage.vue";
import SubmissionTaskManagementPage from "./views/SubmissionTaskManagementPage.vue";
import SubmissionTaskDetailPage from "./views/SubmissionTaskDetailPage.vue";
import SubmissionStatusPage from "./views/SubmissionStatusPage.vue";
import FieldLifecycleMetaPage from "./views/FieldLifecycleMetaPage.vue";
import FieldCatalogPage from "./views/FieldCatalogPage.vue";
import RelevanceQuestionnairePage from "./views/RelevanceQuestionnairePage.vue";
import RelevanceStandardExpressionPage from "./views/RelevanceStandardExpressionPage.vue";
import RelevanceModuleLayout from "./views/RelevanceModuleLayout.vue";
import TaxonomyLevelsPage from "./views/TaxonomyLevelsPage.vue";
import TaxonomyFieldClassificationPage from "./views/TaxonomyFieldClassificationPage.vue";
import ClassificationResultsPage from "./views/ClassificationResultsPage.vue";
import ClassificationConfigPage from "./views/ClassificationConfigPage.vue";
import TaxonomyNodesPage from "./views/TaxonomyNodesPage.vue";
import TaxonomyModuleLayout from "./views/TaxonomyModuleLayout.vue";
import ClassGradeModuleLayout from "./views/ClassGradeModuleLayout.vue";
import SensitivityLevelsPage from "./views/SensitivityLevelsPage.vue";
import FieldClassGradeBindingPage from "./views/FieldClassGradeBindingPage.vue";
import SecurityRequirementModuleLayout from "./views/SecurityRequirementModuleLayout.vue";
import SecurityRequirementPage from "./views/SecurityRequirementPage.vue";
import ApprovalManagementPage from "./views/ApprovalManagementPage.vue";
import DocumentResourcePage from "./views/DocumentResourcePage.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/login", component: LoginPage, meta: { title: "欢迎登录" } },
    {
      path: "/",
      component: DashboardPage,
      meta: { title: "控制台" },
      children: [
        {
          path: "",
          name: "dashboard-home",
          component: DashboardHomeView,
          meta: { title: "控制台" }
        },
        {
          path: "user-management",
          name: "dashboard-user-management",
          component: UserManagementPage,
          meta: { title: "用户管理" }
        },
        {
          path: "project-management",
          name: "dashboard-project-management",
          component: ProjectManagementPage,
          meta: { title: "项目管理" }
        },
        {
          path: "submission-task/:taskId",
          name: "dashboard-submission-task-detail",
          component: SubmissionTaskDetailPage,
          meta: { title: "填报任务详情" }
        },
        {
          path: "submission-status",
          name: "dashboard-submission-status",
          component: SubmissionStatusPage,
          meta: { title: "填报情况" }
        },
        {
          path: "submission-task",
          name: "dashboard-submission-task",
          component: SubmissionTaskManagementPage,
          meta: { title: "填报任务管理" }
        },
        {
          path: "field-lifecycle-meta",
          name: "dashboard-field-lifecycle-meta",
          component: FieldLifecycleMetaPage,
          meta: { title: "数据安全生命周期元字段" }
        },
        {
          path: "field-catalog",
          name: "dashboard-field-catalog",
          component: FieldCatalogPage,
          meta: { title: "数据字段" }
        },
        {
          path: "rule-relevance",
          component: RelevanceModuleLayout,
          redirect: { name: "dashboard-rule-relevance-questionnaire" },
          children: [
            {
              path: "questionnaire",
              name: "dashboard-rule-relevance-questionnaire",
              component: RelevanceQuestionnairePage,
              meta: { title: "相关性问卷", relevancePage: "questionnaire" }
            },
            {
              path: "expression",
              name: "dashboard-rule-relevance-standard-expression",
              component: RelevanceStandardExpressionPage,
              meta: { title: "表达式配置和验证", relevancePage: "expression" }
            }
          ]
        },
        {
          path: "rule-relevance-questionnaire",
          redirect: { name: "dashboard-rule-relevance-questionnaire" }
        },
        {
          path: "rule-relevance-standard-predicate",
          redirect: { name: "dashboard-rule-relevance-standard-expression" }
        },
        {
          path: "rule-relevance-standard-expression",
          redirect: { name: "dashboard-rule-relevance-standard-expression" }
        },
        {
          path: "rule-taxonomy",
          component: TaxonomyModuleLayout,
          redirect: { name: "dashboard-rule-taxonomy-levels" },
          children: [
            {
              path: "levels",
              name: "dashboard-rule-taxonomy-levels",
              component: TaxonomyLevelsPage,
              meta: { title: "分类树层级", taxonomyPage: "levels" }
            },
            {
              path: "nodes",
              name: "dashboard-rule-taxonomy-nodes",
              component: TaxonomyNodesPage,
              meta: { title: "分类树节点", taxonomyPage: "nodes" }
            },
            {
              path: "field-classification",
              name: "dashboard-rule-taxonomy-field-classification",
              component: TaxonomyFieldClassificationPage,
              meta: { title: "数据字段分类", taxonomyPage: "fieldClassification" }
            },
            {
              path: "classification-config",
              name: "dashboard-rule-taxonomy-classification-config",
              component: ClassificationConfigPage,
              meta: { title: "分类矩阵与规则", taxonomyPage: "classificationConfig" }
            },
            {
              path: "classification-results",
              name: "dashboard-rule-taxonomy-classification-results",
              component: ClassificationResultsPage,
              meta: { title: "自动分类结果", taxonomyPage: "classificationResults" }
            }
          ]
        },
        { path: "rule-taxonomy-levels", redirect: { name: "dashboard-rule-taxonomy-levels" } },
        { path: "rule-taxonomy-nodes", redirect: { name: "dashboard-rule-taxonomy-nodes" } },
        {
          path: "rule-taxonomy-field-classification",
          redirect: { name: "dashboard-rule-taxonomy-field-classification" }
        },
        {
          path: "rule-taxonomy-classification-config",
          redirect: { name: "dashboard-rule-taxonomy-classification-config" }
        },
        {
          path: "rule-taxonomy-classification-results",
          redirect: { name: "dashboard-rule-taxonomy-classification-results" }
        },
        {
          path: "rule-classification",
          component: ClassGradeModuleLayout,
          redirect: { name: "dashboard-rule-classification-levels" },
          children: [
            {
              path: "levels",
              name: "dashboard-rule-classification-levels",
              component: SensitivityLevelsPage,
              meta: { title: "密级定义", classGradePage: "levels" }
            },
            {
              path: "bindings",
              name: "dashboard-rule-classification-bindings",
              component: FieldClassGradeBindingPage,
              meta: { title: "数据字段绑定", classGradePage: "bindings" }
            }
          ]
        },
        { path: "rule-classification-levels", redirect: { name: "dashboard-rule-classification-levels" } },
        { path: "rule-classification-bindings", redirect: { name: "dashboard-rule-classification-bindings" } },
        {
          path: "rule-security",
          component: SecurityRequirementModuleLayout,
          children: [
            {
              path: "",
              name: "dashboard-rule-security",
              component: SecurityRequirementPage,
              meta: { title: "安全要求" }
            }
          ]
        },
        { path: "rule-security-predicate", redirect: { name: "dashboard-rule-security" } },
        { path: "rule-security-expression", redirect: { name: "dashboard-rule-security" } },
        {
          path: "approval",
          name: "dashboard-approval",
          component: ApprovalManagementPage,
          meta: { title: "审批管理" }
        },
        {
          path: "document-resource",
          name: "dashboard-document-resource",
          component: DocumentResourcePage,
          meta: { title: "文档资源" }
        }
      ]
    }
  ]
});

router.afterEach((to) => {
  const base = "上汽大众研发数据安全治理工作台";
  if (to.path === "/login") {
    document.title = "欢迎登录 — 上汽大众研发数据安全治理系统";
    return;
  }
  const sub = to.meta?.title;
  document.title = sub ? `${sub} — ${base}` : base;
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("dsms_access_token");
  if (to.path !== "/login" && !token) {
    next("/login");
    return;
  }
  if (to.path === "/login" && token) {
    next("/");
    return;
  }
  next();
});

export default router;
