# DSMS — 数据安全治理独立系统实施规格（v1）

> **DSMS**：Data Secure Management System（中文名：**数据安全治理独立系统**）。  
> 本文档从零描述本仓库应具有的行为与约束；下文称 **「本规格」「本文档」** 均指本文件。

---

## 前言：本产品需要解决什么问题

**DSMS 是一个给企业或组织内部使用的 Web 应用软件**，用来支撑 **「数据字段与数据分类分级相关的治理工作」**。实现者若没有接触过类似系统，可把 DSMS 理解为：

- **多项目**：不同客户或组织在同一套部署里的数据互相隔离（用 **项目** 区分）。
- **项目空间**：在单个项目之下，可以再划分多个 **空间**（例如按产品线、项目组），问卷、字段主表、分类树等业务数据都挂在某一空间之下。
- **典型工作流片段**（能力分阶段交付，见 §11）：
  1. 管理员维护 **问卷题目**、**相关性判定规则**；业务用户在某个空间内填写 **相关性判定**，判断某业务功能是否与数据字段相关。
  2. 维护 **填报表单字段配置**（可配置字段类型与校验）；维护 **数据字段主表**，处理 **字段新增申请**与 **业务功能选项** 的申请与审核。
  3. 用户对具体业务功能提交 **字段填报**，负责人 **审批**；可 **导出** 填报数据。
  4. （后续阶段）维护 **分类树**，配置 **分类分级规则 / 矩阵**，对主表字段做自动或人工的分类分级与安全要求描述、求值、审计与导出。

**本软件不包含**：多工具应用商店、「工具插件」宿主、或对任何外部商业产品的集成（除非你们在其它文档中单独立项）。

---

## 文档契约（必读：不预设读者背景）

以下内容 **全部为硬性约定**，避免出现「不言而喻」或「和你们之前聊过的一样」之类依赖：

1. **未在本规格正文或附录中写明的字段名、枚举值、业务流程，实现者不得在未经产品负责人确认的情况下自行发明**。若为实现所必需而规格未写明，须在变更说明或 PR 中显式增补本规格后再实现。
2. **本文不向读者假设**：曾参与过 MOS、工具箱、或其它代码仓库；亦不假设读者理解任何内部缩写（除本文已展开写出的 DSMS）。
3. 文中 **「项目」「项目空间」「tenant_id」「behavior_key」** 等用语，均以 **本文 §3、§4、附录 A** 的定义与表格为准。
4. **REST 路径前缀**：所有业务接口使用 **`/api/v1/dsms/`**（缩写 DSMS）；认证接口使用 **`/api/v1/auth/`**。不得混用旧的 `dsg` 前缀。

---

## 0. 目标与边界

### 0.1 交付形态

- 单仓：**后端**（FastAPI）+ **前端**（Vue 3 + Vite + Element Plus）+ **`docs/`**。
- **数据库**：仅 **SQLite**（本文档不包含 PostgreSQL 迁移、双数据源或兼容层要求）。
- **部署**：可单机文件库 `sqlite:///...`；备份方式即 **数据库文件拷贝**。

### 0.2 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python 3.11+，FastAPI，SQLModel，Alembic（或等价迁移工具），python-jose（JWT），passlib（bcrypt） |
| 前端 | Vue 3，Vite，Element Plus，pnpm |
| API 风格 | REST，JSON；上传使用 `multipart/form-data` |

**前端门户 UI（壳层 / 深浅色 / 令牌）**：以 **`docs/DSMS_PORTAL_UI_GUIDE.md`** 为固化说明，与 **`frontend/src/styles/portal-theme.css`** 保持一致；新页面与菜单开发须沿用该指南，避免另起一套视觉。

### 0.3 核心产品规则

