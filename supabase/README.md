# Supabase project-storage migrations

The files in `supabase/migrations/` are additive database migrations for the
saved-project subsystem. They are not Local Library sources and must never
replace `data/Calculation-template-Inputs-fixed-outline-restored.xlsx`.

## Applying a migration

Apply pending SQL files in filename order through the Supabase SQL Editor for
the production project. Do not execute schema-changing SQL automatically from
Streamlit startup code.

Before deploying UI code that depends on a migration:

1. Take a database backup or confirm point-in-time recovery.
2. Review the SQL in the pending migration.
3. Apply it in Supabase.
4. Confirm the new columns, indexes and functions exist.
5. Run the storage test group locally.
6. Deploy the matching application code.

`20260727190000_project_organization_and_trash.sql` adds the Project Explorer
organization schema and legacy soft-delete compatibility fields:

- owner labels for Dennis, Vipin, Christer, Shared and Unassigned;
- one logical folder/reference field;
- created-by and updated-by audit labels;
- a reserved monotonic revision field;
- last-saved timestamps plus legacy soft-delete compatibility columns;
- active-project indexes and a legacy soft-delete index;
- a bounded folder-option RPC for server-side filters.

Owner and actor labels are organizational metadata only. They do not authenticate
users, enforce permissions or replace Supabase row-level security. The current
app uses a server-side Supabase secret and must not expose that secret to browser
components or commit it to the repository.

The current application does not expose a Trash workflow. Project Explorer lists
active rows only and deletion is direct, explicit and permanent after confirmation.
The legacy soft-delete columns remain in the deployed additive migration so older
records can be excluded safely; application code does not create, restore or purge
a separate Trash lifecycle.

## Runtime capability and deletion behavior

Streamlit never applies migrations automatically. The repository probes the optional
organization columns once per repository session and checks the folder RPC only when
the columns exist. Missing schema features select the legacy list path and hide
unsupported owner/folder controls; transient network failures are surfaced rather
than cached as a missing migration.

Project pages, exact counts and folder options use a short bounded in-process cache.
Successful local mutations invalidate it immediately, while the short expiry allows
changes made by another organizational user to appear without keeping stale
session-long folder data.

Permanent deletion is idempotent and batched: one bounded file-record query group,
Storage deletion batches, then database deletion batches for projects whose files
were cleaned successfully. A failed Storage batch retains its affected database
records; a failed database batch remains retryable after file cleanup. No migration
or live data change is performed by this application code.
