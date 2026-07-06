"""Shared Streamlit design tokens."""

CSS = r"""
:root {
    --app-bg: #f5f2ea;
    --paper: #fffdf8;
    --surface: #ffffff;
    --surface-soft: #f7f3eb;
    --surface-muted: #ede8de;
    --ink: #242522;
    --ink-soft: #5b5d58;
    --muted: #7d7c74;
    --line: #e4ded2;
    --line-strong: #cfc6b7;
    --sumi: #2f302d;
    --sumi-2: #444640;
    --accent: #817769;
    --accent-dark: #5f574d;
    --accent-soft: #eee9df;
    --sand: #e8dfcf;
    --sand-2: #faf6ee;
    --red: #b9685f;
    --red-dark: #954d46;
    --warning: #8d7045;
    --danger: #954d46;
    --success: #676f73;
    --action: #2f302d;
    --action-hover: #20211f;
    --action-soft: #efebe2;
    --shadow-soft: 0 24px 70px rgba(36, 37, 34, 0.08);
    --shadow-card: 0 12px 36px rgba(36, 37, 34, 0.055);
    --shadow-control: 0 1px 2px rgba(36, 37, 34, 0.055);
    --radius-card: 24px;
    --radius-control: 14px;

    /* Compatibility aliases for older CSS modules. These now point to the
       quiet stone/ink palette rather than the former green accent. */
    --teal: var(--accent);
    --teal-dark: var(--accent-dark);
    --teal-soft: var(--accent-soft);
}
"""
