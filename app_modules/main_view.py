from __future__ import annotations

from html import escape

import streamlit as st
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.diagnostics_panel import render_itinerary_health_report_panel, render_parser_diagnostics_panel
from ui.input_review_panel import render_structured_input_review_panel
from ui.export_files import save_html_file
from ui.render_cache import make_render_signature
from ui.output_edits import (
    apply_output_edits,
    mark_output_dirty,
)
from ui.picture_workflow import pictures_are_added
from itinerary_generation.common import group_rows_by_day
from visual_editor_component.editor_workflow import render_visual_editor

from app_modules.editor_commit import (
    ADD_PICTURES_COMMIT_REQUEST_KEY,
    add_pictures_editor_commit_ready,
    clear_add_pictures_editor_commit_request,
    request_add_pictures_editor_commit,
)
from app_modules.export_step import (
    render_export_step,
    render_pdf_download_station,
    request_pdf_creation_after_visual_editor_commit,
)
from app_modules.project_io import load_project_json, rebuild_current_preview, reset_project_state
from app_modules.validation_gate import (
    block_generation,
    render_blocking_issues,
    render_warning_issues,
)
from app_modules.workflow_shell import build_project_metrics, project_route_label, project_title
from app_modules.workflow_actions import (
    enter_export_stage,
    enter_picture_stage,
    generate_itinerary,
    retry_image_bank_connection,
)
from app_modules.workflow_state import (
    image_grouped_days_from_state,
    session_stage_from_state,
    set_workflow_stage,
)
from images.app_image_selection import (
    audit_day_image_matches,
    connect_remote_image_bank_if_missing,
    destination_requests_from_rows,
    image_bank_status,
    select_day_images_with_overrides,
)
from app_modules.image_bank_status_cache import (
    get_cached_image_bank_status,
    store_image_bank_status,
)


FLOW_STAGES = ("input", "edit", "pictures", "export")
STAGE_LABELS = {
    "input": "Paste text",
    "edit": "Edit itinerary",
    "pictures": "Add pictures",
    "export": "Create PDF",
}
STAGE_COPY = {
    "input": {
        "headline": "Create a premium itinerary",
        "subtitle": "Paste supplier text, generate the itinerary, edit the document, add real destination pictures, then export the final PDF.",
        "panel_title": "Paste supplier text",
        "panel_text": "Copy the full supplier table or messy itinerary rows and paste them below. The app will build the editable itinerary on the next page.",
    },
    "edit": {
        "subtitle": "Edit the generated itinerary directly. Pictures stay off until the text is ready.",
        "panel_title": "Edit the itinerary",
        "panel_text": "Work directly in the generated document. When the text is ready, add destination pictures from the real image bank.",
    },
    "pictures": {
        "subtitle": "Review the same editable itinerary with automatically selected destination pictures.",
        "panel_title": "Review pictures",
        "panel_text": "The itinerary now includes automatic image selections. Replace weak matches, remove unwanted pictures, then create the PDF.",
    },
    "export": {
        "subtitle": "Run final export checks, create the PDF, then download the finished file.",
        "panel_title": "Create the final PDF",
        "panel_text": "The current document and picture choices are used for export. Create PDF applies pending page edits first, then the ready panel keeps the download available. If the PDF already up to date, the existing download is reused.",
    },
}


def _session_stage() -> str:
    return session_stage_from_state(st.session_state)


def _set_stage(stage: str) -> None:
    set_workflow_stage(st.session_state, stage)


def _stage_panel(title: str, body: str) -> None:
    st.html(
        '<div class="document-stage-panel">'
        f'<h2>{escape(title)}</h2>'
        f'<p>{escape(body)}</p>'
        '</div>'
    )


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
    st.html(f'<div class="flow-nav" aria-label="Itinerary workflow">{"".join(items)}</div>')


def _render_app_header(app_version: str, *, stage: str) -> None:
    metrics = build_project_metrics(
        st.session_state.get("parsed_rows", []),
        st.session_state.get("output_edits", {}),
    )
    title = project_title(st.session_state.get("output_edits", {}), "Create itinerary")
    copy = STAGE_COPY[stage]
    headline = copy.get("headline") or title
    subtitle = copy["subtitle"]

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
    result = generate_itinerary(st.session_state, raw_text)
    if not result.ok:
        validation_report = (result.payload or {}).get("validation_report")
        if validation_report is not None:
            block_generation(validation_report)
            render_blocking_issues(validation_report)
        return False
    return True


