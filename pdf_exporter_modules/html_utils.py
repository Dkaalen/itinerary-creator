import html as html_lib


def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def para_text(value):
    return html_lib.escape(clean_text(value))


def has_class(tag, class_name):
    classes = tag.get("class") or []
    return class_name in classes
