from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/qlik.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    qlik_email: str | None = Field(
        default=None, validation_alias=AliasChoices("QLIK_EMAIL", "qlik_email")
    )
    qlik_password: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("QLIK_PASSWORD", "qlik_password")
    )
    qlik_tenant: str | None = Field(
        default=None, validation_alias=AliasChoices("QLIK_TENANT", "qlik_tenant")
    )
    qlik_space: str | None = Field(
        default=None, validation_alias=AliasChoices("QLIK_SPACE", "qlik_space")
    )
    qlik_dataflow_name: str | None = Field(
        default=None, validation_alias=AliasChoices("QLIK_DATAFLOW_NAME", "qlik_dataflow_name")
    )
    qlik_target_url: str = Field(
        default="https://qlikcloud.com/",
        validation_alias=AliasChoices("QLIK_TARGET_URL", "qlik_target_url"),
    )
    qlik_download_dir: Path = Field(
        default=Path("downloads"),
        validation_alias=AliasChoices("QLIK_DOWNLOAD_DIR", "qlik_download_dir"),
    )
    qlik_headless: bool = Field(
        default=False, validation_alias=AliasChoices("QLIK_HEADLESS", "qlik_headless")
    )
    qlik_storage_state: Path = Field(
        default=Path("artifacts/qlik-storage-state.json"),
        validation_alias=AliasChoices("QLIK_STORAGE_STATE", "qlik_storage_state"),
    )

    @model_validator(mode="after")
    def normalize_database_url(self) -> "Settings":
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self

    def validate_qlik(self, space: str | None = None) -> None:
        missing = []
        if not self.qlik_email:
            missing.append("QLIK_EMAIL")
        if not self.qlik_password:
            missing.append("QLIK_PASSWORD")
        if not (space or self.qlik_space):
            missing.append("QLIK_SPACE")
        if missing:
            raise ValueError(f"Configuracion Qlik incompleta: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