def _render_generation_messages() -> None:
    render_structured_input_review_panel(
        st.session_state.get("parsed_rows", []),
        st.session_state.get("parser_diagnostics", []),
        st.session_state.get("structured_input_review"),
    )
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
    _stage_panel(STAGE_COPY["input"]["panel_title"], STAGE_COPY["input"]["panel_text"])

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



def _current_image_bank_requests():
    return destination_requests_from_rows(image_grouped_days_from_state(st.session_state))


def _current_image_bank_status() -> dict:
    requests = _current_image_bank_requests()
    return get_cached_image_bank_status(st.session_state, requests, image_bank_status)


def _connect_current_image_bank() -> dict:
    requests = _current_image_bank_requests()
    status = connect_remote_image_bank_if_missing(requests)
    return store_image_bank_status(st.session_state, requests, status)


def _image_status_notice() -> None:
    status = _current_image_bank_status()
    if status.get("full_bank_found"):
        covered = len(status.get("covered_destinations", []))
        required = len(status.get("required_destinations", []))
        suffix = f" across {covered}/{required} itinerary destinations" if required else ""
        st.success(f"Image bank connected: {status.get('destination_image_count', 0)} destination pictures available{suffix}.")
    else:
        st.error(status.get("blocking_message") or "Full destination image bank is missing.")
        st.caption("Default pictures are fallback placeholders only. They are not approved for final PDF export unless explicitly allowed.")


def _image_bank_gateway_is_blocking(result: dict | None) -> bool:
    return bool(isinstance(result, dict) and result and not result.get("ready"))


def _render_image_bank_gateway_repair(result: dict | None = None) -> None:
    result = result or st.session_state.get("image_bank_gateway") or {}
    status = result.get("status") if isinstance(result.get("status"), dict) else _current_image_bank_status()
    setup_status = result.get("setup_status") if isinstance(result.get("setup_status"), dict) else status.get("setup_status", {})
    message = result.get("message") or status.get("blocking_message") or "Full destination image bank is missing."

    st.html(
        '<div class="image-bank-repair-panel">'
        '<strong>Image bank connection required</strong>'
        '<span>Add Pictures cannot continue with only bundled Default placeholders. Connect the real destination image bank first.</span>'
        '</div>'
    )
    st.error(message)
    st.caption("Expected source: Dkaalen/itinerary-image-bank/image_bank_full. Default pictures remain emergency placeholders only.")

    if setup_status and (setup_status.get("error") or setup_status.get("git_error") or setup_status.get("code")):
        with st.expander("Image-bank setup details", expanded=False):
            st.json({
                "code": setup_status.get("code", ""),
                "method": setup_status.get("method", ""),
                "repo_url": setup_status.get("repo_url", status.get("repo_url", "")),
                "manifest_url": setup_status.get("manifest_url", status.get("manifest_url", "")),
                "zip_url": setup_status.get("zip_url", status.get("zip_url", "")),
                "error": setup_status.get("error", ""),
                "git_error": setup_status.get("git_error", ""),
                "requested_destinations": setup_status.get("requested_destinations", status.get("required_destinations", [])),
                "installed_destinations": setup_status.get("installed_destinations", []),
                "unresolved_destinations": setup_status.get("unresolved_destinations", []),
                "download_errors": setup_status.get("errors", []),
                "paths": status.get("paths", []),
            })

    if st.button("Retry image-bank connection", use_container_width=True):
        with st.spinner("Preparing the required destination image packs…"):
            retry = retry_image_bank_connection(st.session_state, _current_image_bank_status, _connect_current_image_bank)
        if retry.ok:
            st.success("Image bank connected. Click Add pictures again to select destination images.")
        st.rerun()


def _activate_picture_stage() -> bool:
    result = enter_picture_stage(
        st.session_state,
        status_func=_current_image_bank_status,
        connect_func=_connect_current_image_bank,
        select_images_func=select_day_images_with_overrides,
        audit_images_func=audit_day_image_matches,
        rebuild_preview_func=rebuild_current_preview,
    )
    return result.ok


def _add_pictures_apply_ready() -> bool:
    return add_pictures_editor_commit_ready(st.session_state)