- **多项目**：任一业务数据归属某一个 **`tenant`（项目）**；每一个 **项目空间** `project_space` 必须属于一个项目。所有业务持久化数据中须带 **`tenant_id`**，并与该行的 `project_space.tenant_id`（若存在）保持一致。
- **业务 API 路径前缀**：一律为 **`/api/v1/dsms/`**。
- **认证 API 路径前缀**：**`/api/v1/auth/`**，与业务路由分离。
- **列表**：请求参数 **`skip`、`limit`**；响应 **`total`、`items`**。默认 **`limit=20`**，允许的 **`limit` 最大值为 500**。
- **错误信息**：HTTP 响应中面向使用者的 **`detail` 或 `message` 使用简体中文**（协议层面的字段名可保留英文）。
- **审计或使用记录**：当需要记录「用户做了什么」，应写入 **`behavior_key`**：**业务类**键必须与 **附录 A** 中的 `key` **逐字符相同**；展示用中文使用附录 A 的 `label`。**平台 IAM 类**键见 §8。

---

## 1. 仓库结构建议

```
/backend
  app/
    main.py
    api/v1/
    models/
    services/
  alembic/          # 可选
/frontend
  src/
docs/
  DSMS_IMPLEMENTATION_SPEC.md
  DSMS_PORTAL_UI_GUIDE.md
  DSMS_FRONTEND_BACKEND_DEPS.md
  frontend-backend-deps/
    README.md
```

---

## 2. 环境变量

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | JWT 签名密钥 |
| `ALGORITHM` | 默认填写 `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 例如 `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 例如 `7` |
| `FIRST_SUPERUSER` | 首次初始化时创建的超级管理员登录名 |
| `FIRST_SUPERUSER_PASSWORD` | 上述账号的初始密码 |
| `DATABASE_URL` | 例如 `sqlite:///./dsms.db` |
| `BACKEND_CORS_ORIGINS` | JSON 数组字符串，例如 `["http://localhost:5173"]` |
|（可选）| `DSMS_INITIAL_PASSWORD_POLICY` | Excel 导入新用户时的初始密码生成规则编码，需在代码或 README 中列出合法取值 |
|（可选）| `TENANT_ADMIN_USER_DIRECTORY_SCOPE` | **仅允许取值 `all`**；表示项目管理员可查全平台用户目录（§6.2）；若未设置则由代码默认等价于 `all` |

**SQLite**：建议启用 **WAL**；避免单次请求内过长事务。

---

## 3. 身份、角色与项目治理

### 3.1 平台级

- **`super_admin`**：表中字段 **`user.is_superuser == True`**。系统初始化时至少存在一个该账号。**权限范围以本文 §6 / §8 中出现的接口为准**。
- **`tenant_creator`**：**仅当**用户 ID 记录在表 **`tenant_creator_allowlist`** 中时，该用户具备「创建新项目」的权限。**只有** `super_admin` 可以通过接口 **`PUT`** 全量维护该名单。用户创建项目成功后，必须在同一事务内为自己写入一条 **`tenant_membership`，且 `role=tenant_admin`**。同一自然人账号可以成为多个项目的首任 **`tenant_admin`**。

### 3.2 项目内

- **`tenant_admin`**：在某项目的成员关系中 **`role=tenant_admin`**。可以管理该项目内的配置类、审核类、删除类操作（精确到路由的权限矩阵由实现代码结合本文 §7 写清）。
- **`tenant_member`**：在某项目的成员关系中 **`role=tenant_member`**。一般仅能提交与自己相关的单据、读取被授权读的列表。**具体放行规则**：若 §7 未写明某方法是仅 `tenant_admin` 还是也允许 `tenant_member`，则须在实现时用代码注释或在 OpenAPI `description` 中写一行说明，并于后续修订本文档对齐。

### 3.3 用户入项目流程（显式步骤）

1. **`super_admin`** 使用 **Excel 上传接口**批量创建全局用户账号（§6.1）；此时用户 **尚不属于任何项目**。
2. **`tenant_admin`** 调用 **`GET /api/v1/dsms/users`** 检索候选人，再调用 **`members/batch`**，在 body 中指明 **`user_ids`**，默认写入 **`tenant_member`**。
3. 将 **`tenant_member` 升为 `tenant_admin`**：**不得**仅靠 `members/batch` 批量赋 `tenant_admin`；必须使用 **`PUT /tenants/{tenant_id}/members/{user_id}/role`**。是否允许项目内的 `tenant_admin` 升职他人：**须在代码里选一个固定策略**，并在 OpenAPI 或 README 写清（仅允许 `super_admin` / 或允许同项目 `tenant_admin`）。

