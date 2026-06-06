from __future__ import annotations

from html import escape

import streamlit as st
import diagnostics

from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.diagnostics_panel import render_itinerary_health_report_panel, render_parser_diagnostics_panel
from ui.export_files import save_html_file
from ui.render_cache import make_render_signature
from ui.output_edits import (
    apply_output_edits,
    apply_rich_writing_to_all_days,
    make_output_edit_state,
    mark_output_dirty,
)
from ui.picture_workflow import pictures_are_added, set_pictures_added
from itinerary_generation.common import group_rows_by_day, is_optional_row
from visual_editor_component.editor_workflow import render_visual_editor

from app_modules.itinerary_html import build_itinerary_html
from app_modules.export_step import render_export_step, render_pdf_download_station
from app_modules.parse_workflow import parse_and_normalize_itinerary, get_duplicate_count, get_overflow_warnings
from app_modules.project_io import load_project_json, rebuild_current_preview, reset_project_state
from app_modules.validation_gate import (
    block_generation,
    render_blocking_issues,
    render_warning_issues,
    validate_for_generation,
)
from app_modules.workflow_shell import build_project_metrics, project_route_label, project_title
from images.app_image_selection import (
    audit_day_image_matches,
    connect_remote_image_bank_if_missing,
    image_bank_status,
    select_day_images_with_overrides,
)


FLOW_STAGES = ("input", "edit", "pictures", "export")
STAGE_LABELS = {
    "input": "Paste text",
    "edit": "Edit itinerary",
    "pictures": "Review pictures",
    "export": "Create PDF",
}


def _session_stage() -> str:
    stage = str(st.session_state.get("app_stage", "input") or "input")
    if stage not in FLOW_STAGES:
        stage = "input"
    if not st.session_state.get("parsed_rows"):
        return "input"
    if stage == "pictures" and not pictures_are_added(st.session_state.get("output_edits", {})):
        return "edit"
    if stage == "export" and not pictures_are_added(st.session_state.get("output_edits", {})):
        return "edit"
    return stage


def _set_stage(stage: str) -> None:
    if stage in FLOW_STAGES:
        st.session_state["app_stage"] = stage


def _render_top_nav(stage: str) -> None:
    current_index = FLOW_STAGES.index(stage)
    items = []
    for index, item in enumerate(FLOW_STAGES):
        status = "done" if index < current_index else "current" if item == stage else "locked"
        items.append(
            f'<div class="flow-nav-item flow-nav-{status}">'
            f'<span>{index + 1}</span><strong>{escape(STAGE_LABELS[item])}</strong>'
            f'</div>'
        )
    st.html(f'<div class="flow-nav">{"".join(items)}</div>')


def _render_app_header(app_version: str, *, stage: str) -> None:
    metrics = build_project_metrics(
        st.session_state.get("parsed_rows", []),
        st.session_state.get("output_edits", {}),
    )
    title = project_title(st.session_state.get("output_edits", {}), "Create itinerary")
    if stage == "input":
        headline = "Create a client-ready itinerary"
        subtitle = "Paste supplier text, generate the itinerary, edit the document, add real destination pictures, then export the final PDF."
    elif stage == "edit":
        headline = title
        subtitle = "Edit the generated client itinerary directly. Pictures stay off until the text is ready."
    elif stage == "pictures":
        headline = title
        subtitle = "Review the same editable itinerary with automatically selected destination pictures."
    else:
        headline = title
        subtitle = "Run the final quality checks, create the PDF, then download the client-ready file."

    route = project_route_label(metrics)
    duration = f"{metrics['days']} days" if metrics["days"] else "Not generated yet"
    image_status = "Pictures added" if metrics["pictures_added"] else "Text only"
    pdf_status = str(st.session_state.get("pdf_status", "Not created") or "Not created")

    st.html(
        '<div class="luxury-hero">'
        '<div class="luxury-hero-main">'
        '<div class="hero-eyebrow">Itinerary App</div>'
        f'<h1>{escape(headline)}</h1>'
        f'<p>{escape(subtitle)}</p>'
        '</div>'
        '<div class="hero-summary-card">'
        f'<div><span>Route</span><strong>{escape(route)}</strong></div>'
        f'<div><span>Duration</span><strong>{escape(duration)}</strong></div>'
        f'<div><span>Imagery</span><strong>{escape(image_status)}</strong></div>'
        f'<div><span>PDF</span><strong>{escape(pdf_status)}</strong></div>'
        '</div>'
        '</div>'
        f'<div class="app-version-pill">Version {escape(str(app_version))}</div>'
    )
    _render_top_nav(stage)


