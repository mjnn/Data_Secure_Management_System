"""在收集用例前绑定独立 SQLite 文件，避免 TestClient 与开发用 dsms.db 互相污染。"""
import os
from pathlib import Path

# 测试套件会频繁调用 /auth/login，关闭速率限制避免 429
os.environ.setdefault("DSMS_AUTH_RATE_LIMIT_ENABLED", "false")


def pytest_configure(config):
    db = Path(__file__).resolve().parent / "integration_session.sqlite"
    try:
        db.unlink(missing_ok=True)
    except OSError:
        pass
    os.environ["DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