### 3.4 全局用户目录策略

本文档规定：**项目管理员在选人入项目时，可见「全平台已存在用户」的目录条目**（字段白名单见 §6.2）。环境变量 **`TENANT_ADMIN_USER_DIRECTORY_SCOPE` 只允许 `all`**；若省略该变量，实现应默认与 `all` 行为一致。**不得**在未修改本文档的情况下实现第二种可见性模式。

---

## 4. 数据模型

### 4.1 用户与平台角色（精简）

**`user`**

- `id`, `username`（唯一索引）, `email`（唯一索引）, `hashed_password`
- `full_name`, `department`（均可空）
- `is_active`, `is_superuser`, `is_approved`
- `avatar_url`（可选）
- `created_at`, `updated_at`

**`role` / `user_role`（可选）**：若需平台级标记，可自行定义枚举；**须在 README 列出种子角色**。

DSMS **不包含**「工具目录」「按工具授权」等多应用宿主表。

### 4.2 项目

**`tenant`**：`id`, `name`, `slug`（可选、唯一）, `is_archived`, `created_at`，等。

**`tenant_creator_allowlist`**：至少包含 **`user_id`**（主键或唯一约束）。

**`tenant_membership`**

- `tenant_id`, `user_id`, `role`（取值为字面量 **`tenant_admin`** 或 **`tenant_member`**）
- **唯一约束**：`(tenant_id, user_id)`

**`audit_log`（推荐实现）**

- `id`, `tenant_id`（平台级操作可为空）, `user_id`
- `behavior_key`, `label_snapshot`, `detail_json`, `created_at`

### 4.3 业务领域实体（均含 `tenant_id`）

以下实体均需 **`tenant_id` 外键**；绝大部分同时含 **`project_space_id`**。**唯一索引**必须由 **`tenant_id` 与业务键**组合（或与 `project_space_id` 组合），禁止仅按「空间内唯一」却漏掉项目维度。

| 领域 | 实体（表名可自行 snake_case） | 功能摘要 |
|------|-------------------------------|----------|
| 空间 | `project_space` | 项目下的逻辑分区；含 `space_key`, `name` 等 |
| 问卷 | `questionnaire_question` | 空间中问卷题目定义 |
| 相关性 | `relevance_rule`, `assessment_submission`, `assessment_answer` | 相关性规则与用户填报工单 |
| 动态表单 | `lifecycle_field_definition`, `lifecycle_field_config` | 可配置字段与校验规则 |
| 主数据 | `field_catalog_entry`, `field_catalog_value` | 数据字段主表及动态扩展列值 |
| 申请 | `field_request`, `business_function_option_request` | 字段与选项的申请与审批 |
| 填报 | `field_usage_report`, `field_usage_report_item` | 与问卷关联的字段填报单及行项目 |
| 分类树 | `taxonomy_node` | 树形分类节点 |
| 治理日志 | `governance_change_log` | 配置变更履历（主要在 Phase 3 暴露列表） |
| 分类分级 | `classification_matrix`, `classification_rule`, `classification_result`, `classification_audit_log` | Phase 2 |
| 密级与安全 | `field_class_grade`, `field_security_requirement` | Phase 2 |

字段级别的列名、长度、默认值：若本篇未逐列列出，**实现者应在 SQLModel/Alembic 模型文件内自洽定义**，且满足上表语义。

### 4.4 动态表单（在本仓库实现）