def _generate_itinerary(raw_text: str) -> bool:
    diagnostics.reset()
    parsed_rows = parse_and_normalize_itinerary(raw_text)
    validation_report = validate_for_generation(parsed_rows)
    if validation_report.is_blocked:
        block_generation(validation_report)
        st.session_state.parser_diagnostics = diagnostics.get_warnings()
        render_blocking_issues(validation_report)
        return False

    grouped_days = group_rows_by_day(parsed_rows)
    duplicate_count = get_duplicate_count(raw_text, parsed_rows)

    st.session_state.parsed_rows = parsed_rows
    st.session_state.output_edits = make_output_edit_state(parsed_rows, grouped_days)
    st.session_state.output_edits = apply_rich_writing_to_all_days(parsed_rows, st.session_state.output_edits)
    st.session_state.output_edits["allow_default_final_images"] = False
    st.session_state.last_generated_raw_text = raw_text
    st.session_state.pdf_bytes = None
    st.session_state.export_pdf_bytes = None
    st.session_state.pdf_signature = None
    st.session_state.export_pdf_signature = None
    st.session_state.pdf_status = "Not created"
    st.session_state.parser_diagnostics = diagnostics.get_warnings()
    st.session_state.itinerary_validation_report = validation_report

    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    st.session_state.itinerary_html = build_itinerary_html(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
    )
    st.session_state.preview_signature = make_render_signature(st.session_state.parsed_rows, st.session_state.output_edits)
    st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

    st.session_state["generation_duplicate_count"] = duplicate_count
    st.session_state["generation_overflow_warnings"] = get_overflow_warnings(edited_grouped_days)
    return True


def _render_generation_messages() -> None:
    duplicate_count = st.session_state.get("generation_duplicate_count", 0)
    if duplicate_count:
        st.warning(f"Skipped approximately {duplicate_count} duplicate, continuation, or malformed row(s).")
    for warning in st.session_state.get("generation_overflow_warnings", []) or []:
        st.warning(warning)
    validation_report = st.session_state.get("itinerary_validation_report")
    if validation_report:
        render_warning_issues(validation_report)


def render_input_page(app_version: str) -> None:
    _render_app_header(app_version, stage="input")

    st.html(
        '<div class="start-panel">'
        '<div><div class="section-kicker">Step 1</div><h2>Paste supplier text</h2>'
        '<p>Copy the full supplier table or messy itinerary rows and paste them below. The app will build the client itinerary on the next page.</p></div>'
        '</div>'
    )

    raw_text = st.text_area(
        "Supplier text",
        height=430,
        placeholder="Paste itinerary rows here…",
        key="raw_text_input",
        label_visibility="collapsed",
    )

    if st.button("Generate Itinerary", type="primary", use_container_width=True):
        if not raw_text.strip():
            st.warning("Please paste supplier text first.")
            return
        with st.spinner("Building your itinerary…"):
            generated = _generate_itinerary(raw_text)
        if generated:
            _set_stage("edit")
            st.rerun()

    with st.container(border=True):
        st.markdown("**Load saved project**")
        uploaded_project = st.file_uploader("Load editable project JSON", type=["json"], label_visibility="collapsed")
        if uploaded_project is not None and st.button("Load project", use_container_width=True):
            load_project_json(uploaded_project)
            _set_stage("pictures" if pictures_are_added(st.session_state.get("output_edits", {})) else "edit")
            st.rerun()


def _render_stage_actions(stage: str) -> None:
    left, right = st.columns([1, 1])
    with left:
        if st.button("Start over", use_container_width=True):
            reset_project_state(clear_raw_text=True)
            _set_stage("input")
            st.rerun()
    with right:
        if stage != "input" and st.button("Refresh itinerary", use_container_width=True):
            rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
            st.success("Itinerary refreshed.")
            st.rerun()


def _render_document_editor(*, pictures_active: bool) -> None:
    if not (st.session_state.get("parsed_rows") and st.session_state.get("output_edits")):
        return

    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)

    editor_applied = render_visual_editor(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
        rebuild_preview=rebuild_current_preview,
        mark_dirty=mark_output_dirty,
    )
    if editor_applied:
        return

    render_signature = make_render_signature(st.session_state.parsed_rows, st.session_state.output_edits)
    preview_is_current = (
        bool(st.session_state.get("itinerary_html", ""))
        and st.session_state.get("preview_signature") == render_signature
    )
    if not preview_is_current:
        rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
    elif not st.session_state.get("html_path"):
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)


def _image_grouped_days() -> dict:
    grouped_days = group_rows_by_day(st.session_state.get("parsed_rows", []) or [])
    return {
        day: [row for row in rows if not is_optional_row(row)] or list(rows)
        for day, rows in grouped_days.items()
    }


