import pytest

from app.core.config import Settings


def test_settings_use_sqlite_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("sqlite+aiosqlite:///")


def test_storage_state_is_optional() -> None:
    settings = Settings(_env_file=None)

    assert settings.qlik_storage_state is None


def test_settings_require_qlik_credentials_for_automation() -> None:
    settings = Settings(_env_file=None, QLIK_SPACE="Espacio")

    with pytest.raises(ValueError, match="QLIK_EMAIL"):
        settings.validate_qlik()


def test_settings_accept_postgres_url() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/qlik",
        QLIK_EMAIL="user@example.com",
        QLIK_PASSWORD="secret",
        QLIK_SPACE="Espacio",
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")