要求在 **后端** 提供可复用的服务层：**字段定义读写、取值校验、`field_catalog_value` 存取**。在 **前端** 提供：**`FieldConfigManagerTable`**（管理端表格）、**`DynamicFieldInputs`**（填报渲染）。两端共享的字段类型枚举、JSON 结构与校验规则须在 **单独的 TypeScript/Python 契约**（或 OpenAPI Schema）里各写一份并保持同步。**不得**在未定义契约的情况下在路由里手写大段重复的字段校验分支。

---

## 5. HTTP API — 认证与用户资料

**Access Token / Refresh Token** 使用 JWT；密码存储使用 bcrypt。以下为 **第一期必须实现** 的接口集合：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | Body：`username` + `password`；返回 `access_token`, `refresh_token`, `token_type` |
| POST | `/api/v1/auth/refresh` | Body：`refresh_token` |
| GET | `/api/v1/users/me` | Header：`Authorization: Bearer <access>` |
| PUT | `/api/v1/users/me` | Body 只允许修改在白名单内的资料字段（实现白名单：`email`、`full_name`、`department`；`email` 变更须做唯一性校验，冲突返回 409） |
| POST | `/api/v1/users/me/password` | Body：`old_password` + `new_password`。校验原密码后修改自身密码；新密码 8–128 位，不得与原密码相同；成功返回 204 |

是否开放自助注册 **`POST /api/v1/auth/register`**：默认为 **不推荐**；若实现，须在 README 说明如何关闭。

---

## 6. HTTP API — 平台与项目（`/api/v1/dsms/`）

### 6.1 平台：项目创建权 + Excel 用户

| 方法 | 路径 | 权限 |
|------|------|------|
| GET | `/api/v1/dsms/platform/tenant-creators` | `super_admin` |
| PUT | `/api/v1/dsms/platform/tenant-creators` | `super_admin`，body：`{ "user_ids": number[] }`，全量替换 |
| POST | `/api/v1/dsms/platform/users/import-excel` | `super_admin`，`multipart/form-data`，字段名 `file` |
| GET | `/api/v1/dsms/platform/users/import-excel/template` | `super_admin` |

**Excel 导入规则**

- **表头**：必须包含 **邮箱**（列名可为 `email` 或 **`邮箱`**）。可选列：**用户名**、**姓名**、**部门**（中英文列名等价关系由代码内显式映射表列出）。
- **行级错误**：单行失败应记入响应中的 **`skipped_items`**，且不中断其它合法行的创建（除非你们选择全盘回滚——若选择回滚须在 README **明确写明**）。
- **响应**：`total_rows`, `created_count`, `skipped_count`, `created_users[]`（仅 §6.2 白名单字段）, `skipped_items[]`（含 `row`, `email`, `reason` 中文）。

### 6.2 全局用户目录（选人）

**GET `/api/v1/dsms/users`**

- **权限**：`super_admin` **或** 在 **至少一个** 项目中担任 **`tenant_admin`** 的用户。
- **Query**：`skip`, `limit`, `q`（对 `username` / `email` / `full_name` 子串过滤）, `is_active`, `membership_preview_tenant_id`, `only_unassigned_to_tenant`
- **响应每一项仅允许**：`id`, `username`, `email`, `full_name`, `department`, `is_active`, `created_at`；若带 `membership_preview_tenant_id`，附加 `in_tenant`, `tenant_role`。

### 6.3 项目与成员

前缀：**`/api/v1/dsms/tenants`**

| 方法 | 路径 |
|------|------|
| POST | `/` |
| GET | `/{tenant_id}` |
| PATCH | `/{tenant_id}` |
| POST | `/{tenant_id}/seeds/import` |
| GET | `/{tenant_id}/members` |
| POST | `/{tenant_id}/members/batch` |
| POST | `/{tenant_id}/members/batch-remove` |
| PUT | `/{tenant_id}/members/{user_id}/role` |

**批量加入 body**：`{ "user_ids": number[], "role": "tenant_member" }`。已存在的关系应 **跳过并记录**，不当作 500。  
**批量移除**：移除后仍需保证该项目 **`tenant_admin` 数量 ≥ 1**（或由 `super_admin` 特例打破——若允许特例须在 README 写明）。

---

