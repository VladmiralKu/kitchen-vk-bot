from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


POSITION_RE = re.compile(r"^(\d+(?:[\.,]\d+)?)\s+(.+)$")
TABLE_RE = re.compile(r"^(?:стол|table)\s*[:#№-]?\s*(.+)$", re.IGNORECASE)
COMMENT_PREFIX_RE = re.compile(r"^(?:комментарий|comment)\s*:\s*(.*)$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedItem:
    quantity: Decimal
    name: str


@dataclass(frozen=True)
class ParsedOrder:
    table_number: str | None
    items: list[ParsedItem]
    comment: str | None

    @property
    def has_items(self) -> bool:
        return bool(self.items)


def parse_order_text(text: str) -> ParsedOrder:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]

    table_number: str | None = None
    items: list[ParsedItem] = []
    comment_lines: list[str] = []

    for index, line in enumerate(lines):
        table_match = TABLE_RE.match(line)
        if table_match and table_number is None:
            table_number = table_match.group(1).strip()
            continue

        if index == 0 and table_number is None and re.fullmatch(r"\d+", line):
            table_number = line
            continue

        item_match = POSITION_RE.match(line)
        if item_match:
            quantity_raw, name = item_match.groups()
            quantity = _parse_quantity(quantity_raw)
            if quantity is not None and name.strip():
                items.append(ParsedItem(quantity=quantity, name=name.strip()))
                continue

        comment_match = COMMENT_PREFIX_RE.match(line)
        if comment_match:
            value = comment_match.group(1).strip()
            if value:
                comment_lines.append(value)
            continue

        comment_lines.append(line)

    comment = "\n".join(comment_lines).strip() or None
    return ParsedOrder(table_number=table_number, items=items, comment=comment)


def format_quantity(quantity: Decimal) -> str:
    normalized = quantity.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f").rstrip("0").rstrip(".")


def render_parsed_order(parsed: ParsedOrder) -> str:
    table = parsed.table_number or "не указан"
    item_lines = "\n".join(f"• {format_quantity(item.quantity)} {item.name}" for item in parsed.items)
    comment = parsed.comment or "нет"
    return f"Стол: {table}\n\nПозиции:\n{item_lines}\n\nКомментарий:\n{comment}"


def _parse_quantity(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value
