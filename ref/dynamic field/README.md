# 动态字段与可配置表单（参考快照）

本目录为 **Toolbox 主仓库内可复用「动态字段 / 字段配置」能力** 的离线参考包，便于其它仓库的 Agent 或人工在不打开全仓的情况下阅读契约、文档与实现。

**重要**：此处文件为 **快照副本**，与主代码路径可能滞后。以主仓库源文件为准做功能开发；合并前请以主路径为准做 diff。

## 目录结构

| 路径 | 说明 |
|------|------|
| `README.md` | 本说明与主仓库路径映射 |
| `docs/` | 模块设计文档与 Agent 任务模板 |
| `backend/app/services/` | 后端通用核心 + Service ID 薄封装示例 |
| `frontend/` | 通用 Vue 组件 + 从 `types.ts` 摘录的类型文件 |

## 主仓库权威路径（开发时请编辑这里）

| 类别 | 主仓库路径 |
|------|------------|
| 模块总览 | `docs/FORM_FIELD_CONFIG_MODULE.md` |
| Service ID 字段表 + 规则库插槽约定 | `.docs/FIELD_CONFIG_MANAGER_AND_SERVICE_ID_RULES.md` |
| Agent 任务模板 | `docs/templates/FORM_FIELD_CAPABILITY_AGENT_TEMPLATE.md` |
| 工具无关校验 / 归一化 / 值表读写 | `backend/app/services/dynamic_form_fields.py` |
| Service ID 绑定模型与路由编排示例 | `backend/app/services/service_id_dynamic_fields.py` |
| 动态表单渲染 | `frontend/src/components/form-config/DynamicFieldInputs.vue` |
| 管理端字段配置表 | `frontend/src/components/form-config/FieldConfigManagerTable.vue` |
| 静态单选/多选选项编辑（默认弹窗体） | `frontend/src/components/form-config/SelectOptionValuesEditor.vue` |
| 顺序说明常量 | `frontend/src/components/form-config/fieldConfigManagerConstants.ts` |
| 前端类型（完整定义仍在 monolith） | `frontend/src/api/types.ts`（`FormField*`、`DynamicFormValues`） |

## 本目录 `frontend/` 与主仓库的差异

为便于 **单目录阅读**，快照中的 Vue 组件将 `@/api/types` 等别名改为同级的 `./types-form-field.api.ts`。主仓库源码仍使用 `@/api/types` 与 `@/components/form-config/*`。

将组件迁回主仓库或其它已配置 `@/` 别名的工程时，请恢复为与主仓一致的 import。

## 架构要点（给 Agent 的摘要）

1. **路由层**（各工具 `routes.py`）只做权限与编排；字段校验与持久化放在 **服务层**。
2. **通用核心** `dynamic_form_fields.py`：与具体 ORM 模型解耦的校验、允许值解析、`save_custom_field_values` / `load_custom_field_values` 等。
3. **工具封装** `service_id_dynamic_fields.py`：展示如何把上述核心接到具体 `ServiceId*` 模型；新工具应仿照其分层，而不是把逻辑写回 `routes.py`。
4. **前端**：填报用 `DynamicFieldInputs.vue`；管理端字段表用 `FieldConfigManagerTable.vue`；单选/多选默认选项编辑用 `SelectOptionValuesEditor.vue`；若选项来自规则库等外部源，使用 `FieldConfigManagerTable` 的 **`#selectOptionsEditor`** 插槽覆盖默认弹窗（见 `docs/` 内 FIELD_CONFIG 文档）。
5. **依赖**：前端组件基于 **Vue 3 + Element Plus**；后端基于 **FastAPI + SQLModel**。

## 未纳入本快照的内容（需回主仓阅读）

- `ServiceIdRuleCategoryEditor.vue` 等工具专属管理 UI。
- `data_secure_dynamic_fields.py` 等其它工具的动态字段封装。
- `frontend/src/api/tools.ts` 中的具体 API 封装函数。

## 维护建议

在主线修改动态字段相关文件后，可重新执行复制命令更新本目录（或让维护者按需刷新），避免双处长期漂移无人知晓。