## 7. HTTP API — 业务（分期）

### 路径前缀写法

**项目级**：`/api/v1/dsms/tenants/{tenant_id}`  

**空间列表**：`/api/v1/dsms/tenants/{tenant_id}/spaces`

**单个空间内的前缀**：`/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}`

下文表中「 `{空间内前缀}` 」指上述单行完整前缀。

每一条请求必须在服务端验证：**JWT 对应的用户是否在 `tenant_id` 下有 `tenant_membership`**（`super_admin` 是否可省略 membership：**须二选一并文档化**，建议 super_admin 仍写一条「平台项目」或使用专门分支逻辑并在代码注释说明）。

### 7.1 Phase 1 — MVP

| 附录 A behavior_key | 方法 | URL |
|---------------------|------|-----|
| `project-spaces`（列表） | GET | `/api/v1/dsms/tenants/{tenant_id}/spaces` |
| `project-spaces` | POST | 同上前缀 `/spaces` |
| `project-spaces` | PUT | 同上 `/spaces` 或 `/spaces/{space_id}`（**实现时选一种，不得混用两套**） |
| `project-spaces/delete` | POST | `/api/v1/dsms/tenants/{tenant_id}/spaces/delete` |
| `suggest-identifier-key` | POST | `{空间内前缀}/identifiers/suggest` |
| `questionnaire/questions` | GET, POST, PUT | `{空间内前缀}/questionnaires/questions` |
| `questionnaire/questions/delete` | POST | `{空间内前缀}/questionnaires/questions/delete` |
| `relevance-rule` | GET, PUT | `{空间内前缀}/relevance/rules` |
| `relevance-assessments` | POST, GET | `{空间内前缀}/relevance/assessments`、`.../assessments/{submission_id}` |
| `lifecycle-field-config` | GET, POST, PUT, DELETE | `{空间内前缀}/forms/lifecycle-field-config` |
| `field-catalog` | GET, POST | `{空间内前缀}/field-catalog` |
| `field-catalog` | PUT | `{空间内前缀}/field-catalog/{entry_id}` |
| （批量导入） | POST | `{空间内前缀}/field-catalog/batch-import` |
| （选项快照） | GET | `{空间内前缀}/field-catalog/value-options` |
| `field-requests` | POST, GET | `{空间内前缀}/field-requests` |
| `field-requests` | PUT | `{空间内前缀}/field-requests/{request_id}/review` |
| `business-function-options` | GET | `{空间内前缀}/business-functions/options` |
| `business-function-option-requests` | POST, GET, PUT | `{空间内前缀}/business-functions/option-requests`（含审核子路径由 OpenAPI 列出） |
| `field-usage-reports` | POST, GET | `{空间内前缀}/field-usage-reports` |
| `field-usage-reports` | GET | `{空间内前缀}/field-usage-reports/export` |
| `field-usage-reports` | POST | `{空间内前缀}/field-usage-reports/{report_id}/review` |
| （合并工单列表） | GET | `{空间内前缀}/work-orders` |
| `taxonomy-nodes` | GET, POST | `{空间内前缀}/taxonomy/nodes` |
| `taxonomy-nodes`（更新） | PUT | `{空间内前缀}/taxonomy/nodes/{node_id}` |
| `taxonomy-nodes/delete` | DELETE | `{空间内前缀}/taxonomy/nodes/{node_id}` |

凡标注「分页」的 **GET**：须支持 **`skip`/`limit`**，响应 **`total`/`items`**。

### 7.2 Phase 2 — 分类分级与安全要求

以下 **路径后缀**均接在 **`{空间内前缀}`** 之后。

