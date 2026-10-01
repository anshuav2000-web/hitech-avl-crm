# Deployment — Hitech AVL CRM

Full-stack CRM: React frontend, FastAPI backend, MongoDB database.

```
Internet → Coolify → nginx (frontend, :8080)
                    → FastAPI backend (:8000, internal)
                      → MongoDB (persistent volume)
```

## Deploy as a separate Coolify project

This stacks as its own project and shares no network, domain or database with any
existing application. In Coolify: **New Resource → Application → Docker Compose**,
point it at this repository, and set the variables from `.env.example`.

Or, as two applications plus a managed database:

| Coolify resource | Source | Domain | Notes |
|---|---|---|---|
| Frontend | `frontend/` (Nixpacks/Dockerfile) | `crm.example.com` | Build `npm run build`, serve `build/` |
| Backend | `backend/` (Dockerfile) | `api.crm.example.com` | Start `uvicorn server:app --host 0.0.0.0 --port 8000` |
| MongoDB | MongoDB resource | — | Attach a persistent volume; copy its URL into `DATABASE_URL` |

Attach the backend to the database resource so Coolify injects the connection
string automatically, then point the frontend at the backend's public URL.

## Health checks

The backend exposes `GET /health`:

```json
{ "status": "ok", "database": "connected" }
```

It requires no credentials (a platform health check has none) and returns 503 when
the database does not answer, so Coolify will restart a container that lost its
database. Both Dockerfiles also declare a `HEALTHCHECK`.

Set the Coolify health-check path to `/health`.

## Environment variables

Copy `.env.example` and fill in real values. Nothing secret belongs in the repo —
`.env` is git-ignored, only `.env.example` is tracked.

Required in production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` / `MONGO_URL` | Database connection string |
| `DB_NAME` | Database name (`hitech_crm`) |
| `JWT_SECRET` | Token signing key, ≥32 chars. **Startup fails without it.** |
| `CORS_ORIGINS` | Comma-separated frontend origins. Never `*` in production. |
| `GENERATED_EMAIL_DOMAIN` | Domain for email addresses derived from a contact's name |
| `FRONTEND_URL` / `PUBLIC_BASE_URL` | Public origin, used for share links |
| `REACT_APP_BACKEND_URL` | Public API URL, baked into the frontend bundle at build time |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Bootstrap admin, created on first start only |

## Production process

The backend runs `uvicorn` with `--workers 2`. The frontend is a static nginx
serving `build/`. Neither uses a dev server, and there is no `--reload` anywhere in
the deployment path.

## Database persistence

MongoDB runs with a named volume (`hitech-avl-crm-mongo-data`). Data survives
container restart, redeploy and server reboot. When using a Coolify-managed MongoDB
resource, attach a persistent volume there instead.

Schema changes are applied by migrations, not by hand:

```bash
cd backend && python -m migrations
```

The same runner executes at application startup, so a new deploy applies any
pending migration before serving traffic.

### Migration runner concurrency

`uvicorn` runs two workers, so startup triggers the migration runner twice
concurrently. `run_migrations()` takes a MongoDB lease before applying anything:

- the lease is a document in the `schema_migration_lock` collection, written with
  an upsert whose filter requires the existing lease to be expired, so the unique
  `_id` decides the winner;
- the losing worker waits (up to `LOCK_TTL_SECONDS`) until every migration is
  recorded before continuing, so a worker never builds indexes against a
  half-migrated database;
- the lease is released as soon as the runner finishes.

Keep the lease in its own collection. It lives beside the migration records only
by accident, and a lease document has no `id` field, so the reader that builds
the "already applied" set raises `KeyError` and silently skips the entire
migration chain.

Seed migrations must also be idempotent — use an upsert with `$setOnInsert`
rather than `insert_one`, or a re-run against a partially seeded database trips
the unique index.

## Database engine note

The application is MongoDB-native: every endpoint queries documents through Motor,
and the data model is document-oriented (quotation line items, stage history,
project integrations). PostgreSQL is not compatible with the current code without
rewriting every query, so MongoDB with a persistent volume is used. This is a
deliberate decision, not an oversight — if PostgreSQL is a hard requirement, that
is a separate porting project.

## Backups

`mongodump` against the volume before any migration that touches data:

```bash
docker compose exec -T mongo mongodump --archive --gzip > crm-backup-$(date +%F).archive
```

Restore:

```bash
docker compose exec -T mongo mongorestore --archive --gzip --drop < crm-backup-YYYY-MM-DD.archive
```