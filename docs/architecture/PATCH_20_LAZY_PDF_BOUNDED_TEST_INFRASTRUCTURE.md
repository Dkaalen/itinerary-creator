# Patch 20 — Lazy PDF and bounded test-infrastructure contract

## Status

Patch 20 establishes two independent architecture boundaries:

1. Heavy PDF dependencies remain dormant until an explicit PDF creation call.
2. The repository's explicit test catalogue is complete, bounded, resumable, and honest about incomplete execution.

Neither boundary changes itinerary facts, prepared content, editor state, image selections, workbook provenance, financial calculations, or export layout decisions.

## 20A — Supported lazy PDF API

### Supported application boundary

Application code imports PDF behavior only from:

```python
from pdf_exporter import create_pdf
```

The supported `pdf_exporter.__all__` surface is deliberately narrow:

- `PdfExportProfile`
- `PdfExportResult`
- `create_pdf`
- `pdf_export_profile_options`
- `pdf_filename`
- `resolve_pdf_export_profile`

`pdf_exporter_modules` is a private implementation package. Its initializer is side-effect free and exports nothing. The retired `pdf_exporter_modules/public_api.py` facade must remain absent.

### Import boundary

The following operations must not import ReportLab or renderer implementation modules:

- Importing the application entry package
- Importing the declarative route registry
- Opening Calculator
- Parsing source input
- Normalizing rows
- Generating itinerary content
- Building preview
- Opening the visual editor
- Entering picture selection
- Opening the export page
- Importing export actions

Only calling `create_pdf` may import the HTML or typed PDF renderer and its heavy dependencies. Request validation happens before those imports, so invalid requests remain lightweight.

### Result contract

`create_pdf` returns an immutable `PdfExportResult` rather than leaking implementation exceptions into UI code. Supported outcomes include:

- `created`
- `invalid_request`
- `dependency_unavailable`
- `failed`

Missing ReportLab, Pillow, or BeautifulSoup dependencies produce a stable `pdf_dependency_unavailable` result. The existing preview and editor state remain unchanged.

### Rendering and cache parity

`create_pdf` preserves the established renderer decision:

- A prepared `RenderDocument` uses typed PDF rendering when supported.
- Unsupported manual HTML uses the established HTML fallback.
- The export coordinator continues to pass the committed editor document, committed image selections, crop focus, output profile, output brand, and prepared colors.
- Existing PDF artifact identity, render-context reuse, image prewarming, and persistent image crop caches remain owned by their existing modules.

Legacy call-level helpers remain lazily accessible from `pdf_exporter` for repository tests and migration safety, but they are outside the supported `__all__` boundary. Production modules must not import `pdf_exporter_modules` directly.

## 20B — Explicit bounded test catalogue

### Catalogue authority

`scripts/test_group_catalog` owns the registered target data. `scripts/test_catalogue.py` owns static validation and listing.

The validator must:

- Verify every registered module exists.
- Reject duplicate targets inside a lane.
- Report active test modules absent from every lane.
- Verify catalogue order and mapping order agree.
- List any lane without importing or running pytest.

Cross-domain registration is allowed because focused lanes intentionally overlap. An executable plan must deduplicate overlapping lanes and reject any exact target that would run twice in that plan.

### Independently runnable domains

The supported catalogue includes dedicated lanes for:

- Architecture
- Calculator
- Generator
- Routes
- Inclusions
- Quality
- Export
- Editor
- Storage
- Images
- Failure modes

Full automatic discovery remains separately available through normal pytest collection and the full plan.

### Stage boundary

`TEST_STAGE_BOUNDARY_SECONDS` is 45 seconds. Every generated executable stage has a timeout between one and 45 seconds. Environment overrides may reduce a timeout but cannot raise it above the boundary.

When a stage is too large, its catalogue definition must be split. Runners must not recommend increasing the timeout.

The release command invokes the resumable stage orchestrator in-process. It does not wrap the entire multi-stage release plan in one long subprocess timeout.

### Honest interruption semantics

A checkpoint is written atomically when a stage starts and after it finishes. A stage left as `RUNNING`, returning timeout code 124, or otherwise interrupted is not counted as passed.

Stage records include:

- Owning group
- Timeout
- Status
- Elapsed time
- Completion state
- Whether the result was counted
- Log path

Summaries aggregate elapsed time and status by group and flag any recorded stage duration above the 45-second boundary. One subgroup failure does not erase completed subgroup evidence.

### Deterministic evidence

Runtime checkpoints, logs, duration history, and generated audit reports live under `.test-runs/`, which is ignored by Git. Catalogue listing never writes reports. Generated report noise must not enter a patch manifest unless explicitly intended.

## Architecture guards

Patch 20 tests fail if:

- Application workflow imports initialize ReportLab before PDF creation.
- Production code imports private `pdf_exporter_modules` implementations.
- The PDF implementation package regains a broad package initializer or wildcard export.
- The retired `pdf_exporter_modules/public_api.py` facade returns.
- Missing dependencies escape without a supported result.
- A registered test module is missing, duplicated within its lane, or uncatalogued.
- An executable plan contains the same exact target twice.
- A generated stage exceeds 45 seconds.
- Required major domains are not independently runnable.
- Summaries omit group elapsed time or boundary reporting.
- Catalogue listing runs tests or writes tracked reports.
