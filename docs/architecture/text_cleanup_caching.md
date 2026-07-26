# Text cleanup caching

## Scope

The text cleanup hot path precompiles static replacement expressions and caches
only deterministic string-to-string functions:

- `text_polish_modules.text_cleanup._polish_text_fragment`
- `shared.source_text_cleanup._fix_common_text_cached`
- `place_alias_queries._normalize_place_text_cached`

Public wrappers remain permissive for non-string legacy inputs. Diagnostic
functions, including `check_for_unknown_typos`, are not cached.

## Cache contract

| Cache | Key | Stored value | Max entries | Invalidation |
|---|---|---|---:|---|
| Polished fragment | Canonical input string | Polished string | 8192 | Process restart or explicit clear |
| Common parser cleanup | Canonical input string | Cleaned string | 8192 | Process restart or explicit clear |
| Place-text normalization | Canonical input string | Normalized string | 8192 | Process restart or explicit clear |

The replacement tables are module-level static data. Runtime rule mutation is
not supported, so automatic invalidation is unnecessary. Tests and benchmarks
use `shared.text_cleanup_cache.clear_text_cleanup_caches()`.

## Tuning decision

An additional cache around `polish_client_text` was measured but not retained.
The expensive single-line work is already owned by `_polish_text_fragment`.
Adding the outer cache duplicated roughly the same key set, while warm workflow
timings were effectively unchanged.

The 8192-entry bounds were retained. Across all 15 real-input fixtures, the
full parse, preview, editor, and render-context workflow populated approximately:

- 3106 polished fragments
- 1339 common-cleanup strings
- 1311 place-normalization strings

A synthetic 9000-item probe confirmed that all caches remained bounded. The
complete nested cleanup pipeline retained about 6 MB for 8192 representative
120-character entries in the measurement environment.

## Benchmark

Run:

```powershell
python .\scripts\benchmark_text_cleanup.py --repeats 3
python .\scripts\benchmark_text_cleanup.py --all-fixtures --include-pdf
```

The report separates cold and warm timings for parse/normalize, generated edit
state, preview HTML, editor payload, shared render context, and typed PDF export.
It also records output identity and cache hit/miss statistics.
