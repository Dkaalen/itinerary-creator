import html as html_lib


def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def para_text(value):
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    return "<br/>".join(html_lib.escape(line) for line in lines)


def has_class(tag, class_name):
    classes = tag.get("class") or []
    return class_name in classes


def para_text_with_breaks(value):
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.replace("\xa0", " ").split()) for line in text.split("\n")]
    return "<br/>".join(html_lib.escape(line) for line in lines if line)
