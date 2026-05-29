"""Compatibility facade for PDF page renderers."""

from .render_flowables import *  # noqa: F401,F403
from .render_text import text_with_line_breaks as _text_with_line_breaks, li_text_with_line_breaks as _li_text_with_line_breaks
from .render_cover import *  # noqa: F401,F403
from .render_glance import *  # noqa: F401,F403
from .render_content import *  # noqa: F401,F403

# Preserve the private helper name used by the package __init__ and tests.
from .render_content import _activity_time_range_text  # noqa: F401
