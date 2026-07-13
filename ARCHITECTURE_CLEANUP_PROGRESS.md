# Architecture Cleanup Progress

This file is kept as the current handoff/workflow contract expected by tests and older handover prompts.

Use **patch** for each implementation unit.

When returning changed files, use explicit Git staging. For normal patches use:

```powershell
git add -- $files
```

When files are deleted, use explicit deletion staging:

```powershell
git rm --ignore-unmatch path/to/deleted_file.py
```

Do not use broad accidental staging as the primary delivery mechanism unless the patch deliberately owns every changed file. `git add .` is mentioned here only as an anti-footgun check target for legacy handoff tests and should not replace explicit scoped staging.

## Architecture principle

One file should have one clear responsibility. Compatibility facades are allowed only to preserve stable import paths; they must not contain duplicate business logic.

Historical patch notes have been archived at `docs/archive/ARCHITECTURE_CLEANUP_PROGRESS.md`.
