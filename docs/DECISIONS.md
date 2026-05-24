# DSMS 待确认决策记录（实现占位）

本文档记录在 `docs/DSMS_IMPLEMENTATION_SPEC.md` 未逐列定义、但 Phase 2/3 闭环所必需的**自洽约定**。若产品后续修订规格，应同步更新本文或删除对应条目。

## D1 — 字段主表与分类树的关联

**决策**：在 `field_catalog_entry` 上增加可选列 **`taxonomy_code`**（字符串，与同一空间内 `taxonomy_node.code` 对齐；可为空）。

**原因**：显式分类矩阵按「分类树节点 → 敏感级别」映射；无关联字段则矩阵无法作用于具体主表行。

**影响**：种子/旧数据可为空；重算时仅对填写了 `taxonomy_code` 的条目应用矩阵覆盖（见 D3）。旧 SQLite 文件在启动时会由 `create_db_and_tables` 尝试 `ALTER TABLE` 补列（见 `app/core/database.py`）。

## D2 — 分类规则 `condition_json` / `output_sensitivity`

**决策**：`classification_rule.condition_json` 为 JSON 字符串，支持：

| `type` | 含义 | 额外字段 |
|--------|------|----------|
| `identifier_contains` | `identifier_key` 子串匹配 | `value`: string |
| `field_name_contains` | `field_name` 子串匹配 | `value`: string |
| `data_type_equals` | `data_type` 全等 | `value`: string |
| `default` | 恒为真 | 无 |

`output_sensitivity` 存于规则行的 **`output_sensitivity`** 列（如 `公开` / `内部` / `秘密` / `机密`；实现不强制枚举，由项目配置语义）。

**影响**：规则按 **`priority` 升序** 取首个匹配项。

## D3 — 重算时规则与矩阵的优先级

**决策**：

1. 以主表 `sensitivity_level`（可空）为初始级别，缺省为 **`未分级`**。
2. 按规则优先级首个匹配覆盖级别，并记录 `matched_rule_id`。
3. 若主表 **`taxonomy_code` 非空**，且存在矩阵单元 `cells_json` 中与该 code 匹配的项，则用矩阵中的 **`sensitivity_level` 覆盖**当前级别（矩阵后于规则生效，便于「树定档、规则微调后再按矩阵收口」的运营理解）。

**矩阵 `cells_json` 结构**：`[{"taxonomy_code": "L1.A", "sensitivity_level": "内部"}, ...]`

**影响**：与仅规则引擎相比，多一步矩阵覆盖；审计 `detail_json` 中写入 `applied_matrix` 布尔。

## D4 — 配置导入的项目/空间范围

**决策**：

- **`tenant_admin`**：仅允许导入到 **当前 URL 中的 `tenant_id` + `space_id`**（与导出目标一致），载荷中若出现其它项目/空间 ID 一律 **422**。
- **`super_admin`**：允许在请求体中携带 **`target_tenant_id`**、**`target_project_space_id`**（须已存在且一致），将包导入至该空间；省略时默认导入到 URL 所指空间。

**影响**：跨项目搬运仅限超管；审计写入 `governance_change_log`。

## D5 — `POST /config/batch-delete` 语义

**决策**：请求体为 `{ "classification_matrix_ids": number[], "classification_rule_ids": number[] }`（可空数组）；仅删除属于该空间且 ID 在列表中的记录。其它资源类型后续可按相同模式扩展。

## D7 — Phase 3 与部分治理操作的 `behavior_key`（平台扩展键）

规格 §8 未逐条列出「配置导出/导入」等平台键。为在 `governance_change_log` 中可检索，本实现使用以下**平台扩展键**（写入 `GovernanceChangeLog.behavior_key`，**不**冒充附录 A）：

| 键 | 场景 |
|----|------|
| `dsms-config-export` | 配置导出 |
| `dsms-config-import` | 配置导入 |
| `dsms-config-batch-delete` | 配置批量删除 |
| `dsms-config-matrix-create` / `dsms-config-matrix-update` / `dsms-config-matrix-delete` | 矩阵维护（与附录 A 的审计表并存时便于区分） |
| `dsms-config-matrix-batch-import` | 矩阵批量导入 |
| `dsms-config-rule-create` / `dsms-config-rule-update` / `dsms-config-rule-delete` | 规则维护 |
| `dsms-classification-recompute` | 重算触发的治理侧摘要 |
| `dsms-field-class-grade-batch` / `dsms-field-class-grade-delete` | 密级绑定 |
| `dsms-security-req-create` / `dsms-security-req-update` | 安全要求维护 |
| `dsms-ref-sqlite-migration` | 自 `ref/data_secure_from_rds.sqlite` 导入治理日志（`governance_change_log`） |

**分类专用审计表** `classification_audit_log` 仍仅使用 **附录 A** 中的键（如 `classification-matrix`、`classification-recompute` 等）。

## D6 — 安全要求求值 `check_json`

**决策**：`field_security_requirement.check_kind` 取值：

- `min_grade`：`check_json` 为 `{"min_label":"秘密"}`，与字段 **`field_class_grade.grade_label`** 做字典序分级比较不严谨，故采用 **有序阶梯**：`公开=0, 内部=1, 秘密=2, 机密=3, 绝密=4`（未知标签记为 -1，判定为不满足并说明）。
- `max_length`：`check_json` 为 `{"max": 100}`，对主表 `identifier_key` 长度求值（演示用）。

**影响**：`evaluate` 返回结构化 `passed` / `reason` 中文说明。
