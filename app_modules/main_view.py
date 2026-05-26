from pathlib import Path
import json

import streamlit as st
import diagnostics

from layout_policy import DEFAULT_DAY_PAGE_LAYOUT, DAY_PAGE_LAYOUTS
from ui.app_constants import PRESET_ORDER
from ui.diagnostics_panel import render_parser_diagnostics_panel
from ui.export_files import save_html_file, save_pdf_file
from ui.output_edits import (
    apply_output_edits,
    apply_rich_writing_to_all_days,
    make_output_edit_state,
    mark_output_dirty,
)
from generator import group_rows_by_day
from visual_editor_component.editor_workflow import render_visual_editor

from app_modules.itinerary_html import build_itinerary_html
from app_modules.output_editor import render_output_editor
from app_modules.parse_workflow import parse_and_normalize_itinerary, get_duplicate_count, get_overflow_warnings
from app_modules.project_io import load_project_json, rebuild_current_preview, reset_project_state
from app_modules.sidebar import render_sidebar_snapshot


def render_sidebar_controls():
    with st.sidebar:
        st.subheader("Settings")
        current_preset = st.session_state.get("color_preset", "Classic Agent")
        if current_preset not in PRESET_ORDER:
            current_preset = "Classic Agent"

        selected_preset = st.selectbox(
            "Color preset",
            PRESET_ORDER,
            index=PRESET_ORDER.index(current_preset),
            help="Classic Agent keeps the neutral travel-agent look. Booknordics B2C uses a cleaner branded palette.",
        )
        st.session_state.color_preset = selected_preset

        if selected_preset == "Classic Agent":
            st.caption("Warm, neutral, B2B-friendly.")
        else:
            st.caption("Clean, bright, B2C-friendly.")

        selected_detail = "Rich descriptive"
        previous_detail = "Rich descriptive"
        st.session_state.detail_level = selected_detail
        st.caption("Writing style: warm, full and client-facing.")

        current_day_layout = st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
        if current_day_layout not in DAY_PAGE_LAYOUTS:
            current_day_layout = DEFAULT_DAY_PAGE_LAYOUT

        selected_day_layout = st.selectbox(
            "Day page layout",
            DAY_PAGE_LAYOUTS,
            index=DAY_PAGE_LAYOUTS.index(current_day_layout),
            help="Keeps each itinerary day on its own A4 page, preparing the layout for day imagery.",
        )
        previous_day_layout = st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
        st.session_state.day_page_layout = selected_day_layout
        st.caption("Premium visual layout: one itinerary day per A4 page.")

        if st.session_state.get("output_edits"):
            st.session_state.output_edits["color_preset"] = selected_preset
            st.session_state.output_edits["day_page_layout"] = selected_day_layout
            st.session_state.output_edits["detail_level"] = "Rich descriptive"
            if previous_day_layout != selected_day_layout:
                st.session_state.pdf_bytes = None
                st.session_state.pdf_status = "Needs refresh"

        show_debug = st.checkbox("Show parser/debug panels", value=False)

        st.divider()
        st.subheader("Project")
        uploaded_project = st.file_uploader("Load editable project JSON", type=["json"])

        if uploaded_project is not None and st.button("Load project", use_container_width=True):
            load_project_json(uploaded_project)
            st.rerun()

        st.divider()
        st.subheader("Project actions")
        st.markdown('<div class="project-action-note">Use these when the preview feels out of sync or when you want to start from a clean slate.</div>', unsafe_allow_html=True)

        if st.button("Refresh preview", use_container_width=True, disabled=not bool(st.session_state.get("parsed_rows"))):
            if rebuild_current_preview(mark_pdf_dirty=True):
                st.success("Preview refreshed.")
            st.rerun()

        if st.button("Generate new itinerary", use_container_width=True):
            reset_project_state(clear_raw_text=True)
            st.rerun()

        render_sidebar_snapshot()

    return show_debug


