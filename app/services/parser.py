from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


LEADING_QUANTITY_RE = re.compile(r"^(\d+(?:[\.,]\d+)?)\s+(.+)$")
TRAILING_QUANTITY_RE = re.compile(r"^(.+?)(?:\s*[-–—:]\s*|\s+)(\d+(?:[\.,]\d+)?)$")
TABLE_RE = re.compile(r"^(?:стол|table)\s*[:#№-]?\s*(.+)$", re.IGNORECASE)
COMMENT_PREFIX_RE = re.compile(r"^(?:комм|комментарий|comment)\s*:?\s*(.*)$", re.IGNORECASE)
COMMENT_HINT_RE = re.compile(r"^(?:без|не|no)\b", re.IGNORECASE)
COURSE_MARKER_RE = re.compile(r"^(?:к|курс|course)\s*([1-9]\d*)$|^([1-9]\d*)\s*(?:к|курс|course)$", re.IGNORECASE)
COURSE_PREFIX_RE = re.compile(r"^(?:к|курс|course)\s*([1-9]\d*)\s+(.+)$|^([1-9]\d*)\s*(?:к|курс|course)\s+(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedItem:
    quantity: Decimal
    name: str
    course: int = 1


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

    table_number: str | None = None
    items: list[ParsedItem] = []
    comment_lines: list[str] = []
    in_comment = False
    current_course = 1
    blank_already_started_course = False

    for index, line in enumerate(lines):
        if not line:
            if items and not in_comment and not blank_already_started_course:
                current_course += 1
                blank_already_started_course = True
            continue

        blank_already_started_course = False

        if in_comment:
            comment_lines.append(line)
            continue

        table_match = TABLE_RE.match(line)
        if table_match and table_number is None:
            table_number = table_match.group(1).strip()
            continue

        if index == 0 and table_number is None and re.fullmatch(r"\d+", line):
            table_number = line
            continue

        comment_match = COMMENT_PREFIX_RE.match(line)
        if comment_match:
            value = comment_match.group(1).strip()
            if value:
                comment_lines.append(value)
            in_comment = True
            continue

        course_marker = _parse_course_marker(line)
        if course_marker is not None:
            current_course = course_marker
            continue

        course_prefix = _parse_course_prefix(line)
        if course_prefix is not None:
            current_course, line = course_prefix
            parsed_item = _parse_item_line(line)
            if parsed_item:
                items.append(ParsedItem(quantity=parsed_item.quantity, name=parsed_item.name, course=current_course))
            elif line:
                items.append(ParsedItem(quantity=Decimal("1"), name=line, course=current_course))
            continue

        parsed_item = _parse_item_line(line)
        if parsed_item:
            items.append(ParsedItem(quantity=parsed_item.quantity, name=parsed_item.name, course=current_course))
            continue

        if COMMENT_HINT_RE.match(line):
            comment_lines.append(line)
            continue

        if _looks_like_order_context(lines, index, table_number, items):
            items.append(ParsedItem(quantity=Decimal("1"), name=line, course=current_course))
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
    item_lines = _render_items_by_course(parsed.items)
    comment = parsed.comment or "нет"
    return f"Стол: {table}\n\nПозиции:\n{item_lines}\n\nКомм:\n{comment}"


def format_item(name: str, quantity: Decimal) -> str:
    return f"{name} {format_quantity(quantity)}"


def _parse_item_line(line: str) -> ParsedItem | None:
    trailing_match = TRAILING_QUANTITY_RE.match(line)
    if trailing_match:
        name, quantity_raw = trailing_match.groups()
        quantity = _parse_quantity(quantity_raw)
        if quantity is not None and name.strip():
            return ParsedItem(quantity=quantity, name=name.strip())

    leading_match = LEADING_QUANTITY_RE.match(line)
    if leading_match:
        quantity_raw, name = leading_match.groups()
        quantity = _parse_quantity(quantity_raw)
        if quantity is not None and name.strip():
            return ParsedItem(quantity=quantity, name=name.strip())
    return None


def _parse_course_marker(line: str) -> int | None:
    normalized = line.strip().lower().replace("ё", "е")
    word_markers = {
        "первый курс": 1,
        "первое": 1,
        "первая подача": 1,
        "второй курс": 2,
        "второе": 2,
        "вторая подача": 2,
    }
    if normalized in word_markers:
        return word_markers[normalized]

    match = COURSE_MARKER_RE.match(normalized)
    if not match:
        return None
    return int(next(group for group in match.groups() if group))


def _parse_course_prefix(line: str) -> tuple[int, str] | None:
    match = COURSE_PREFIX_RE.match(line.strip())
    if not match:
        return None
    course = int(match.group(1) or match.group(3))
    item_text = (match.group(2) or match.group(4)).strip()
    return course, item_text


def _looks_like_order_context(lines: list[str], index: int, table_number: str | None, items: list[ParsedItem]) -> bool:
    if table_number or items:
        return True
    if len(lines) <= 1:
        return False
    remaining_lines = lines[index + 1 :]
    return any(candidate and (_parse_item_line(candidate) is not None or TABLE_RE.match(candidate)) for candidate in remaining_lines)


def _parse_quantity(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value


def _render_items_by_course(items: list[ParsedItem]) -> str:
    if not items:
        return "-"

    lines: list[str] = []
    current_course: int | None = None
    for item in items:
        if item.course != current_course:
            if lines:
                lines.append("")
            current_course = item.course
            lines.append(f"К{current_course}")
        lines.append(f"• {format_item(item.name, item.quantity)}")
    return "\n".join(lines)
