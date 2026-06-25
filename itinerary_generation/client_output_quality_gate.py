"""Client-output quality gate."""

from __future__ import annotations

from itinerary_generation.quality_gate_core import (
    ClientOutputQualityGateReport,
    _meta_lines_with_time_warnings,
    _journey_arc_phrase_issues,
    _bare_activity_blocks,
    evaluate_client_output_quality,
    blocking_client_output_messages,
)

__all__ = ['ClientOutputQualityGateReport', '_meta_lines_with_time_warnings', '_journey_arc_phrase_issues', '_bare_activity_blocks', 'evaluate_client_output_quality', 'blocking_client_output_messages']