| behavior_key | 方法 | 后缀 |
|--------------|------|------|
| `classification-matrix` | GET | `/classification/matrix` |
| （矩阵批量导入） | POST | `/classification/matrix/batch-import` |
| `classification-matrix` | POST, PUT | `/classification/matrix` |
| `classification-matrix/delete` | DELETE | `/classification/matrix/{matrix_id}` |
| `classification-rules` | GET, POST, PUT | `/classification/rules` |
| `classification-rules/delete` | DELETE | `/classification/rules/{rule_id}` |
| `classification-recompute` | POST | `/classification/recompute` |
| `classification-results` | GET | `/classification/results` |
| `classification-manual-override` | PUT | `/classification/results/{result_id}/manual` |
| `classification-revert-auto` | POST | `/classification/results/{result_id}/revert-auto` |
| `classification-audit` | GET | `/classification/audit` |
| `classification-export` | GET | `/classification/export` |
| `field-class-grade` | GET, PUT | `/fields/class-grade` |
| （删除绑定） | DELETE | `/fields/class-grade/{catalog_entry_id}` |
| `field-security-requirements` | GET, POST | `/fields/security-requirements` |
| `field-security-requirements` | PUT | `/fields/security-requirements/{requirement_id}` |
| `field-security-requirements/delete` | DELETE | `/fields/security-requirements/{requirement_id}` |
| `field-security-requirements-eval` | POST | `/fields/security-requirements/evaluate` |

### 7.3 Phase 3 — 治理台账与配置包

后缀均接 **`{空间内前缀}`** 之后。

| 说明 | 方法 | 后缀 |
|------|------|------|
| 治理变更日志 | GET | `/governance/change-logs` |
| 配置导出 | POST | `/config/export` |
| 配置导入 | POST | `/config/import` |
| 批量删除配置 | POST | `/config/batch-delete` |
| 已批准合并导出 | GET | `/exports/consolidated` |

若某操作在附录 A 中 **没有** 独立 key：任选 **（1）** 用最接近的 appendix A key 并把子动作写入 `detail_json`，或 **（2）** 在附录 A 增加新 key 并与产品负责人确认。**不得**不写 key 却仍写 audit 行。

---

## 8. 平台 IAM 审计键（非附录 A）

以下键名为 **本平台专用**，与附录 A **独立**：

| behavior_key | 建议 label |
|--------------|------------|
| `dsms-platform-tenant-creators-update` | 数据安全平台：项目创建权限维护 |
| `dsms-platform-users-import-excel` | 数据安全平台：用户批量导入 |
| `dsms-tenant-members-batch-add` | 数据安全项目：批量加入成员 |
| `dsms-tenant-members-batch-remove` | 数据安全项目：批量移除成员 |
| `dsms-tenant-member-role-promote` | 数据安全项目：项目角色变更 |
| `dsms-seeds-import` | 数据安全项目：治理种子导入 |

---

## 9. 错误码与分页

- **403**：当前身份无权访问该资源或执行该动作。
- **404**：资源不存在，或存在但不属于请求的 `tenant_id` / `space_id`。
- **422**：请求体验证失败。
- **409**（可选）：资源冲突。
- **分页响应体**：必须包含 **`total`** 与 **`items`** 两个键。

---

## 10. 前端

- **路由**：登录页；登录后进入 **项目选择或默认项目**；再进入 **`space_id` 工作台**。
- **同一屏幕多个平级功能模块**：必须使用 **Element Plus `el-tabs`**（见仓库 `.cursor/rules/dsms-ui-multi-function-tabs.mdc`）。
- **列表**：筛选条件变化时重置 **`skip=0`**。
- **HTTP**：`Authorization: Bearer`；收到 **401** 时的刷新逻辑或跳转登录：**在单个前端工程内选一种实现并保持一致**。

---

## 11. 分期验收

| 阶段 | 完成判定（可测试） |
|------|-------------------|
| Phase 1 | §5、§6、§7.1 的接口可被 Postman 或集成测试打通；前端 `pnpm run build` 成功 |
| Phase 2 | §7.2 接口齐全；每条写审计的调用携带正确 **附录 A key** |
| Phase 3 | §7.3 可用；另有「站内通知」则须在单独需求中定义，本文不默认实现 |

---

## 12. 建议实施顺序

