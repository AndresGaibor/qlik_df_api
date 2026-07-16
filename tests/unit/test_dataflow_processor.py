import json

from app.qlik.processor import procesar_dataflow


def test_extracts_dataflow_and_target_fields(tmp_path) -> None:
    source = {
        "dataflow": {
            "id": "flow-1",
            "name": "Flujo 1",
            "description": "Descripcion",
            "graph": {
                "nodes": [
                    {
                        "type": "target",
                        "id": "target-1",
                        "label": "FTP",
                        "component": {
                            "type": "analyticsTarget",
                            "properties": {
                                "configuration": {
                                    "settings": {
                                        "fileName": "/upload/file",
                                        "extension": "parquet",
                                        "format": "parquet",
                                        "treatAsRelative": False,
                                    }
                                }
                            },
                        },
                    }
                ]
            },
        }
    }
    path = tmp_path / "flow.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    records = procesar_dataflow(path)

    assert records[0].dataflow_id == "flow-1"
    assert records[0].target_label == "FTP"
    assert records[0].filename == "/upload/file"
    assert records[0].extension == "parquet"
    assert records[0].format == "parquet"
    assert records[0].treat_as_relative is False
