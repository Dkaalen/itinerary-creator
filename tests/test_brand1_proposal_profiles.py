from pdf_exporter_modules.export_profiles import pdf_export_profile_options, pdf_filename, resolve_pdf_export_profile


def test_brand1_profiles_are_named_as_proposal_outputs():
    labels = {profile["id"]: profile["label"] for profile in pdf_export_profile_options()}

    assert labels["client_premium"] == "Luxury Proposal"
    assert labels["client_compact"] == "Compact Itinerary"
    assert labels["client_detailed"] == "Detailed Travel Plan"
    assert labels["internal_review"] == "Internal Ops Version"


def test_brand1_profile_metadata_controls_pdf_title_and_client_readiness():
    premium = resolve_pdf_export_profile(None)
    detailed = resolve_pdf_export_profile("client_detailed")
    internal = resolve_pdf_export_profile("internal_review")

    assert premium.document_label == "LUXURY PROPOSAL"
    assert detailed.document_label == "DETAILED TRAVEL PLAN"
    assert internal.client_ready is False
    assert internal.include_internal_notes is True
    assert pdf_filename(profile={"id": "client_detailed"}) == "itinerary_preview_detailed.pdf"
