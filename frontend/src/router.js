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

const router = createRouter({
  history: createWebHistory(),
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
