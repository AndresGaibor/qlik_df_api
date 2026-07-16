import csv
import os
import tempfile
from pathlib import Path

from app.remote.schemas import DataflowRecord

FIELDS = list(DataflowRecord.model_fields)


class CsvDataflowRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def replace(self, records: list[DataflowRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=self.path.parent, delete=False
        ) as temporary:
            writer = csv.DictWriter(temporary, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(record.model_dump() for record in records)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.path)

    def list_records(self) -> list[DataflowRecord]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as source:
            return [DataflowRecord.model_validate(row) for row in csv.DictReader(source)]
