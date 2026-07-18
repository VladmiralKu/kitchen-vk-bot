from decimal import Decimal

from app.services.parser import format_quantity, parse_order_text


def test_parse_order_with_table_items_and_comment():
    parsed = parse_order_text("Стол 4\nборщ 2\nпаста 1\nлимонад 1\nкомм: пасту без лука")

    assert parsed.table_number == "4"
    assert [(item.quantity, item.name) for item in parsed.items] == [
        (Decimal("2"), "борщ"),
        (Decimal("1"), "паста"),
        (Decimal("1"), "лимонад"),
    ]
    assert parsed.comment == "пасту без лука"


def test_old_leading_quantity_format_still_works():
    parsed = parse_order_text("Стол 4\n2 борщ\n1 паста\nКомментарий: без лука")

    assert [(item.quantity, item.name) for item in parsed.items] == [
        (Decimal("2"), "борщ"),
        (Decimal("1"), "паста"),
    ]
    assert parsed.comment == "без лука"


def test_parse_first_numeric_line_as_table():
    parsed = parse_order_text("7\nборщ 2\nбез сметаны")

    assert parsed.table_number == "7"
    assert parsed.items[0].name == "борщ"
    assert parsed.comment == "без сметаны"


def test_parse_decimal_quantity_with_comma():
    parsed = parse_order_text("лимонада 1,5")

    assert parsed.items[0].quantity == Decimal("1.5")
    assert format_quantity(parsed.items[0].quantity) == "1.5"


def test_no_items_when_no_quantity_lines():
    parsed = parse_order_text("паста без лука")

    assert parsed.items == []
    assert parsed.comment == "паста без лука"


def test_comment_alias_without_colon():
    parsed = parse_order_text("Стол 2\nкапуч кокос 2\nкомм без сахара")

    assert parsed.items[0].name == "капуч кокос"
    assert parsed.comment == "без сахара"


def test_blank_line_starts_second_course():
    parsed = parse_order_text("Стол 1\nборщ - 1\nкапуч - 2\n\nдесерт")

    assert parsed.table_number == "1"
    assert [(item.name, item.quantity, item.course) for item in parsed.items] == [
        ("борщ", Decimal("1"), 1),
        ("капуч", Decimal("2"), 1),
        ("десерт", Decimal("1"), 2),
    ]


def test_explicit_course_marker():
    parsed = parse_order_text("Стол 1\nК2\nмороженое 1")

    assert [(item.name, item.quantity, item.course) for item in parsed.items] == [
        ("мороженое", Decimal("1"), 2),
    ]


def test_inline_course_prefix():
    parsed = parse_order_text("К2 медовик - 1")

    assert [(item.name, item.quantity, item.course) for item in parsed.items] == [
        ("медовик", Decimal("1"), 2),
    ]


def test_inline_course_prefix_without_quantity_defaults_to_one():
    parsed = parse_order_text("К2 медовик")

    assert [(item.name, item.quantity, item.course) for item in parsed.items] == [
        ("медовик", Decimal("1"), 2),
    ]
