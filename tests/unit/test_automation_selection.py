import pytest

from app.qlik.automation import QlikAutomation, QlikAutomationError


def test_selects_configured_item_or_first() -> None:
    items = [{"name": "A"}, {"name": "B"}]

    assert QlikAutomation._select(items, None, "item") == items[0]
    assert QlikAutomation._select(items, "b", "item") == items[1]


def test_select_rejects_empty_or_unknown_item() -> None:
    with pytest.raises(QlikAutomationError, match="No hay item"):
        QlikAutomation._select([], None, "item")
    with pytest.raises(QlikAutomationError, match="No se encontro"):
        QlikAutomation._select([{"name": "A"}], "B", "item")
