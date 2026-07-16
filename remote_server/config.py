from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RemoteSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="remote_server/.env", extra="ignore")

    remote_api_key: SecretStr
    remote_csv_path: Path = Path("data/dataflows.csv")
