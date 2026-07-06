"""Shared Streamlit design tokens."""

CSS = r"""
:root {
    --app-bg: #f8f6f1;
    --paper: #fffdf8;
    --surface: #ffffff;
    --surface-soft: #f6f2ea;
    --surface-muted: #ebe5da;
    --ink: #242522;
    --ink-soft: #60625d;
    --muted: #85827a;
    --line: #e0d8ca;
    --line-strong: #c7bcaa;
    --sumi: #2f302d;
    --sumi-2: #444640;
    --accent: #9a8f7f;
    --accent-dark: #6f665b;
    --accent-soft: #eee9df;
    --sand: #e8dfcf;
    --sand-2: #faf6ee;
    --red: #b9685f;
    --red-dark: #954d46;
    --warning: #8d7045;
    --danger: #954d46;
    --success: #676f73;
    --action: #e6ded1;
    --action-hover: #ddd3c4;
    --action-text: #242522;
    --action-soft: #f1ede6;
    --shadow-soft: 0 18px 52px rgba(36, 37, 34, 0.06);
    --shadow-card: 0 10px 28px rgba(36, 37, 34, 0.045);
    --shadow-control: 0 1px 2px rgba(36, 37, 34, 0.045);
    --radius-card: 18px;
    --radius-control: 10px;

    /* Compatibility aliases for older CSS modules. These intentionally point to
       quiet stone/taupe values rather than the former saturated green accent. */
    --teal: var(--accent);
    --teal-dark: var(--accent-dark);
    --teal-soft: var(--accent-soft);
}
"""
