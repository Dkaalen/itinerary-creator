from pathlib import Path
import json

import streamlit as st

from ui.export_files import save_pdf_file
from ui.output_edits import apply_output_edits
from app_modules.project_io import rebuild_current_preview
from ui.picture_workflow import pictures_are_added
from itinerary_generation.common import group_rows_by_day, is_optional_row
from itinerary_generation.output_contract import validate_output_layout_contract
from itinerary_generation.quality_gate import evaluate_client_output_quality
from app_modules.validation_gate import block_generation, render_blocking_issues, validate_for_generation
from app_modules.itinerary_render_context import build_itinerary_render_context
from images.app_image_selection import audit_day_image_matches, connect_remote_image_bank_if_missing, get_day_image_crop_focus, image_bank_status, select_day_images_with_overrides


def render_export_step(app_version):
    if st.session_state.itinerary_html:
        st.subheader("Step 5 — Export")
        st.markdown('<div class="workflow-note">Download your editable project, download the HTML preview, or create a PDF. Create PDF applies pending page/image edits first.</div>', unsafe_allow_html=True)

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
            requested_commit_nonce = st.session_state.get("_pdf_after_visual_edit_commit_nonce")
            commit_ready = (
                requested_commit_nonce
                and st.session_state.get("_visual_editor_export_commit_ready")
                and str(st.session_state.get("_visual_editor_last_applied_commit_nonce", "")) == str(requested_commit_nonce)
            )

            pictures_added = pictures_are_added(st.session_state.get("output_edits", {}))
            create_clicked = st.button("Create PDF", use_container_width=True, disabled=not pictures_added)
            if not pictures_added:
                st.caption("Add pictures before creating the final PDF.")
            if create_clicked and not commit_ready:
                next_nonce = str(int(st.session_state.get("_visual_editor_commit_counter", 0)) + 1)
                st.session_state["_visual_editor_commit_counter"] = int(next_nonce)
                st.session_state["_visual_editor_commit_nonce"] = next_nonce
                st.session_state["_pdf_after_visual_edit_commit_nonce"] = next_nonce
                st.session_state["_visual_editor_export_commit_ready"] = False
                st.info("Applying pending preview edits before creating the PDF…")
                st.rerun()

            if commit_ready and pictures_added:
                validation_report = validate_for_generation(st.session_state.get("parsed_rows", []))
                if validation_report.is_blocked:
                    block_generation(validation_report)
                    render_blocking_issues(validation_report)
                    return
                try:
                    with st.spinner("Creating PDF..."):
                        # The visual editor has now committed browser-side edits.
                        # Rebuild only when the content signature changed, then
                        # reuse an up-to-date PDF instead of exporting again.
                        rebuild_current_preview(mark_pdf_dirty=False, save_html=True)
                        html_path = Path(st.session_state.html_path) if st.session_state.html_path else html_path

                        expected_day_count = len(group_rows_by_day(st.session_state.get("parsed_rows", []) or []))
                        contract_issues = validate_output_layout_contract(
                            st.session_state.get("itinerary_html", ""),
                            expected_day_count=expected_day_count,
                        )
                        blocking_contract_issues = [
                            issue for issue in contract_issues if issue.severity == "error"
                        ]
                        if blocking_contract_issues:
                            st.session_state.pdf_signature = None
                            st.session_state.pdf_status = "Needs review"
                            st.error("PDF export stopped because the preview structure needs review.")
                            with st.expander("Preview structure issues"):
                                for issue in blocking_contract_issues:
                                    st.write(f"- {issue.message}")
                            return

                        grouped_days = group_rows_by_day(st.session_state.get("parsed_rows", []) or [])
                        image_grouped_days = {
                            day: [row for row in rows if not is_optional_row(row)] or list(rows)
                            for day, rows in grouped_days.items()
                        }
                        current_image_bank_status = image_bank_status()
                        if image_grouped_days and current_image_bank_status.get("missing_full_bank"):
                            with st.spinner("Connecting the separate itinerary-image-bank repository from GitHub…"):
                                current_image_bank_status = connect_remote_image_bank_if_missing()

                        image_matches = select_day_images_with_overrides(
                            image_grouped_days,
                            st.session_state.get("output_edits", {}),
                        )
                        current_image_bank_status = image_bank_status()
                        image_issues = audit_day_image_matches(
                            image_grouped_days,
                            image_matches,
                            st.session_state.get("output_edits", {}),
                        )
                        blocking_image_issues = [
                            issue for issue in image_issues if issue.severity == "error"
                        ]
                        if blocking_image_issues:
                            st.session_state.pdf_signature = None
                            st.session_state.pdf_status = "Needs image review"
                            st.error("PDF export stopped because one or more pictures need review.")
                            with st.expander("Picture review issues"):
                                for issue in blocking_image_issues:
                                    st.write(f"- {issue.message}")
                            return
                        nonblocking_image_issues = [
                            issue for issue in image_issues if issue.severity != "error"
                        ]
                        if nonblocking_image_issues:
                            with st.expander("Picture review warnings"):
                                for issue in nonblocking_image_issues[:10]:
                                    st.write(f"- {issue.message}")

                        current_pdf_signature = st.session_state.get("preview_signature")

                        pdf_is_current = (
                            bool(st.session_state.get("pdf_bytes"))
                            and st.session_state.get("pdf_signature") == current_pdf_signature
                        )

                        if pdf_is_current:
                            st.session_state.pdf_status = "Ready"
                        else:
                            edited_rows_for_pdf = apply_output_edits(
                                st.session_state.get("parsed_rows", []) or [],
                                st.session_state.get("output_edits", {}) or {},
                            )
                            grouped_days_for_pdf = group_rows_by_day(edited_rows_for_pdf)
                            pdf_render_context = build_itinerary_render_context(
                                edited_rows_for_pdf,
                                grouped_days_for_pdf,
                                st.session_state.get("output_edits", {}) or {},
                            )
                            day_image_crop_focus = {
                                day: get_day_image_crop_focus(st.session_state.get("output_edits", {}) or {}, day)
                                for day in grouped_days_for_pdf
                            }
                            client_quality_report = evaluate_client_output_quality(
                                pdf_render_context.render_document,
                                day_images=image_matches,
                                image_bank_status=current_image_bank_status,
                            )
                            if client_quality_report.is_blocked:
                                st.session_state.pdf_status = "Blocked by output quality gate"
                                for issue in client_quality_report.blocking_issues:
                                    st.error(issue.message)
                                return
                            pdf_path = save_pdf_file(
                                html_path,
                                render_document=pdf_render_context.render_document,
                                color_data=pdf_render_context.colors,
                                day_images=image_matches,
                                day_image_crop_focus=day_image_crop_focus,
                                output_edits=st.session_state.get("output_edits", {}) or {},
                            )
                            if pdf_path is None:
                                st.session_state.pdf_bytes = None
                                st.session_state.pdf_signature = None
                                st.session_state.pdf_status = "PDF failed"
                            else:
                                st.session_state.pdf_bytes = Path(pdf_path).read_bytes()
                                st.session_state.pdf_signature = current_pdf_signature
                                st.session_state.pdf_status = "Ready"

                    st.session_state["_pdf_after_visual_edit_commit_nonce"] = None
                    st.session_state["_visual_editor_export_commit_ready"] = False
                    st.session_state["_visual_editor_commit_nonce"] = None

                    if st.session_state.pdf_bytes:
                        if pdf_is_current:
                            st.success("PDF already up to date. Use the download button.")
                        else:
                            st.success("PDF created with the latest preview edits. Use the download button.")

                except Exception as error:
                    st.session_state.pdf_signature = None
                    st.session_state.pdf_status = "PDF failed"
                    st.error(
                        "PDF export failed in this environment. The itinerary preview and HTML download still work."
                    )
                    with st.expander("PDF export error details"):
                        st.exception(error)
            elif st.session_state.get("_pdf_after_visual_edit_commit_nonce"):
                st.info("Applying pending preview edits before creating the PDF…")

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


