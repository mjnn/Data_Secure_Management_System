# DSMS 全功能测试用例

> **版本**：与当前仓库 Phase 1–3 联调范围对齐  
> **规格真源**：`docs/DSMS_IMPLEMENTATION_SPEC.md`、`docs/DSMS_DATA_MODEL.md`  
> **联调清单**：`docs/frontend-backend-deps/phase11-integration-checklist.md`  
> **用例类型**：手工冒烟 + 可作为自动化用例设计输入（ID 可映射到 `backend/tests/`）

---

## 1. 测试范围

| 包含 | 不包含 |
|------|--------|
| 认证、用户资料、门户壳层（项目切换、深浅色、路由） | 多数据库类型、K8s 部署 |
| 项目管理、成员、种子导入、配置复制、租户删除 | 站内通知（规格未默认） |
| 问卷 / 相关性 / 分类树 / 分类矩阵与结果 | 外部 IAM 联邦登录 |
| 密级、安全要求、字段目录、生命周期元字段 | 性能压测（另立专项） |
| 填报任务全链路、审批、文档资源 | |

---

## 2. 环境与前置

### 2.1 运行环境

| 项 | 要求 |
|----|------|
| 后端 | `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 前端 | `cd frontend && pnpm run dev` → http://localhost:5173/ |
| 数据库 | SQLite（仓库默认 `backend/dsms.db`） |
| 浏览器 | Chrome / Edge 最新版；建议各测一轮浅色 + 深色主题 |

### 2.2 发版前自动化基线

```bash
cd backend && python -m pytest tests/ -q
cd frontend && pnpm run build
```

### 2.3 测试账号（种子默认）

| 用户名 | 密码 | 平台角色 | 典型用途 |
|--------|------|----------|----------|
| `admin` | `Admin123456` | 系统管理员（`is_superuser`） | 全菜单、项目管理、审批 |
| `security_fo` | `SecurityFo123456` | 数据安全 FO | 规则/字段/填报下发与审核 |
| `function_fo` | `FunctionFo123456` | 功能 FO | 绑定业务功能、填报工作流 |

### 2.4 项目与空间

| 对象 | 说明 |
|------|------|
| 默认项目 | `slug=default`，门户种子含业务功能 `field_usage` / `field_request` 等 |
| 新建项目 | 项目管理 → 新建 → 自动 `seeds/import` 得 `default-space` |
| 空间键 | 默认种子空间 `space_key=default-space`（新建租户）；默认项目内为 `default` |

**通用期望**：列表接口 `skip`/`limit`，响应 `total` + `items`；面向用户的 `detail` 为中文；写操作审计 `behavior_key` 与规格附录 A / §8 逐字一致。

---

## 3. 用例编写约定

| 字段 | 说明 |
|------|------|
| **ID** | `TC-<模块>-<序号>` |
| **优先级** | P0 阻断 / P1 主流程 / P2 边界与体验 |
| **角色** | 执行账号 |
| **步骤** | 可逐条勾选 |
| **期望** | 可观察、可判定 |

---

## 4. 认证与门户壳层

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-AUTH-01 | P0 | 未登录 | 直接访问 `/` | 重定向 `/login` |
| TC-AUTH-02 | P0 | admin | 正确账号密码登录 | 进入控制台 `/`；`localStorage` 有 `dsms_access_token` |
| TC-AUTH-03 | P0 | admin | 错误密码登录 | 中文错误提示；不写入 token |
| TC-AUTH-04 | P1 | admin | 已登录访问 `/login` | 重定向控制台 |
| TC-AUTH-05 | P1 | admin | 顶栏 → 退出登录 | 回登录页；token 清除；再访 `/` 需登录 |
| TC-AUTH-06 | P1 | admin | 顶栏 → 账号设置 → 改姓名/邮箱 → 保存 | `PUT /users/me` 成功；顶栏显示名更新；刷新仍一致 |
| TC-AUTH-07 | P1 | admin | 账号设置 → 修改密码 | `POST /users/me/password` 成功；旧密码失效 |
| TC-AUTH-08 | P2 | admin | 切换深/浅色主题 | 全站令牌一致；刷新后主题保持 |
| TC-AUTH-09 | P1 | admin | 连续切换 5 个侧栏菜单 | **不出现**每次「正在加载当前用户…」；Network 中 `/users/me` 仅首次或刷新后 1 次 |
| TC-AUTH-10 | P2 | admin | 顶栏项目切换 | `GET /tenants` 列表；切换后业务数据随 `tenant_id` 变化 |
| TC-AUTH-11 | P1 | admin | 登录后首屏 | 租户/空间解析完成（`bootstrapSpaceConfig`）；首页卡片待办数可加载 |

---

## 5. 项目管理

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-PROJ-01 | P0 | admin | 侧栏进入「项目管理」 | 可见项目列表（非 FO） |
| TC-PROJ-02 | P1 | security_fo | 访问项目管理路由 | 提示无权限或重定向首页 |
| TC-PROJ-03 | P0 | admin | 新建项目（仅名称） | `POST /tenants` 成功；列表出现；`seeds/import` 后有 `default-space` |
| TC-PROJ-04 | P0 | admin | 新建并勾选复制：字段+规则+成员+已审填报 | 配置 import 成功；成员 batch 成功；`copy-approved-from` `copied_count≥0`；目标空间有对应业务功能 |
| TC-PROJ-05 | P1 | admin | 复制来源无已审任务 | 复制填报提示「无已审核通过…」或 `copied_count=0` |
| TC-PROJ-06 | P0 | admin | 删除非 default 项目 | `DELETE /tenants/{id}` 成功；列表消失；审计 `dsms-tenant-delete` |
| TC-PROJ-07 | P0 | admin | 删除 `slug=default` | 前端禁止或后端 4xx；中文说明 |
| TC-PROJ-08 | P1 | admin | 新建后顶栏切换至新项目 | 空间配置重载；填报/字段页数据属新项目 |

---

## 6. 用户管理

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-USER-01 | P0 | admin | 用户管理列表 | `GET /dsms/users` 分页；显示成员关系 |
| TC-USER-02 | P1 | security_fo | 进入用户管理 | 可浏览（规格允许 FO 检索入项） |
| TC-USER-03 | P1 | function_fo | 进入用户管理 | 无权限提示或重定向 |
| TC-USER-04 | P0 | admin | 批量加入成员到当前项目 | `members/batch` 成功；重复用户 skipped |
| TC-USER-05 | P1 | admin | 提升成员为 tenant_admin | `PUT .../members/{id}/role` 成功 |
| TC-USER-06 | P2 | admin | 下载导入模板 / Excel 导入用户 | 模板可下；导入后新用户出现在目录 |
| TC-USER-07 | P1 | admin | 修改用户平台角色为 function_fo | 该用户侧栏仅 FO 可见菜单 |

---

## 7. 规则治理 — 相关性

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-REL-01 | P0 | security_fo | 相关性问卷：新增/编辑/删除题目 | CRUD 持久化；列表刷新一致 |
| TC-REL-02 | P0 | security_fo | 表达式配置页保存规则 | `relevance_rule` 保存；审计 key 正确 |
| TC-REL-03 | P1 | security_fo | 表达式页验证/试算（若有） | 输出与配置一致 |
| TC-REL-04 | P1 | function_fo | 访问相关性配置 | 无菜单或重定向 |
| TC-REL-05 | P2 | security_fo | 删除题目后表达式仍引用 | 有合理提示或校验失败（中文） |

---

## 8. 规则治理 — 数据分类标准

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-TAX-01 | P0 | security_fo | 分类树层级 CRUD | 层级列表与 API 一致 |
| TC-TAX-02 | P0 | security_fo | 分类树节点增删改 | 树结构正确；`taxonomy_code` 唯一约束生效 |
| TC-TAX-03 | P0 | security_fo | 数据字段分类：选字段+叶节点保存 | 绑定写入；列表可查 |
| TC-TAX-04 | P0 | security_fo | 分类矩阵/规则配置保存 | 矩阵与规则持久化 |
| TC-TAX-05 | P0 | security_fo | 自动分类结果：重算 | 结果列表更新 |
| TC-TAX-06 | P1 | security_fo | 结果手调级别 | 单条更新成功 |
| TC-TAX-07 | P1 | security_fo | 导出 CSV | 文件可下载、编码正确（含 BOM 若实现） |
| TC-TAX-08 | P2 | function_fo | 访问分类配置页 | 无权限 |

---

## 9. 规则治理 — 密级绑定

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-GRADE-01 | P0 | security_fo | 密级定义 CRUD | 密级列表与排序正确 |
| TC-GRADE-02 | P0 | security_fo | 字段-密级绑定保存 | 绑定关系持久化 |
| TC-GRADE-03 | P1 | function_fo | 访问密级模块 | 无权限或重定向 |

---

## 10. 规则治理 — 安全要求

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-SEC-01 | P0 | security_fo | 新增/编辑/删除安全要求规则 | 富文本保存；列表刷新 |
| TC-SEC-02 | P1 | security_fo | 试算 evaluate（若页面提供） | 返回匹配的要求项 |
| TC-SEC-03 | P2 | function_fo | 只读访问安全要求页 | 仅查看或不可见（与实现一致） |

---

## 11. 字段治理

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-FIELD-01 | P0 | security_fo | 生命周期元字段：查看内置项 | `data_field`、`business_function` 锁定必填 |
| TC-FIELD-02 | P0 | security_fo | 新增自定义生命周期字段并保存 | `lifecycle-field-config` 同步成功 |
| TC-FIELD-03 | P0 | security_fo | 字段目录：新增字段 | 列表出现；审计正确 |
| TC-FIELD-04 | P0 | function_fo | 字段目录：申请新增 | 产生待审批；审批通过后入库 |
| TC-FIELD-05 | P1 | function_fo | 申请删除字段 | 待审批 → 通过后删除 |
| TC-FIELD-06 | P1 | security_fo | 关联业务功能列 | 来自已审填报 `foFillLifecycleRows` 聚合 |

---

## 12. 填报管理

### 12.1 数据安全 FO / 管理员

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-SUB-01 | P0 | security_fo | 填报情况页 | 统计与图表有数据；与任务列表一致 |
| TC-SUB-02 | P0 | security_fo | 创建填报任务（选 field_usage） | 任务草稿创建 |
| TC-SUB-03 | P0 | security_fo | 多选任务批量下发 | `dispatched`；FO 可见 |
| TC-SUB-04 | P0 | security_fo | 任务详情 → 审核通过 | `audit_status=approved`；若有 `submission_fill_review` 同步 |
| TC-SUB-05 | P1 | security_fo | 审核退回 | `audit_status=returned`；中文意见保存 |
| TC-SUB-06 | P1 | security_fo | 未绑定 FO 的功能下发 | 提示或禁止（与产品文案一致） |

### 12.2 功能 FO

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-SUB-10 | P0 | function_fo | 绑定业务功能（申请→审批） | 绑定 active；任务列表可按功能过滤 |
| TC-SUB-11 | P0 | function_fo | 打开工作流：相关性判定 → 不相关 | 任务结束/打标；不再要求生命周期填报 |
| TC-SUB-12 | P0 | function_fo | 工作流：相关 → 填生命周期 → 提交 | `fo_fill_status=submitted`；产生待审记录 |
| TC-SUB-13 | P1 | function_fo | 申请取消填报 | 审批管理出现待办；通过后任务取消态 |
| TC-SUB-14 | P1 | function_fo | 已结束任务只读打开 | 不可再编辑 |
| TC-SUB-15 | P1 | function_fo | 访问「填报情况」 | 无菜单入口 |

---

## 13. 审批管理

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-APR-01 | P0 | security_fo | 待我审批：通过 FO 绑定申请 | 状态 approved；绑定生效 |
| TC-APR-02 | P0 | security_fo | 驳回字段目录申请 | 状态 rejected；理由中文 |
| TC-APR-03 | P0 | security_fo | 通过填报内容审核 | 任务审核态与审批单一致 |
| TC-APR-04 | P1 | function_fo | 「我的申请」Tab | 仅本人记录 |
| TC-APR-05 | P1 | function_fo | 待我审批 Tab | 无审批按钮或为空 |
| TC-APR-06 | P1 | admin | 审批链一览卡片 | 系统管理员可见说明表 |
| TC-APR-07 | P1 | security_fo | 通过后顶栏/首页待办红点减少 | `pending-count` 与列表一致 |

---

## 14. 文档资源

| ID | 优先级 | 角色 | 步骤 | 期望 |
|----|--------|------|------|------|
| TC-DOC-01 | P1 | security_fo | 法规文件上传 | 资源列表出现；可下载 |
| TC-DOC-02 | P1 | security_fo | 模块模板下载 | xlsx 可打开 |
| TC-DOC-03 | P1 | security_fo | 模块数据导入 | 作业记录 success/失败中文 |
| TC-DOC-04 | P1 | security_fo | 模块数据导出 | 生成资源并可下载 |
| TC-DOC-05 | P2 | function_fo | 文档资源页只读 | 可浏览；上传按钮隐藏（若 FO 无上传权） |

---

## 15. 权限矩阵（菜单冒烟）

| 菜单/路由 | admin | security_fo | function_fo |
|-----------|:-----:|:-----------:|:-----------:|
| 控制台首页 | ✓ | ✓ | ✓ |
| 用户管理 | ✓ | ✓ | ✗ |
| 项目管理 | ✓ | ✗ | ✗ |
| 填报情况 | ✓ | ✓ | ✗ |
| 填报任务管理 | ✓ | ✓ | ✓ |
| 生命周期元字段 | ✓ | ✓ | ✗ |
| 数据字段 | ✓ | ✓ | ✓ |
| 规则治理（相关性/分类/密级/安全） | ✓ | ✓ | ✗ |
| 审批管理 | ✓ | ✓ | ✓（仅我的申请） |
| 文档资源 | ✓ | ✓ | ✓ |

**判定**：侧栏无入口 + 直接输入 URL 应重定向或中文无权限提示。

---

## 16. 端到端场景（建议演示顺序）

### E2E-01 新项目从零到可填报（admin + security_fo + function_fo）

1. **admin** 新建项目 B，复制 default 的字段+规则+成员。  
2. **admin** 将 `function_fo` batch 加入项目 B。  
3. **security_fo** 切换至 B：问卷/分类/密级/安全要求各保存一条。  
4. **security_fo** 创建并下发 `field_usage` 任务。  
5. **function_fo** 切换至 B：绑定 `field_usage`（若需审批则 **security_fo** 通过）。  
6. **function_fo** 完成工作流并提交。  
7. **security_fo** 任务详情审核通过。  
8. **security_fo** 字段目录可见新 `data_field` 聚合。

**通过标准**：全链路无 500；状态与数据库一致；关键步骤有 governance/audit 记录（若已实现查询 UI）。

### E2E-02 已审填报复制到新项目（admin）

1. 在 default 项目确保存在 `audit_status=approved` 的填报任务。  
2. **admin** 新建项目 C，仅勾选「完成审核的填报数据」。  
3. 打开 C 的填报任务列表 / 字段目录关联功能。

**通过标准**：`copied_count≥1`；目标空间自动补齐同名 `function_key`；任务标题与审核态保留。

### E2E-03 字段变更审批闭环（function_fo + security_fo）

1. **function_fo** 字段目录提交新增申请。  
2. **security_fo** 审批管理通过。  
3. **function_fo** 刷新字段目录可见新项。

---

## 17. API 冒烟附录（Postman / curl）

| 序号 | 方法 | 路径 | 角色 | 期望 |
|------|------|------|------|------|
| API-01 | POST | `/api/v1/auth/login` | - | 200 + access_token |
| API-02 | GET | `/api/v1/users/me` | 任意已登录 | 200 + platform_role |
| API-03 | GET | `/api/v1/dsms/tenants` | admin | total/items |
| API-04 | POST | `/api/v1/dsms/tenants/{id}/seeds/import` | tenant_admin | space_id |
| API-05 | POST | `.../submission-tasks/copy-approved-from` | tenant_admin | copied_count, skipped |
| API-06 | DELETE | `/api/v1/dsms/tenants/{id}` | super_admin | default 不可删 |
| API-07 | GET | `.../approval-requests/pending-count` | security_fo | 数字 ≥0 |
| API-08 | GET | `.../governance/change-logs` | tenant_admin | 写操作后有记录 |

---

## 18. 缺陷记录模板

| 字段 | 内容 |
|------|------|
| 用例 ID | |
| 环境 | 前后端 commit / 分支 |
| 角色 | |
| 复现步骤 | |
| 实际结果 | |
| 期望结果 | |
| 截图/Network | |
| 严重程度 | 阻断 / 主要 / 次要 |

---

## 19. 执行记录（可打印）

| 日期 | 执行人 | 构建/分支 | P0 通过 | P1 通过 | 备注 |
|------|--------|-----------|---------|---------|------|
| | | | / | | |
| | | | / | | |

---

**说明**：若实现与规格不一致，以规格为准修正产品或代码，并在 `docs/frontend-backend-deps/<slug>.md` 的「与规格的差异」中记录后再更新本用例。