1. 后端：配置、数据库、JWT、**`user` / `tenant` / `tenant_membership` / `tenant_creator_allowlist`**、超管种子。
2. **`/api/v1/auth/*` 与 `/api/v1/users/me`**。
3. **§6** 全部路径。
4. **§7.1**：按子域拆文件（如 `spaces_router.py`, `field_catalog_router.py`）；完成动态表单服务与一个空间的最小闭环。
5. 前端：登录 → 项目 → 空间 → Tab 页挂载 API。
6. Phase 2、Phase 3 按迭代追加。

---

## 13. Agent 启动提示（可复制到新会话）

```text
你是本仓库（DSMS / 数据安全治理独立系统）的实现 Agent。不得假设你见过其它项目或历史对话；仅阅读本仓库中的文本与代码。

唯一产品规格：docs/DSMS_IMPLEMENTATION_SPEC.md。实现前通读「前言」「文档契约」与附录 A。

技术约束摘要：FastAPI + SQLModel + SQLite；业务 API 前缀 /api/v1/dsms/；认证 /api/v1/auth/；多项目 tenant_id；列表 skip/limit 与 total/items；用户可读错误须中文；业务审计 behavior_key 与附录 A 的 key 完全一致；前端多功能区用 el-tabs。

执行顺序遵循规格 §12；先交付 Phase 1 可演示闭环：初始化超管、登录、创建项目、Excel 导入或手建用户、成员批量加入、创建空间、taxonomy 或 questionnaire 至少一条端到端可走通。

每次提交前在 frontend 执行 pnpm install --frozen-lockfile（若尚无 lock 则首次 install）与 pnpm run build；后端至少能启动并完成手工冒烟。
```

---

## 附录 A — 业务行为目录（behavior_key ⇄ 中文 label）

系统在记录「用户对业务功能的一次操作」时，**必须使用**下表 **`key`** 作为 `behavior_key`；界面展示 **`label`**。

| key | label |
|-----|-------|
| project-spaces | 数据安全治理：项目空间管理 |
| project-spaces/delete | 数据安全治理：删除项目空间 |
| suggest-identifier-key | 数据安全治理：标识自动生成 |
| questionnaire/questions | 数据安全治理：问卷题目管理 |
| questionnaire/questions/delete | 数据安全治理：删除问卷题目 |
| relevance-rule | 数据安全治理：相关性判定规则 |
| relevance-assessments | 数据安全治理：相关性判定填报 |
| lifecycle-field-config | 数据安全治理：填报表单字段配置 |
| field-catalog | 数据安全治理：数据字段主表 |
| field-requests | 数据安全治理：数据字段新增申请 |
| business-function-options | 数据安全治理：业务功能选项查询 |
| business-function-option-requests | 数据安全治理：业务功能选项申请与审核 |
| field-usage-reports | 数据安全治理：数据字段填报与导出 |
| classification-matrix | 数据安全治理：显式分类矩阵 |
| classification-matrix/delete | 数据安全治理：删除显式分类矩阵 |
| classification-rules | 数据安全治理：分类分级规则 |
| classification-rules/delete | 数据安全治理：删除分类分级规则 |
| classification-recompute | 数据安全治理：分类分级重算 |
| classification-results | 数据安全治理：分类分级结果查询 |
| classification-manual-override | 数据安全治理：分类分级人工覆写 |
| classification-revert-auto | 数据安全治理：分类分级恢复自动 |
| classification-audit | 数据安全治理：分类分级审计记录 |
| classification-export | 数据安全治理：分类分级结果导出 |
| taxonomy-nodes | 数据安全治理：分类分级和要求治理（Level1/2 分类树） |
| taxonomy-nodes/delete | 数据安全治理：删除分类节点 |
| field-class-grade | 数据安全治理：数据字段分类分级（密级） |
| field-security-requirements | 数据安全治理：数据字段安全要求 |
| field-security-requirements/delete | 数据安全治理：删除数据字段安全要求 |
| field-security-requirements-eval | 数据安全治理：安全要求逻辑求值 |

---

*文档版本：v1.2；日期：2026-05-09。*