def _add_pictures_apply_pending() -> bool:
    return bool(st.session_state.get(ADD_PICTURES_COMMIT_REQUEST_KEY)) and not _add_pictures_apply_ready()


def render_edit_page(app_version: str) -> None:
    _render_app_header(app_version, stage="edit")
    _render_generation_messages()
    _render_stage_actions("edit")
    _stage_panel(STAGE_COPY["edit"]["panel_title"], STAGE_COPY["edit"]["panel_text"])

    was_waiting_for_apply = _add_pictures_apply_pending()
    if not _add_pictures_apply_ready():
        _render_document_editor(pictures_active=False)
        if was_waiting_for_apply and _add_pictures_apply_ready():
            st.rerun()

    st.html('<div class="bottom-cta"><div><strong>Text ready?</strong><span>Apply the current preview changes, then add destination pictures from the committed itinerary.</span></div></div>')
    gateway_result = st.session_state.get("image_bank_gateway")
    if _image_bank_gateway_is_blocking(gateway_result):
        _render_image_bank_gateway_repair(gateway_result)
        return

    apply_ready = _add_pictures_apply_ready()
    apply_pending = _add_pictures_apply_pending()

    if apply_ready:
        st.success("Changes applied. Add pictures is ready to run from the committed itinerary.")
        left, right = st.columns(2)
        with left:
            if st.button("Edit again", use_container_width=True):
                clear_add_pictures_editor_commit_request(st.session_state)
                st.rerun()
        with right:
            if st.button("Add pictures", type="primary", use_container_width=True):
                with st.spinner("Preparing destination pictures and finding the best matches…"):
                    _activate_picture_stage()
                st.rerun()
        return

    if apply_pending:
        st.info("Applying preview changes before pictures can be added…")
        st.button("Add pictures", disabled=True, use_container_width=True)
        return

    if st.button("Apply Changes", type="primary", use_container_width=True):
        request_add_pictures_editor_commit(st.session_state)
        st.rerun()
    st.button("Add pictures", disabled=True, use_container_width=True)
    st.caption("Apply changes before adding pictures so image matching uses the latest committed itinerary.")


def render_final_preview_step():
    """Legacy hook retained so older UI regression tests find the new boundary."""
    return None


def render_picture_page(app_version: str) -> None:
    _render_app_header(app_version, stage="pictures")
    _render_stage_actions("pictures")
    render_pdf_download_station(location="top")
    status = _current_image_bank_status()
    if not status.get("required_destinations_ready", not status.get("missing_full_bank")):
        st.session_state["image_bank_gateway"] = {
            "ready": False,
            "status": status,
            "message": status.get("blocking_message", ""),
        }
        _render_image_bank_gateway_repair(st.session_state.get("image_bank_gateway"))
        return
    _image_status_notice()
    _stage_panel(STAGE_COPY["pictures"]["panel_title"], STAGE_COPY["pictures"]["panel_text"])
    _render_document_editor(pictures_active=True)

    st.html('<div class="bottom-cta"><div><strong>Pictures reviewed?</strong><span>Create the final PDF from the current document.</span></div></div>')
    if st.button("Create PDF", type="primary", use_container_width=True):
        enter_export_stage(st.session_state, request_pdf_commit_func=request_pdf_creation_after_visual_editor_commit)
        st.rerun()


def render_export_page(app_version: str) -> None:
    _render_app_header(app_version, stage="export")
    _render_stage_actions("export")
    render_pdf_download_station(location="top")
    status = _current_image_bank_status()
    if not status.get("required_destinations_ready", not status.get("missing_full_bank")):
        st.session_state["image_bank_gateway"] = {
            "ready": False,
            "status": status,
            "message": status.get("blocking_message", ""),
        }
        _render_image_bank_gateway_repair(st.session_state.get("image_bank_gateway"))
        return
    _image_status_notice()
    _stage_panel(STAGE_COPY["export"]["panel_title"], STAGE_COPY["export"]["panel_text"])
    _render_document_editor(pictures_active=True)

    st.html('<div class="bottom-cta"><div><strong>Ready to deliver?</strong><span>Create or download the final PDF.</span></div></div>')
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
    elif stage == "export":
        render_export_page(app_version)
    else:
        render_input_page(app_version)

    render_debug_tools()
