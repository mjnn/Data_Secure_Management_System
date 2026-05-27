# 安全要求 — 后端依赖清单

## 1. 前端入口

- **路由**：`/rule-security`，`name`: `dashboard-rule-security`
- **页面**：`SecurityRequirementPage.vue` — **触发规则列表**（非「为字段填写要求」）
- **组件**：`SecurityLogicExprBuilder.vue`（触发条件逻辑树）
- **数据**：`securityRequirementRulesMock.js`（`dsms_mock_security_requirement_rules_v1`）、`securityLogicTree.js`、`securityConditionCatalog.js`
- **权限**：`system_admin` / `security_fo`

## 2. 产品语义（Mock）

每条**规则**包含：

| 部分 | 含义 |
|------|------|
| **触发条件** | 仅 **密级 / 分类（`-` 路径）/ 其他生命周期元字段** 取值（支持括号、且/或）；**不在条件中选数据字段**（分类/密级来自前两步，求值时选字段） |
| **执行的安全要求** | 富文本 `content_html`（占位）；结构化 `check_kind` / `check_json` 待联调 |

试算：选数据字段 → 列出条件中含该字段的规则 → 按主数据判断**是否触发** → 展示将执行的检查说明。

## 3. 待对接 API

| 能力 | 路径 | 说明 |
|------|------|------|
| 规则 CRUD | `/fields/security-requirements` 或独立规则资源（以定稿为准） | 需承载 `trigger` 表达式 + `check_kind` / `check_json` |
| 求值 | `POST …/fields/security-requirements/evaluate` | `field-security-requirements-eval` |

## 4. 与规格的差异

- 触发条件树为前端 Mock，未映射后端 DSL。
- 规则与 `field_catalog_entry_id` 的绑定策略（一条规则是否可作用于多字段）待产品定稿。

## 5. 联调检查清单

- [ ] 触发成立时写入/执行的要求与 `check_json` 一致
- [ ] 密级阶梯（D6）与 `min_grade` 求值
- [ ] 403 与中文 `detail`
