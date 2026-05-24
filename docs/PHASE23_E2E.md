# Phase 2 / Phase 3 端到端演示步骤

前置：后端已启动（默认 `http://127.0.0.1:8000`）、前端已登录、已选择项目与 `spaceId`，且该空间下已有至少一条 **字段主表** `field_catalog` 条目（记下 `id` 作为 `field_catalog_entry_id`）。

若本地 SQLite 库在 Phase 2 代码之前已存在，启动时会在 `app/core/database.py` 的 **`create_db_and_tables`** 内尝试自动补列 **`taxonomy_code`**（`fieldcatalogentry`）。若仍失败，请备份后删库重建，或手工 `ALTER TABLE fieldcatalogentry ADD COLUMN taxonomy_code VARCHAR;`。

## Phase 2 — 分类闭环

1. 在 **字段主表** Tab 为某字段填写 **taxonomy_code**（与 **分类树** 中某节点 `code` 一致），保存/更新条目。
2. 打开 **Phase2/3 治理 → 分类矩阵与规则**：新建矩阵，`cells_json` 示例：`[{"taxonomy_code":"你的code","sensitivity_level":"秘密"}]`。
3. 新建规则：`condition_json` 可为 `{"type":"default"}` 或 `{"type":"identifier_contains","value":"xxx"}`，填写 `output_sensitivity`。
4. **重算与结果** Tab：点击 **分类重算**，再 **加载结果**，确认 `sensitivity_level` 与预期一致。
5. 填写 **result_id**，**人工覆写**为其它级别，再 **加载结果** 确认 `is_manual_override=true`。
6. 点击 **恢复自动**，再加载结果，确认恢复为自动重算结果且人工标记清除。
7. **审计** / **导出 CSV**：确认 `classification_audit` 表有附录 A 键名记录；CSV 可下载。

## Phase 2 — 密级与安全求值

1. **密级与安全** Tab：填写主表 `field_catalog_entry_id` 与密级标签，**保存密级**。
2. **新建安全要求**：`check_kind` 填 `min_grade`，`check_json` 如 `{"min_label":"秘密"}`；或 `max_length` / `{"max":64}`。
3. **求值 evaluate**：查看返回 JSON 中每条 `passed` 与中文 `reason`。

## Phase 3 — 配置与治理

1. **治理与配置** Tab：**导出配置(JSON)**，得到 `dsms-space-config.json`。
2. 将文件内容粘贴到 **导入 bundle**，**导入配置**（同空间为合并/覆盖式 upsert，见 `docs/DECISIONS.md`）。
3. **变更日志**：确认出现 `dsms-config-export` / `dsms-config-import` 等平台扩展键（见 `docs/DECISIONS.md` D7）。
4. 在「删矩阵 IDs / 删规则 IDs」填入从列表中读到的 id，**批量删矩阵/规则**。
5. **合并导出 ZIP**：下载后应含 `approved_field_usage.csv` 与 `classification_results.csv`。

## 自动化冒烟（可选）

在后端目录执行（需已安装依赖）：

```bash
python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); print('health', c.get('/healthz').status_code)"
```

将 `Authorization` 头换为真实 JWT 后，可对 `/api/v1/dsms/tenants/1/spaces/1/classification/matrix` 等路径做 GET 校验。

### pytest（含 JWT 集成）

`tests/conftest.py` 会在会话开始时将 `DATABASE_URL` 指向 `tests/integration_session.sqlite` 并删除旧文件，与开发用 `dsms.db` 隔离。在 `backend` 目录执行：

```bash
python -m pytest tests/ -v
```

其中 `test_api_integration.py` 会走登录 → 建项目 → 建空间 → 调分类矩阵 API 的完整链路。
