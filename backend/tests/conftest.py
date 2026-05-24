"""在收集用例前绑定独立 SQLite 文件，避免 TestClient 与开发用 dsms.db 互相污染。"""
from pathlib import Path


def pytest_configure(config):
    import os

    db = Path(__file__).resolve().parent / "integration_session.sqlite"
    try:
        db.unlink(missing_ok=True)
    except OSError:
        pass
    os.environ["DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