def _image_status_notice() -> None:
    status = image_bank_status()
    if status.get("full_bank_found"):
        st.success(f"Image bank connected: {status.get('destination_image_count', 0)} destination pictures available.")
    else:
        st.error(status.get("blocking_message") or "Full destination image bank is missing.")
        st.caption("Default pictures are fallback placeholders only. They are not approved for final client output unless explicitly allowed.")


def _activate_picture_stage() -> None:
    status = image_bank_status()
    if status.get("missing_full_bank"):
        status = connect_remote_image_bank_if_missing()
    st.session_state["image_bank_status"] = status
    st.session_state.output_edits["allow_default_final_images"] = False
    set_pictures_added(st.session_state.output_edits, True)

    matches = select_day_images_with_overrides(_image_grouped_days(), st.session_state.output_edits)
    warnings = audit_day_image_matches(_image_grouped_days(), matches, st.session_state.output_edits)
    st.session_state["image_review_warning_count"] = len([warning for warning in warnings if warning.severity == "error"])

    st.session_state.pdf_bytes = None
    st.session_state.export_pdf_bytes = None
    st.session_state.pdf_signature = None
    st.session_state.export_pdf_signature = None
    st.session_state.pdf_status = "Needs refresh"
    rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
    _set_stage("pictures")


def render_edit_page(app_version: str) -> None:
    _render_app_header(app_version, stage="edit")
    _render_generation_messages()
    _render_stage_actions("edit")

    st.html(
        '<div class="editor-stage-intro">'
        '<div><div class="section-kicker">Step 2</div><h2>Edit the itinerary</h2>'
        '<p>Work directly in the generated document. Keep pictures off until the text and layout feel ready.</p></div>'
        '</div>'
    )
    _render_document_editor(pictures_active=False)

    st.html('<div class="bottom-cta"><div><strong>Text ready?</strong><span>Add destination pictures and return to the top for visual review.</span></div></div>')
    if st.button("Add pictures", type="primary", use_container_width=True):
        with st.spinner("Finding best images…"):
            status = image_bank_status()
            if status.get("missing_full_bank"):
                status = connect_remote_image_bank_if_missing()
            st.session_state["image_bank_status"] = status
            st.session_state.output_edits["allow_default_final_images"] = False
            set_pictures_added(st.session_state.output_edits, True)
            st.session_state["_add_pictures_after_visual_edit_commit_nonce"] = None
            st.session_state["_visual_editor_add_pictures_commit_ready"] = False
            st.session_state["_visual_editor_commit_nonce"] = None
            matches = select_day_images_with_overrides(_image_grouped_days(), st.session_state.output_edits)
            warnings = audit_day_image_matches(_image_grouped_days(), matches, st.session_state.output_edits)
            st.session_state["image_review_warning_count"] = len([warning for warning in warnings if warning.severity == "error"])
            st.session_state.pdf_bytes = None
            st.session_state.export_pdf_bytes = None
            st.session_state.pdf_signature = None
            st.session_state.export_pdf_signature = None
            st.session_state.pdf_status = "Needs refresh"
            rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
            _set_stage("pictures")
        st.rerun()


def render_final_preview_step():
    """Legacy hook retained so older UI regression tests find the new boundary."""
    return None


def render_picture_page(app_version: str) -> None:
    _render_app_header(app_version, stage="pictures")
    _render_stage_actions("pictures")
    render_pdf_download_station(location="top")
    _image_status_notice()

    st.html(
        '<div class="editor-stage-intro">'
        '<div><div class="section-kicker">Step 3</div><h2>Review pictures</h2>'
        '<p>The itinerary now includes automatic image selections. Replace weak matches, remove unwanted pictures, then create the PDF at the bottom.</p></div>'
        '</div>'
    )
    _render_document_editor(pictures_active=True)

    st.html('<div class="bottom-cta"><div><strong>Pictures reviewed?</strong><span>Create the final client PDF from the current document.</span></div></div>')
    render_export_step(app_version)


def render_debug_tools() -> None:
    with st.container(border=True):
        show_debug = st.checkbox("Show parser/debug panels", value=False)
        if not show_debug:
            return
        render_parser_diagnostics_panel()
        render_itinerary_health_report_panel(
            st.session_state.get("parsed_rows", []),
            st.session_state.get("itinerary_validation_report"),
        )
        if st.session_state.get("parsed_rows"):
            st.dataframe(st.session_state.parsed_rows, use_container_width=True)


def render_app(app_version: str) -> None:
    st.session_state.setdefault("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    stage = _session_stage()
    if stage == "input":
        render_input_page(app_version)
    elif stage == "edit":
        render_edit_page(app_version)
    elif stage == "pictures":
        render_picture_page(app_version)
    else:
        render_picture_page(app_version)

    render_debug_tools()
