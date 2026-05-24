# DSMS 门户前端 UI 风格指南（固化版）

本文档固化当前 **登录页 + 控制台壳（顶栏 / 侧栏 / 主区）** 的视觉与结构约定，供后续业务页面与路由开发 **直接沿用**。实现细节以代码为准；令牌与全局样式以 `frontend/src/styles/portal-theme.css` 为 **唯一事实来源**，本文只做索引与约束说明。

---

## 1. 必读与文件入口

| 用途 | 路径 |
|------|------|
| 全局样式、设计令牌、顶栏/玻璃/动效/深色覆盖 | `frontend/src/styles/portal-theme.css` |
| 应用入口、EP 深色变量、主题初始化 | `frontend/src/main.js` |
| 主题状态（`html.dark`、`localStorage`） | `frontend/src/composables/useDsmsTheme.js` |
| 顶栏徽标 | `frontend/src/components/PortalBrandLogo.vue` |
| 深/浅切换按钮 | `frontend/src/components/ThemeToggleControl.vue` |
| 控制台壳（布局 + 菜单） | `frontend/src/views/DashboardPage.vue` |
| 登录页 | `frontend/src/views/LoginPage.vue` |
| 路由与 `document.title` | `frontend/src/router.js` |
| 用户管理页（IA / 线框 / 与 API 对齐说明） | `docs/DSMS_USER_MANAGEMENT_UI_SPEC.md` |
| **前端页面对后端依赖（规范 + 索引）** | **`docs/DSMS_FRONTEND_BACKEND_DEPS.md`**、**`docs/frontend-backend-deps/README.md`** |

产品级 API/数据契约仍以 **`docs/DSMS_IMPLEMENTATION_SPEC.md`** 为准；本文仅覆盖 **门户 UI**。

---

## 2. 视觉基调（浅色 / 深色）

- **浅色**：页面底为淡蓝灰（`--dsms-page-bg`），正文为偏蓝深 slate（`--dsms-text`），表面白（`--workspace-surface-2`、`--dsms-aside-surface`）。**Element 主色**在 `:root` 中配置为 **深藏青**（`--el-color-primary` 及 `light-*` 阶梯），主按钮为 **深底白字**，与「接近黑的蓝 + 白」品牌方向一致。
- **深色**：`html.dark` 下重写 `--dsms-*`、`--workspace-*` 及一组 `--el-color-primary*`，并配合 `element-plus/theme-chalk/dark/css-vars.css`。顶栏用户区、登录输入等在 `portal-theme.css` 的 `html.dark` 段内有补充规则。
- **禁止**：在业务页面内 **复制一套** 与 `header.dsms-portal-topbar` 等价的顶栏样式；新壳层页面应 **复用类名与结构**（见下文）。

---

## 3. 设计令牌（摘要）

以下名称在 `portal-theme.css` 的 `:root` 与 `html.dark` 中定义，**业务样式应优先使用变量**，避免硬编码色值。

- **动效**：`--dsms-ease-standard`、`--dsms-ease-out-expo`、`--dsms-duration-*`；尊重 `prefers-reduced-motion: reduce` 时 `:root` 将时长置 `0ms`。
- **页面与文字**：`--dsms-page-bg`、`--dsms-text`、`--dsms-text-secondary`。
- **工作区表面与边框**：`--workspace-surface`、`--workspace-surface-2`、`--workspace-border`、`--dsms-aside-surface`（侧栏与菜单背景应对齐）。
- **毛玻璃卡片**：`--dsms-glass-bg`、`--dsms-glass-bg-strong`、`--dsms-glass-border-subtle`、`--dsms-glass-shadow`、`--dsms-glass-blur*`。
- **焦点**：`--dsms-focus-ring`（浅色/深色分别覆盖），用于输入框 inset 焦点等。

---

## 4. 布局骨架（控制台内新业务页）

后续从侧栏进入的 **具体业务页**，建议在 **`DashboardPage` 的 `el-main` 内** 渲染（路由 `component` 仍为 `DashboardPage`，由内部 `<router-view>` 切换子路由；**若当前仓库尚未嵌套子路由**，则新增路由时保持 **同一壳**：顶栏 + `el-container direction="horizontal"` + 侧栏 + 主区）。

**固定结构要点**（与 `DashboardPage.vue` 一致）：

1. 根：`div.dsms-dashboard-page`（`min-height: 100vh`，列方向 flex）。
2. 顶栏：`header.dsms-portal-topbar`（**必须** `flex-direction: row`；已用类型选择器提高优先级，避免被压成纵向）。
3. 主体：`el-container.dashboard-body` **`direction="horizontal"`**，避免 EP 误判为纵向。
4. 侧栏：`el-aside.dashboard-aside`，宽度与 `el-menu` 折叠状态联动；背景用 `var(--dsms-aside-surface)`。
5. 主区：`el-main.dashboard-main`，内边距与滚动与现有一致；业务内容放在 **白/玻璃卡片**（`dsms-glass-panel`）内。