def render_app_hero(app_version):
    st.markdown(
        f"""
        <div class="app-hero">
            <h1>Itinerary Creator</h1>
            <p>Paste itinerary rows, review the generated output, then export a polished A4 itinerary.</p>
            <p style="font-size: 0.85rem; opacity: 0.65; margin-top: 0.4rem;">Version: {app_version}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_input_step():
    with st.expander("Step 1 — Paste raw itinerary text", expanded=not bool(st.session_state.itinerary_html)):
        st.markdown('<div class="workflow-note">Paste the full itinerary table or copied Excel rows here.</div>', unsafe_allow_html=True)
        raw_text = st.text_area(
            "Raw Excel text",
            height=300,
            placeholder="Paste itinerary rows here...",
            key="raw_text_input",
        )

        if st.button("Generate itinerary", type="primary", use_container_width=True):
            if raw_text.strip():
                diagnostics.reset()
                parsed_rows = parse_and_normalize_itinerary(raw_text)
                grouped_days = group_rows_by_day(parsed_rows)
                duplicate_count = get_duplicate_count(raw_text, parsed_rows)

                st.session_state.parsed_rows = parsed_rows
                st.session_state.output_edits = make_output_edit_state(parsed_rows, grouped_days)
                st.session_state.output_edits = apply_rich_writing_to_all_days(parsed_rows, st.session_state.output_edits)
                st.session_state.last_generated_raw_text = raw_text
                st.session_state.pdf_bytes = None
                st.session_state.pdf_status = "Not created"
                st.session_state.parser_diagnostics = diagnostics.get_warnings()

                edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
                edited_grouped_days = group_rows_by_day(edited_rows)
                st.session_state.itinerary_html = build_itinerary_html(
                    edited_rows,
                    edited_grouped_days,
                    st.session_state.output_edits,
                )
                st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

                st.success(f"Parsed {len(parsed_rows)} itinerary rows across {len(grouped_days)} days. Rich day-to-day wording applied automatically.")

                if duplicate_count:
                    st.warning(f"Skipped approximately {duplicate_count} duplicate, continuation, or malformed row(s).")

                overflow_warnings = get_overflow_warnings(edited_grouped_days)
                for warning in overflow_warnings:
                    st.warning(warning)

                if st.session_state.html_path:
                    st.success("HTML preview prepared.")

            else:
                st.warning("Please paste some itinerary text first.")


def render_debug_panels(show_debug):
    if show_debug:
        render_parser_diagnostics_panel()

    if show_debug and st.session_state.parsed_rows:
        with st.expander("Debug tools", expanded=False):
            st.dataframe(st.session_state.parsed_rows, use_container_width=True)
            st.write("Day grouping")
            for day, rows in group_rows_by_day(st.session_state.parsed_rows).items():
                st.write(f"{day}: {len(rows)} rows")
                for row in rows:
                    st.write(
                        f"- {row.get('type')} / {row.get('effective_type')}: "
                        f"{row.get('title')} ({row.get('city')})"
                    )


def render_visual_editor_step():
    if st.session_state.parsed_rows and st.session_state.output_edits:
        edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
        edited_grouped_days = group_rows_by_day(edited_rows)

        with st.expander("Step 2 — Edit proposal directly on A4 pages", expanded=True):
            st.markdown(
                '<div class="workflow-note">Click directly into the A4 pages and type. Use the save button inside the editor before reviewing/exporting.</div>',
                unsafe_allow_html=True,
            )
            render_visual_editor(edited_rows, edited_grouped_days, st.session_state.output_edits, rebuild_preview=rebuild_current_preview, mark_dirty=mark_output_dirty)

        rebuilt_html = build_itinerary_html(
            edited_rows,
            edited_grouped_days,
            st.session_state.output_edits,
        )

        if rebuilt_html != st.session_state.itinerary_html:
            st.session_state.pdf_bytes = None
            if st.session_state.itinerary_html:
                st.session_state.pdf_status = "Needs refresh"
            st.session_state.itinerary_html = rebuilt_html
            st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        elif st.session_state.itinerary_html and not st.session_state.html_path:
            st.session_state.html_path = save_html_file(st.session_state.itinerary_html)


def render_final_preview_step():
    if st.session_state.itinerary_html:
        with st.expander("Step 3 — Review final PDF-style preview", expanded=False):
            st.caption("This preview is not editable. It is the final layout check before PDF export.")
            st.html(st.session_state.itinerary_html)


def render_fallback_editor(show_debug):
    if st.session_state.parsed_rows and st.session_state.output_edits and show_debug:
        with st.expander("Advanced fallback text and image editor", expanded=False):
            render_output_editor(
                st.session_state.parsed_rows,
                group_rows_by_day(apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)),
                st.session_state.output_edits,
            )


def render_export_step(app_version):
    if st.session_state.itinerary_html:
        st.subheader("Step 4 — Export")
        st.markdown('<div class="workflow-note">Save your editable project, download the HTML preview, or create a PDF.</div>', unsafe_allow_html=True)

        html_path = Path(st.session_state.html_path) if st.session_state.html_path else None
        project_data = {
            "app_version": app_version,
            "raw_text": st.session_state.get("last_generated_raw_text", ""),
            "output_edits": st.session_state.get("output_edits", {}),
        }

        export_col_1, export_col_2, export_col_3, export_col_4 = st.columns(4)

        with export_col_1:
            st.download_button(
                "Download project JSON",
                data=json.dumps(project_data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="itinerary_project.json",
                mime="application/json",
                use_container_width=True,
            )

        with export_col_2:
            if html_path and html_path.exists():
                with open(html_path, "rb") as html_file:
                    st.download_button(
                        label="Download HTML",
                        data=html_file,
                        file_name="itinerary_preview.html",
                        mime="text/html",
                        use_container_width=True,
                    )
            else:
                st.button("Download HTML", disabled=True, use_container_width=True)
                st.caption("HTML file not available.")

        with export_col_3:
            if st.button("Create PDF", use_container_width=True):
                try:
                    with st.spinner("Creating PDF..."):
                        pdf_path = save_pdf_file(html_path)
                        if pdf_path is None:
                            st.session_state.pdf_bytes = None
                            st.session_state.pdf_status = "PDF failed"
                        else:
                            st.session_state.pdf_bytes = Path(pdf_path).read_bytes()
                            st.session_state.pdf_status = "Ready"

                    if st.session_state.pdf_bytes:
                        st.success("PDF created. Use the download button.")

                except Exception as error:
                    st.session_state.pdf_status = "PDF failed"
                    st.error(
                        "PDF export failed in this environment. The itinerary preview and HTML download still work."
                    )
                    with st.expander("PDF export error details"):
                        st.exception(error)

        with export_col_4:
            if st.session_state.pdf_bytes:
                st.download_button(
                    label="Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name="itinerary_preview.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button("Download PDF", disabled=True, use_container_width=True)
                st.caption(st.session_state.get("pdf_status", "Not created"))


def render_app(app_version):
    show_debug = render_sidebar_controls()
    render_app_hero(app_version)
    render_input_step()
    render_debug_panels(show_debug)
    render_visual_editor_step()
    render_final_preview_step()
    render_fallback_editor(show_debug)
    render_export_step(app_version)
