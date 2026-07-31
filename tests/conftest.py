from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

_USE_CONFIGURED_DB = os.getenv("SAGE_TEST_USE_CONFIGURED_DB", "").lower() in {"1", "true", "yes"}
_bootstrap_db = Path(tempfile.gettempdir()) / f"sage-pytest-{os.getpid()}.db"
if not _USE_CONFIGURED_DB:
    os.environ["SAGE_DATABASE_URL"] = f"sqlite:///{_bootstrap_db}"
os.environ["SAGE_AUTH_REQUIRED"] = "false"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    from sage_plugin import db as db_module
    __import__("sage_plugin.db_models")

    if _USE_CONFIGURED_DB:
        test_engine = db_module.engine
        db_module.SessionLocal.configure(bind=test_engine)
        db_module.Base.metadata.drop_all(test_engine)
        db_module.Base.metadata.create_all(test_engine)
        try:
            yield
        finally:
                    db_module.Base.metadata.drop_all(test_engine)
        return

    test_db = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db}",
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
    db_module.SessionLocal.configure(bind=test_engine)
    db_module.Base.metadata.create_all(test_engine)
    try:
        yield
    finally:
        db_module.Base.metadata.drop_all(test_engine)
        test_engine.dispose()


def pytest_sessionfinish() -> None:
    if _USE_CONFIGURED_DB:
        return
    try:
        _bootstrap_db.unlink()
    except FileNotFoundError:
        pass
