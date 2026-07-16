import json
from datetime import datetime
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QlikRunRequest(BaseModel):
    tenant: str | None = Field(default=None, min_length=1)
    space: str | None = Field(default=None, min_length=1)
    dataflow: str | None = Field(default=None, min_length=1)
    headless: bool | None = None


class RunData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    tenant_name: str | None
    space_name: str | None
    dataflow_name: str | None
    downloaded_files: list[str] = Field(default_factory=list)
    error: str | None
    created_at: datetime | None

    @field_validator("downloaded_files", mode="before")
    @classmethod
    def parse_downloaded_files(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return json.loads(value)
        return value if isinstance(value, list) else []


ResponseT = TypeVar("ResponseT")


class ApiResponse(BaseModel, Generic[ResponseT]):
    data: ResponseT


class ErrorResponse(BaseModel):
    error: dict[str, str]


def safe_download_path(path: str | None) -> str | None:
    return str(Path(path).resolve()) if path else None
