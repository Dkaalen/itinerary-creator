"""Small shared helpers for inclusion summary rendering."""


def clean(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def clean_multiline(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in text:
        return clean(text)
    lines = [clean(line) for line in text.split("\n") if clean(line)]
    return "\n".join(lines)


def add_unique(items: list[str], item: str) -> None:
    clean_item = clean_multiline(item)
    if clean_item and clean_item not in items:
        items.append(clean_item)


def join_detail_parts(parts: list[str]) -> str:
    clean_parts = [clean(part).strip(" ,") for part in parts if clean(part).strip(" ,")]
    if not clean_parts:
        return ""
    if len(clean_parts) == 1:
        return clean_parts[0]
    return ", ".join(clean_parts[:-1]) + f" and {clean_parts[-1]}"
