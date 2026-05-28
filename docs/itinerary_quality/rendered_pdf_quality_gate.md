# Rendered PDF Quality Gate

The itinerary app must be tested against the final PDF text, not only parser or generator objects.

Run:

```powershell
python .\tests\test_rendered_pdf_quality.py
```

What this catches:

- transport rows rendered in the wrong category
- self transfers leaking into inclusions
- optional add-ons shown as included
- cruise leisure days listed as commercial inclusions
- outdated/raw supplier wording in the exported PDF
- inclusion/exclusion wording that only fails after the final HTML → PDF path

The helper strips large images during test rendering to keep the test fast. It keeps the real itinerary text, page structure, final-page sections and ReportLab PDF conversion path.

To review extracted fixture text manually:

```powershell
python .\tests\tools\generate_fixture_pdf_texts.py
```

Outputs are written to:

```text
outputs/fixture_pdf_text/
```
