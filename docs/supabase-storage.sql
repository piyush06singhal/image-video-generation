-- Run once in the Supabase SQL editor.
-- The application stores private project archives in Storage. This table keeps
-- an auditable index and can be used for retention/cleanup jobs later.
create table if not exists public.project_snapshots (
  project_id text primary key,
  archive_path text not null,
  archive_bytes bigint not null,
  updated_at timestamptz not null default now()
);

alter table public.project_snapshots enable row level security;

revoke all on table public.project_snapshots from anon, authenticated;
