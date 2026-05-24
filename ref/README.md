# 参考数据（ref）

- **`data_secure_from_rds.sqlite`**：从旧环境导出的 SQLite，表前缀为 `datasecure*`，业务外键原为 **`tool_id` + `project_space_id`**（多工具宿主模型）。

迁移到本仓库 DSMS 模型时，请使用：

```bash
cd backend
set PYTHONPATH=.
python scripts/migrate_from_ref_sqlite.py --ref ../ref/data_secure_from_rds.sqlite --dry-run
python scripts/migrate_from_ref_sqlite.py --ref ../ref/data_secure_from_rds.sqlite
```

默认目标库为环境变量 **`DATABASE_URL`**（未设置时同 `app/core/config.py` 默认 `sqlite:///./dsms.db`）。**正式迁移前请备份目标库文件。**

字段级映射说明见 **`docs/MIGRATION_REF_SQLITE.md`**。
