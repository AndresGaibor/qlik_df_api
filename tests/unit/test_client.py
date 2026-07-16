from app.client import construir_payload


def test_payload_without_dataflow_exports_all() -> None:
    assert construir_payload(headless=False) == {"headless": False}


def test_payload_can_select_one_dataflow() -> None:
    assert construir_payload(space="Espacio", dataflow="Flujo S3", headless=True) == {
        "space": "Espacio",
        "dataflow": "Flujo S3",
        "headless": True,
    }
