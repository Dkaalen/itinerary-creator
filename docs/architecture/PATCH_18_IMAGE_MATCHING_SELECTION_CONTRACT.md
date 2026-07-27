# Patch 18 — Image matching and selection contract

The supported image lifecycle is:

`candidate discovery → metadata normalization → scoring → automatic selection/fallback → user override → committed selection → preview/editor/PDF projection`

## Owners

- `images.scanner` discovers and indexes candidates.
- `images.metadata` normalizes candidate metadata.
- `images.matcher_context` and `images.matcher_scoring` calculate relevance.
- `images.matcher_selection` chooses automatic candidates deterministically.
- `images.day_image_selection` applies deliberate user choices and duplicate policy.
- `images.selection_contract` owns the versioned selected-image payload and internal provenance/debug fields.
- `images.selection_commit` owns deterministic reuse and invalidation of committed selections.
- Preview, editor, storage and PDF are passive projections of the committed path.

## Contracts

- Equal-scoring candidates are ordered by a stable full-path key.
- Automatic duplicate prevention remains deterministic.
- Reuse of a strong shared default is explicit as `safe_default_reuse`.
- Deliberate manual reuse is preserved as `intentional_manual_reuse`.
- Manual choices and explicit removals are authoritative.
- A commit is reused only when itinerary matching fields, overrides, fallback policy and image-bank content signature remain unchanged.
- Preview image bytes may enrich a committed selection only when the preview and committed paths match.
- Stale preview HTML cannot replace a newer selection.
- Selection provenance and scoring diagnostics remain internal metadata and do not enter customer copy.
