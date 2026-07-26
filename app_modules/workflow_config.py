from __future__ import annotations

from app_modules.route_registry import (
    EDIT_STAGE,
    EXPORT_STAGE,
    INPUT_STAGE,
    PICTURES_STAGE,
    SUPPORTED_WORKFLOW_STAGES,
)

FLOW_STAGES = SUPPORTED_WORKFLOW_STAGES
STAGE_LABELS = {
    INPUT_STAGE: "Paste text",
    EDIT_STAGE: "Edit itinerary",
    PICTURES_STAGE: "Add pictures",
    EXPORT_STAGE: "Create PDF",
}
STAGE_COPY = {
    INPUT_STAGE: {
        "headline": "Create a premium itinerary",
        "subtitle": "Paste supplier text, generate the itinerary, edit the document, add real destination pictures, then export the final PDF.",
        "panel_title": "Paste supplier text",
        "panel_text": "Copy the full supplier table or messy itinerary rows and paste them below. The app will build the editable itinerary on the next page.",
    },
    EDIT_STAGE: {
        "subtitle": "Edit the generated itinerary directly. Pictures stay off until the text is ready.",
        "panel_title": "Edit the itinerary",
        "panel_text": "Work directly in the generated document. When the text is ready, add destination pictures from the real image bank.",
    },
    PICTURES_STAGE: {
        "subtitle": "Review the same editable itinerary with automatically selected destination pictures.",
        "panel_title": "Review pictures",
        "panel_text": "The itinerary now includes automatic image selections. Replace weak matches, remove unwanted pictures, then create the PDF.",
    },
    EXPORT_STAGE: {
        "subtitle": "Create the PDF, then download the finished file.",
        "panel_title": "Create the final PDF",
        "panel_text": "The current saved document and picture choices are used for export. The ready panel keeps the download available, and if the PDF is already up to date, the existing download is reused.",
    },
}

CALCULATOR_COPY = {
    "panel_title": "Calculate itinerary",
    "panel_text": "Build calculation rows in an Excel-like grid, use Travel element cell suggestions, download the calculation workbook, or generate an itinerary from the calculated rows.",
}
