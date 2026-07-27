-- Additive Project Explorer organization and Trash foundation.
-- Apply this migration in Supabase before enabling the owner/folder/bulk UI.
-- These labels are organizational metadata only; they are not authentication.

alter table public.itineraries
    add column if not exists owner_slug text not null default 'unassigned',
    add column if not exists folder_name text not null default '',
    add column if not exists created_by text not null default 'unassigned',
    add column if not exists updated_by text not null default 'unassigned',
    add column if not exists revision bigint not null default 0,
    add column if not exists last_saved_at timestamptz,
    add column if not exists deleted_at timestamptz,
    add column if not exists deleted_by text;

update public.itineraries
set last_saved_at = coalesce(last_saved_at, updated_at, created_at, now())
where last_saved_at is null;

alter table public.itineraries
    alter column last_saved_at set default now(),
    alter column last_saved_at set not null;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'itineraries_owner_slug_allowed'
    ) then
        alter table public.itineraries
            add constraint itineraries_owner_slug_allowed
            check (owner_slug in ('unassigned', 'dennis', 'vipin', 'christer', 'shared'));
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'itineraries_created_by_allowed'
    ) then
        alter table public.itineraries
            add constraint itineraries_created_by_allowed
            check (created_by in ('unassigned', 'dennis', 'vipin', 'christer', 'shared'));
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'itineraries_updated_by_allowed'
    ) then
        alter table public.itineraries
            add constraint itineraries_updated_by_allowed
            check (updated_by in ('unassigned', 'dennis', 'vipin', 'christer', 'shared'));
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'itineraries_deleted_by_allowed'
    ) then
        alter table public.itineraries
            add constraint itineraries_deleted_by_allowed
            check (
                deleted_by is null
                or deleted_by in ('unassigned', 'dennis', 'vipin', 'christer', 'shared')
            );
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'itineraries_folder_name_length'
    ) then
        alter table public.itineraries
            add constraint itineraries_folder_name_length
            check (char_length(folder_name) <= 80);
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'itineraries_revision_nonnegative'
    ) then
        alter table public.itineraries
            add constraint itineraries_revision_nonnegative
            check (revision >= 0);
    end if;
end
$$;

create index if not exists itineraries_active_recent_idx
    on public.itineraries (last_saved_at desc, id)
    where deleted_at is null;

create index if not exists itineraries_active_owner_recent_idx
    on public.itineraries (owner_slug, last_saved_at desc, id)
    where deleted_at is null;

create index if not exists itineraries_active_folder_recent_idx
    on public.itineraries (folder_name, last_saved_at desc, id)
    where deleted_at is null;

create index if not exists itineraries_trash_recent_idx
    on public.itineraries (deleted_at desc, id)
    where deleted_at is not null;

comment on column public.itineraries.owner_slug is
    'Organizational owner label; not an authenticated user or authorization boundary.';
comment on column public.itineraries.folder_name is
    'Single logical Project Explorer folder/reference such as ITIN-2020.';
comment on column public.itineraries.revision is
    'Monotonic project revision reserved for compare-and-swap save protection.';
comment on column public.itineraries.deleted_at is
    'Soft-delete timestamp. Non-null rows belong to Project Explorer Trash.';

-- Keep the project-list save timestamp owned by immutable version writes.
-- This avoids requiring application clients to coordinate two timestamps and
-- prevents owner/folder/Trash edits from appearing as itinerary content saves.
create or replace function public.sync_itinerary_last_saved_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if tg_op = 'INSERT' then
        update public.itineraries
        set last_saved_at = coalesce(new.created_at, now())
        where id = new.itinerary_id;
        return new;
    end if;

    update public.itineraries as i
    set last_saved_at = coalesce(
        (
            select max(v.created_at)
            from public.itinerary_versions as v
            where v.itinerary_id = old.itinerary_id
        ),
        i.updated_at,
        i.created_at,
        now()
    )
    where i.id = old.itinerary_id;
    return old;
end;
$$;

drop trigger if exists itinerary_versions_sync_last_saved_at
    on public.itinerary_versions;
create trigger itinerary_versions_sync_last_saved_at
after insert or delete on public.itinerary_versions
for each row execute function public.sync_itinerary_last_saved_at();

create or replace function public.list_project_folders(
    p_owner_slug text default null,
    p_include_trashed boolean default false
)
returns table(folder_name text, project_count bigint)
language sql
stable
set search_path = public
as $$
    select
        i.folder_name,
        count(*)::bigint as project_count
    from public.itineraries as i
    where i.folder_name <> ''
      and (p_owner_slug is null or i.owner_slug = p_owner_slug)
      and (p_include_trashed or i.deleted_at is null)
    group by i.folder_name
    order by lower(i.folder_name), i.folder_name;
$$;

revoke all on function public.list_project_folders(text, boolean) from public;
grant execute on function public.list_project_folders(text, boolean) to service_role;
