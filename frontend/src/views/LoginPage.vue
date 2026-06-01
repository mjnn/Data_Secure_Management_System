<template>
  <div class="login-page">
    <a href="#login-main" class="login-skip-link">跳到登录表单</a>
    <header class="dsms-portal-topbar">
      <div class="dsms-portal-topbar__brand">
        <PortalBrandLogo />
        <span class="dsms-portal-title">上汽大众研发数据安全治理系统</span>
      </div>
      <div class="dsms-portal-topbar__actions">
        <ThemeToggleControl />
      </div>
    </header>
    <main id="login-main" class="login-main" tabindex="-1">
      <el-card class="login-card dsms-glass-panel dsms-animate-stagger-0" shadow="never">
        <template #header>
          <h1 class="login-title dsms-animate-stagger-1">欢迎登录</h1>
        </template>

        <el-form
          class="login-form dsms-animate-stagger-2"
          label-position="top"
          :model="form"
          @submit.prevent="onSubmit"
          :aria-describedby="loginFormDescribedBy"
        >
          <el-form-item label="用户名" required>
            <el-input
              id="login-username"
              v-model="form.username"
              name="username"
              autocomplete="username"
              maxlength="128"
              clearable
              aria-required="true"
              @keyup.enter="onSubmit"
            />
          </el-form-item>
          <el-form-item label="密码" required>
            <el-input
              id="login-password"
              v-model="form.password"
              name="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              maxlength="256"
              aria-required="true"
              aria-describedby="login-help"
              @keyup.enter="onSubmit"
            >
              <template #suffix>
                <button
                  type="button"
                  class="login-password-toggle"
                  :aria-pressed="showPassword ? 'true' : 'false'"
                  :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                  @click="showPassword = !showPassword"
                >
                  <!-- 图标仅装饰，名称由 aria-label 提供 -->
                  <svg
                    v-if="!showPassword"
                    class="login-password-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                    focusable="false"
                  >
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg
                    v-else
                    class="login-password-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                    focusable="false"
                  >
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                </button>
              </template>
            </el-input>
          </el-form-item>

          <div
            id="login-status"
            role="status"
            aria-live="polite"
            aria-atomic="true"
            aria-label="登录结果"
            class="login-status"
            :class="{ 'login-status--active': !!statusMessage }"
          >
            <span v-if="statusMessage">{{ statusMessage }}</span>
          </div>

          <el-button
            type="primary"
            native-type="submit"
            class="login-submit"
            :loading="loading"
            :aria-busy="loading ? 'true' : 'false'"
          >
            登录
          </el-button>
        </el-form>

        <section
          v-if="isDev"
          id="login-dev-accounts"
          class="login-dev-accounts"
          aria-label="开发阶段测试账号"
        >
          <h2 class="login-dev-accounts__title">开发阶段测试账号</h2>
          <p class="login-dev-accounts__lead">
            与后端默认种子一致；密码可被环境变量覆盖。点击下方可将账号填入上方表单。
          </p>
          <ul class="login-dev-accounts__list">
            <li v-for="acc in devTestAccounts" :key="acc.username" class="login-dev-accounts__row">
              <div class="login-dev-accounts__meta">
                <span class="login-dev-accounts__role">{{ acc.roleLabel }}</span>
                <code class="login-dev-accounts__creds" translate="no">{{ acc.username }}</code>
                <span class="login-dev-accounts__sep" aria-hidden="true">/</span>
                <code class="login-dev-accounts__creds" translate="no">{{ acc.password }}</code>
              </div>
              <el-button type="primary" link size="small" @click="fillDevAccount(acc)">
                填入表单
              </el-button>
            </li>
          </ul>
        </section>

        <p id="login-help" class="login-help">
          默认管理员账号由服务端环境变量
          <span class="login-help-code" translate="no">FIRST_SUPERUSER</span>
          与
          <span class="login-help-code" translate="no">FIRST_SUPERUSER_PASSWORD</span>
          配置；若登录失败请核对部署环境是否与文档一致。
        </p>
      </el-card>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import PortalBrandLogo from "../components/PortalBrandLogo.vue";
import ThemeToggleControl from "../components/ThemeToggleControl.vue";
import api from "../api";
import { clearCurrentUser } from "../composables/useCurrentUser.js";
import { resetPortalTenantContext } from "../composables/usePortalTenantContext.js";

const router = useRouter();
const loading = ref(false);
const showPassword = ref(false);
const statusMessage = ref("");
const isDev = import.meta.env.DEV;

const form = reactive({
  username: isDev ? "admin" : "",
  password: isDev ? "Admin123456" : ""
});

const devTestAccounts = [
  {
    roleLabel: "系统管理员",
    username: "admin",
    password: "Admin123456"
  },
  {
    roleLabel: "数据安全 FO（测试）",
    username: "security_fo",
    password: "SecurityFo123456"
  },
  {
    roleLabel: "功能 FO（测试）",
    username: "function_fo",
    password: "FunctionFo123456"
  }
];

