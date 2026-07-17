import json
from pathlib import Path

from app.remote.schemas import DataflowRecord


def procesar_dataflow(path: Path) -> list[DataflowRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    dataflow = payload.get("dataflow", {})
    app_id = str(dataflow.get("context", {}).get("dataAppId", ""))
    graph = dataflow.get("graph", {})
    records: list[DataflowRecord] = []

    for node in graph.get("nodes", []):
        component = node.get("component", {})
        if node.get("type") != "target" and component.get("type") != "analyticsTarget":
            continue
        settings = (
            component.get("properties", {})
            .get("configuration", {})
            .get("settings", {})
        )
        records.append(
            DataflowRecord(
                dataflow_id=str(dataflow.get("id", "")),
                app_id=app_id,
                dataflow_name=str(dataflow.get("name", "")),
                description=str(dataflow.get("description", "")),
                target_type=str(node.get("type", "target")),
                target_id=str(node.get("id", "")),
                target_label=str(node.get("label", "")),
                filename=str(settings.get("fileName", "")),
                extension=str(settings.get("extension", "")),
                format=str(settings.get("format", "")),
                treat_as_relative=bool(settings.get("treatAsRelative", False)),
            )
        )

    if not records:
        records.append(
            DataflowRecord(
                dataflow_id=str(dataflow.get("id", "")),
                app_id=app_id,
                dataflow_name=str(dataflow.get("name", "")),
                description=str(dataflow.get("description", "")),
            )
        )
    return records
