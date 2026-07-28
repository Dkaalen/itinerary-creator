# Browser recovery storage

Calculator and Visual Editor recovery drafts use the bounded app-owned IndexedDB database `itineraryCreatorRecovery`. Large recovery payloads are not written to `localStorage`; `localStorage` is read only during one-time migration of recognized legacy keys.

## Existing browsers already over quota

Streamlit can attempt to write its own theme metadata before application Python or the cleanup component runs. A browser that is already over the origin quota may therefore show the framework storage error once before the application can migrate old data.

The practical one-time recovery is:

1. Close every open Itinerary Creator tab.
2. Clear site data for `itinerary-creator.streamlit.app` in the browser's site settings.
3. Reopen the application and sign in again if required.

This removes browser-local recovery copies only. It does not delete Supabase projects or the production Local Library workbook. After reopening, new Calculator and Visual Editor recovery data is written to bounded IndexedDB records, preventing the previous `localStorage` quota pattern from recurring.

## Ownership and limits

`app_modules/browser_storage_contract.py` is the sole authority for database identity, recognized legacy prefixes, retention age, namespace count, and byte limits. The startup guard and both frontend components receive that same contract. Unrelated browser keys are never cleared by the application.

If IndexedDB is unavailable or rejects a write, editing remains active, recovery writes pause, and the interface shows a quiet recovery status. Explicit Save and Supabase project persistence remain separate.
