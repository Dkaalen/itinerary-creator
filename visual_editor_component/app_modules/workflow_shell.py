"""Compatibility shim for old workflow shell imports.

The active app no longer renders the old workflow card grid. Project metrics
and title helpers still live in ``app_modules.workflow_shell``.
"""

from app_modules.workflow_shell import (  # noqa: F401
    build_project_metrics,
    project_route_label,
    project_title,
)
