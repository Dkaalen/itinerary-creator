"""Compatibility exports for itinerary HTML/day rendering helpers.

The rendering code is split by responsibility into smaller modules. This module
keeps older imports stable while app.py and tests transition module-by-module.
"""

from ui.render_helpers import *  # noqa: F401,F403
from ui.day_blocks import *  # noqa: F401,F403
from ui.day_pages import *  # noqa: F401,F403
from ui.final_pages import *  # noqa: F401,F403
