from __future__ import annotations

from pathlib import Path

from sage_plugin.config import Settings


def test_default_sqlite_database_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.delenv("SAGE_DATABASE_URL", raising=False)
    settings = Settings(auth_required=False)

    assert settings.database_url == f"sqlite:///{Path.home() / 'sage.db'}"
    assert not settings.database_url.endswith("./sage.db")


def test_explicit_database_url_is_preserved(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'explicit.db'}"
    monkeypatch.setenv("SAGE_DATABASE_URL", database_url)

    settings = Settings(auth_required=False)

    assert settings.database_url == database_url


def test_production_still_rejects_sqlite():
    try:
        Settings(
            env="production",
            database_url="sqlite:////tmp/production.db",
            auth_required=True,
            api_keys=["s" * 32],
            auto_create_schema=False,
            allowed_hosts=["example.test"],
            docs_enabled=False,
        )
    except ValueError as exc:
        assert "production requires a server database" in str(exc)
    else:
        raise AssertionError("production SQLite configuration unexpectedly accepted")