**登录页**：`div.login-page` + 同顶栏类名 + `main.login-main` + `el-card.login-card`，与控制台 **共享** `portal-theme` 顶栏与令牌。

---

## 5. 顶栏（`dsms-portal-topbar`）

- **结构**：`header.dsms-portal-topbar` → `div.dsms-portal-topbar__brand`（`PortalBrandLogo` + `h1.dsms-portal-title` 或标题文案）+ `div.dsms-portal-topbar__actions`（项目、用户、**`ThemeToggleControl`** 等）。
- **高度**：当前 **56px**（与 `portal-theme` 一致）；勿在页面内再写一套高度/边框/背景。
- **窄屏**：顶栏已 `flex-wrap` + `row-gap`，操作区可换行。
- **项目按钮**：需提供清晰 **`aria-label`**（参见 `DashboardPage` 中 `tenantMenuAriaLabel`）。

---

## 6. 侧栏与菜单（Element Plus）

- `el-menu` 的 `background-color` / `text-color` / `active-text-color` 应随 **`useDsmsTheme().isDark`** 计算，与 `--dsms-aside-surface` 一致，避免深色下仍为浅色写死值。
- 菜单项图标：同一业务含义的条目应使用 **相同图标**（例如两处「谓词配置 / 表达式配置和验证」已对齐）。
- 折叠：`collapse-transition`、侧栏 `width` 过渡与 `MENU_COLLAPSE_LABEL_MS` 等逻辑以 `DashboardPage` 为准；勿在侧栏容器上使用 `backdrop-filter` 与宽度动画叠加以防卡顿。

---

## 7. 业务区卡片与内容

- **玻璃面板**：大块内容区使用 class **`dsms-glass-panel`**（可与 `dsms-animate-stagger-*` 组合做分层入场）。
- **主区内边距**：与 `dashboard-main` 一致（当前 `padding: 28px`），新业务避免无故缩小或取消。
- **列表与分页**：见项目规则「一致性」：`skip`/`limit`、`total`/`items`，筛选变更重置 `skip`。

---

## 8. Element Plus 与弹层

- 全站已 `use(ElementPlus)`；主色由 `:root` / `html.dark` 覆盖，**勿**在单页再引入一套覆盖主色的 `dark` 样式文件。
- 对话框：`AccountSettingsDialog` 等与 `portal-theme` 中 `.el-dialog` 规则一致；表单按钮以 `type="primary"` 为主。

---

## 9. 主题切换

- **`ThemeToggleControl`**：顶栏右侧；`aria-pressed` 与当前深/浅同步。
- **持久化**：`localStorage` 键 **`dsms_portal_color_scheme`**，值 `light` / `dark`；**`initDsmsThemeBeforeMount()`** 须在 `createApp` 之前执行（见 `main.js`），减轻首屏闪色。

---

## 10. 路由与 `document.title`

- 在 `router.js` 的 `afterEach` 中维护 **`document.title`**；`meta.title` 与页面语义一致（如控制台为「控制台」）。
- 新路由：**`meta.title`** 必填；业务区可见 **`h1`/`h2`** 与标题语义一致（WCAG 2.4.2）。

---

## 11. 可访问性与焦点

- 顶栏产品名：`h1.dsms-portal-title`（控制台）；登录页卡片内主标题用 **`h1.login-title`**。
- 跳过链接：登录页保留 **`login-skip-link`** 与 `#login-main`。
- 焦点环：输入框等优先使用 **`--dsms-focus-ring`** 或与 `var(--el-color-primary)` 一致的 outline（见登录页、用户触发器）。

---

## 12. 动效

- 路由：`App.vue` 中 `transition name="dsms-route"`。
- 分层入场：`dsms-animate-stagger-0` … `3`、`dsms-animate-content-in`；遵守 `prefers-reduced-motion`。

---

## 13. 新页面 / 新菜单自检清单

- [ ] 未复制顶栏/侧栏 CSS；复用 `dsms-portal-*` / `dashboard-*` 或嵌套于现有壳。
- [ ] 颜色使用 `portal-theme` 变量或 EP 语义色，避免魔法数（除 EP 组件必要属性外）。
- [ ] 已配置 `meta.title` 与 `document.title`。
- [ ] 深色下关键控件对比度可接受；必要时在 `html.dark` 段追加 **页面级** 补充选择器（与登录输入框写法一致）。
- [ ] `pnpm run build` 通过。

---

## 14. 变更流程

若需调整 **全站** 视觉（令牌、顶栏、深色表），应 **优先改 `portal-theme.css`**，并同步更新 **本指南与规格** 中相关描述，避免各页面漂移。