const loginFormDescribedBy = computed(() =>
  isDev ? "login-dev-accounts login-help" : "login-help"
);

const fillDevAccount = (acc) => {
  form.username = acc.username;
  form.password = acc.password;
};

const onSubmit = async () => {
  statusMessage.value = "";
  loading.value = true;
  try {
    const { data } = await api.post("/api/v1/auth/login", form);
    clearCurrentUser();
    resetPortalTenantContext();
    localStorage.setItem("dsms_access_token", data.access_token);
    localStorage.setItem("dsms_refresh_token", data.refresh_token);
    statusMessage.value = "登录成功，正在进入系统。";
    ElMessage.success("登录成功");
    router.push("/");
  } catch (error) {
    const detail = error.response?.data?.detail;
    const msg = typeof detail === "string" ? detail : "登录失败，请检查用户名与密码。";
    statusMessage.value = msg;
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  box-sizing: border-box;
  background: transparent;
  color: var(--dsms-text);
}

.login-skip-link {
  position: absolute;
  left: -9999px;
  top: auto;
  width: 1px;
  height: 1px;
  overflow: hidden;
  z-index: 1000;
  padding: 10px 14px;
  background: var(--workspace-surface-2);
  color: var(--dsms-text);
  border: 2px solid var(--dsms-text);
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
}

.login-skip-link:focus {
  left: 16px;
  top: 16px;
  width: auto;
  height: auto;
  overflow: visible;
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

.login-main {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  width: 100%;
  padding: 32px 16px 48px;
  box-sizing: border-box;
  outline: none;
}

.login-main:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 4px;
  border-radius: 8px;
}

.login-card {
  width: min(100%, 400px);
  border: none !important;
  box-shadow: var(--dsms-glass-shadow) !important;
}

.login-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--dsms-glass-border-subtle);
  background: transparent;
}

.login-card :deep(.el-card__body) {
  background: transparent;
}

.login-title {
  margin: 0;
  font-size: clamp(0.95rem, 2.8vw, 1.125rem);
  font-weight: 600;
  line-height: 1.45;
  color: var(--dsms-text);
  text-wrap: balance;
}

.login-form :deep(.el-form-item__label) {
  color: var(--dsms-text-secondary);
  font-weight: 600;
}

.login-form :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 0 0 1px var(--dsms-glass-border-subtle) inset;
  transition:
    box-shadow var(--dsms-duration-short) var(--dsms-ease-standard),
    background-color var(--dsms-duration-short) var(--dsms-ease-standard);
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--el-color-primary-light-8) inset;
  background-color: rgba(255, 255, 255, 0.82);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--dsms-focus-ring) inset;
  background-color: rgba(255, 255, 255, 0.92);
}

.login-form :deep(.el-input__inner) {
  color: var(--dsms-text);
}

.login-form :deep(.el-button:focus-visible) {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

.login-password-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin: 0 2px 0 0;
  padding: 0;
  color: var(--dsms-text-secondary);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.login-password-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  pointer-events: none;
}

.login-password-toggle:hover {
  color: var(--dsms-text);
  background: var(--workspace-surface);
}

.login-password-toggle:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

.login-status {
  margin: 4px 0 12px;
  min-height: 0;
  font-size: 0.875rem;
}

.login-status--active {
  min-height: 1.5rem;
  font-weight: 600;
  color: var(--el-color-danger);
}

.login-submit {
  width: 100%;
  margin-top: 4px;
}

.login-dev-accounts {
  margin: 20px 0 0;
  padding: 14px 16px;
  border: 1px solid var(--workspace-border);
  border-radius: 10px;
  background: var(--workspace-surface);
  box-sizing: border-box;
}

.login-dev-accounts__title {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--dsms-text);
  line-height: 1.35;
}

.login-dev-accounts__lead {
  margin: 0 0 12px;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.login-dev-accounts__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.login-dev-accounts__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.login-dev-accounts__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 0.8125rem;
}

.login-dev-accounts__role {
  flex-shrink: 0;
  font-weight: 600;
  color: var(--dsms-text-secondary);
}

.login-dev-accounts__sep {
  color: var(--dsms-text-secondary);
  user-select: none;
}

.login-dev-accounts__creds {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--workspace-surface-2);
  color: var(--dsms-text);
  word-break: break-all;
}

.login-help {
  margin: 16px 0 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.login-help-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.8125rem;
  color: var(--dsms-text);
  background: var(--workspace-surface);
  padding: 1px 6px;
  border-radius: 4px;
  word-break: break-all;
}

@media (prefers-reduced-motion: reduce) {
  .login-form :deep(.el-input__wrapper),
  .login-submit {
    transition: none !important;
  }
}
</style>
