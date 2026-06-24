from decimal import Decimal

from app.services.parser import format_quantity, parse_order_text


def test_parse_order_with_table_items_and_comment():
    parsed = parse_order_text("Стол 4\n2 борщ\n1 паста\n1 лимонад\nКомментарий: пасту без лука")

    assert parsed.table_number == "4"
    assert [(item.quantity, item.name) for item in parsed.items] == [
        (Decimal("2"), "борщ"),
        (Decimal("1"), "паста"),
        (Decimal("1"), "лимонад"),
    ]
    assert parsed.comment == "пасту без лука"


def test_parse_first_numeric_line_as_table():
    parsed = parse_order_text("7\n2 борщ\nбез сметаны")

    assert parsed.table_number == "7"
    assert parsed.items[0].name == "борщ"
    assert parsed.comment == "без сметаны"


def test_parse_decimal_quantity_with_comma():
    parsed = parse_order_text("1,5 лимонада")

    assert parsed.items[0].quantity == Decimal("1.5")
    assert format_quantity(parsed.items[0].quantity) == "1.5"


def test_no_items_when_no_quantity_lines():
    parsed = parse_order_text("паста без лука")

    assert parsed.items == []
    assert parsed.comment == "паста без лука"
