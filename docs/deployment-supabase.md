# Durable storage on Render Free

Render's free filesystem is ephemeral, so the backend uses Supabase Storage as
the durable source of truth while keeping a local working copy for FFmpeg.

## Supabase setup

1. Create a free Supabase project.
2. Create a **private** Storage bucket named `walkthrough-assets`.
3. Run [`supabase-storage.sql`](./supabase-storage.sql) in the SQL editor.
4. Copy the project URL and the **service-role** key. The service-role key is
   backend-only and must never be added to Vercel.

## Render variables

Set these on the Render service and redeploy:

```text
REMOTE_STORAGE_ENABLED=true
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-service-role-key>
SUPABASE_STORAGE_BUCKET=walkthrough-assets
ASSEMBLY_MAX_RESOLUTION=720p
```

The application uploads one private ZIP snapshot per project after each
mutation. Archives are written to temporary disk storage and uploaded as a
stream, so the full project is not duplicated in RAM. Temporary assembly
directories are excluded. On a restart, a project is restored lazily when its
first request loads the missing local `project.json`. Assembly continues to use
local files, then the completed MP4 and metadata are uploaded in the final
snapshot.

`ASSEMBLY_MAX_RESOLUTION=720p` is intentional for Render Free's 512 MB memory
limit. The UI may retain a higher selected quality, but the backend caps the
actual FFmpeg output safely on this plan. Remove or increase the variable only
on a service with enough memory.

## Operational notes

- Existing projects created before Supabase was enabled cannot be recovered
  unless their local Render files still exist.
- Do not put `SUPABASE_SERVICE_ROLE_KEY` in the frontend or commit it.
- A large project archive can take time to upload; this is intentional because
  the API reports persistence failures instead of silently losing data.
- Local development remains filesystem-only unless the four variables above are
  enabled.
