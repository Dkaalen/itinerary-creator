from pathlib import Path
import json

import streamlit as st

from ui.export_files import save_pdf_file
from app_modules.project_io import rebuild_current_preview


def render_export_step(app_version):
    if st.session_state.itinerary_html:
        st.subheader("Step 4 — Export")
        st.markdown('<div class="workflow-note">Download your editable project, download the HTML preview, or create a PDF. Create PDF applies pending page edits first.</div>', unsafe_allow_html=True)

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

            create_clicked = st.button("Create PDF", use_container_width=True)
            if create_clicked and not commit_ready:
                next_nonce = str(int(st.session_state.get("_visual_editor_commit_counter", 0)) + 1)
                st.session_state["_visual_editor_commit_counter"] = int(next_nonce)
                st.session_state["_visual_editor_commit_nonce"] = next_nonce
                st.session_state["_pdf_after_visual_edit_commit_nonce"] = next_nonce
                st.session_state["_visual_editor_export_commit_ready"] = False
                st.info("Applying pending preview edits before creating the PDF…")
                st.rerun()

            if commit_ready:
                try:
                    with st.spinner("Creating PDF..."):
                        # The visual editor has now committed browser-side edits.
                        # Rebuild only when the content signature changed, then
                        # reuse an up-to-date PDF instead of exporting again.
                        rebuild_current_preview(mark_pdf_dirty=False, save_html=True)
                        html_path = Path(st.session_state.html_path) if st.session_state.html_path else html_path
                        current_pdf_signature = st.session_state.get("preview_signature")

                        pdf_is_current = (
                            bool(st.session_state.get("pdf_bytes"))
                            and st.session_state.get("pdf_signature") == current_pdf_signature
                        )

                        if pdf_is_current:
                            st.session_state.pdf_status = "Ready"
                        else:
                            pdf_path = save_pdf_file(html_path)
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


