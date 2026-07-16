from app.remote.csv_repository import CsvDataflowRepository
from app.remote.schemas import DataflowRecord


def test_replace_rewrites_all_records(tmp_path) -> None:
    repository = CsvDataflowRepository(tmp_path / "dataflows.csv")
    first = DataflowRecord(dataflow_id="1", dataflow_name="A", description="A")
    second = DataflowRecord(dataflow_id="2", dataflow_name="B", description="B")

    repository.replace([first, second])
    repository.replace([second])

    assert repository.list_records() == [second]
