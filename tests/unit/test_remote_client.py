import json

from app.remote import client
from app.remote.schemas import DataflowRecord


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps({"data": {"count": 1}}).encode()


def test_replace_sync_uses_identifiable_user_agent(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(client, "urlopen", fake_urlopen)

    result = client._replace_sync(
        "https://apiqd.andresgaibor.com",
        "test-key",
        [DataflowRecord(dataflow_id="flow-1", dataflow_name="Flujo 1")],
    )

    assert result == 1
    assert captured["request"].get_header("User-agent") == "qlik-df-api/0.1"
    assert captured["timeout"] == 60
