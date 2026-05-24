# ref SQLite → DSMS 本仓模型迁移说明

脚本：`backend/scripts/migrate_from_ref_sqlite.py`

## 源库特征

- 表名前缀 `datasecure*`，部分列为 **TEXT** 存 UUID/数字。
- 业务维度为 **`tool_id`（对应旧「工具」）+ `project_space_id`**。
- 本仓库 DSMS 无 `tool` 实体：迁移时将 **每个 `tool_id` 映射为一个新项目**  
  `slug = migrated-ref-tool-{tool_id}`，名称取自源表 `tool.name`（前缀 `[迁移]`）。

## 已迁移实体（有数据即迁）

| 源表 | 目标表 | 说明 |
|------|--------|------|
| `tool` + `datasecureprojectspace` | `tenant` + `tenantmembership` + `projectspace` | 超管（目标库首个 `is_superuser`）写入 `tenant_admin`；`space_key`/`name` 保留；若 `space_key` 冲突则追加 `-m{旧id}` |
| `datasecurequestionnairequestion` | `questionnairequestion` | `question_key` → `key`；`YES_NO` → `yes_no`；已存在同 `(tenant, space, key)` 则跳过 |
| `datasecurerelevancerule` | `relevancerule` | 旧列打包为 JSON 写入 `expression` |
| `datasecurelifecyclefielddefinition` + `datasecurelifecyclefieldconfig` | `lifecyclefieldconfig` | 按 `field_key` 合并；`TEXTAREA`→`textarea`；校验写入 `validation_json` |
| `datasecuregovernancechangelog` | `governancechangelog` | `behavior_key` 固定为 **`dsms-ref-sqlite-migration`**；原 `domain`/`action` 等写入 `summary` 与 `detail_json` |

## 当前不迁移（源表行数为 0 或未映射）

包括但不限于：`datasecurefieldcatalogentry`、`datasecurefieldrequest`、`datasecurefieldclassification*`、`datasecurefieldusagereport*`、`datasecuretaxonomynode` 等。若后续 ref 库有数据，可在同一脚本中按字段契约扩展。

## 在前端为什么「看不到」迁移数据？

1. **项目**：迁移会新建项目（`slug=migrated-ref-tool-{tool_id}`），与你在页面上手动建的其他项目并存。必须在项目下拉框里选中该迁移项目（页面已优先自动选中带 `[迁移]` / `migrated-ref-tool-` 的项目）。  
2. **空间 ID**：目标库里 `projectspace.id` 会重新分配，**与 ref 里旧的 `project_space_id`（如 9）一般不一致**。各 Tab 里的 `spaceId` 必须填**新 ID**；加载「项目空间列表」后会把当前页第一个空间 ID 自动写入 `spaceId`（若当前值为空或与当前页不匹配）。  
3. **未迁移的表**：当前脚本**未**导入字段主表、填报、分类矩阵等 ref 里行数为 0 的表，这些 Tab 仍会空。

## 幂等与重复执行

- 项目：按 `slug` 查找，已存在则复用并补写缺失的 `tenant_admin` 成员关系。
- 问卷题目、生命周期配置：同键已存在则跳过插入。
- **治理日志**未做去重：重复执行会再次插入 30 条类日志，请避免对同一目标库多次全量迁移。

## 平台审计键

治理迁移写入的 `behavior_key` 为 **`dsms-ref-sqlite-migration`**（非附录 A；与 `docs/DECISIONS.md` 中平台扩展键策略一致）。
