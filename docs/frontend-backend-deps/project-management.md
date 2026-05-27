# 项目管理 — 后端依赖清单

## 1. 前端入口

- **路由**：`path`: `/project-management`，`name`: `dashboard-project-management`
- **主要组件**：`frontend/src/views/ProjectManagementPage.vue`

## 2. 当前实现状态

- **已接真实 API**
  - `GET /api/v1/users/me` — 仅 `system_admin` 可进入
  - `GET /api/v1/dsms/tenants` — 项目列表
  - `POST /api/v1/dsms/tenants` — 新建项目
  - `DELETE /api/v1/dsms/tenants/{id}` — 删除项目（`super_admin`；`slug=default` 不可删）
  - `POST .../tenants/{id}/seeds/import` — 默认空间与问卷种子
  - 复制**字段/规则**：`config/export` + `config/import`
  - 复制**人员**：`members/batch`
  - 复制**已审核填报**：`POST .../submission-tasks/copy-approved-from`（见下）
- **角色**：仅系统管理员

## 3. 复制「完成审核的填报数据」

| 项 | 说明 |
|----|------|
| HTTP | `POST /api/v1/dsms/tenants/{target_tenant_id}/spaces/{target_space_id}/submission-tasks/copy-approved-from` |
| Body | `{ "source_tenant_id", "source_project_space_id" }` |
| 筛选 | 来源空间内 `audit_status === "approved"` 的 `submission_task` |
| 映射 | 按 `business_function.function_key` 匹配目标空间业务功能；复制快照、生命周期行、协同人 |
| 权限 | 目标项目 `tenant_admin` 或 `super_admin`；非超管须同时是来源项目成员 |
| 审计 | `behavior_key`: `dsms-submission-tasks-copy-approved` |
| 建议顺序 | 先 `seeds/import` → 可选字段/规则 import → 可选成员 → 再复制填报 |
| 业务功能 | 目标空间缺同名 `function_key` 时，复制接口会按来源业务功能元数据自动创建（仅当来源功能记录存在） |

## 4. 联调检查清单

- [ ] 新建并复制后，字段目录「关联业务功能」能聚合到已审核填报
- [ ] 来源无 approved 任务时 `copied_count=0` 有提示
- [ ] 目标缺业务功能时 `skipped` 非空
