#!/usr/bin/env bash
# One-time bootstrap: create the PostgreSQL schema and import the CRM data.
#
# Run this from the backend directory. It is safe to re-run: tables use
# CREATE TABLE IF NOT EXISTS and documents are skipped when their _id is present.
#
#   ./bootstrap.sh                    # schema + import
#   ./bootstrap.sh --schema           # schema only
#   ./bootstrap.sh --verify           # row counts
#
# DATABASE_URL must be set (backend/.env is read automatically).
set -euo pipefail

cd "$(dirname "$0")"

echo "Checking requirements..."
python -c "import asyncpg" 2>/dev/null || {
  echo "Installing asyncpg..."
  python -m pip install --quiet asyncpg
}

echo "Checking the database..."
python -c "
import asyncio, asyncpg, pgbootstrap
url = pgbootstrap.database_url()
async def main():
    conn = await asyncpg.connect(pgbootstrap._normalize(url))
    print('  connected to', pgbootstrap._redact(url))
    await conn.close()
asyncio.run(main())
" || {
  echo
  echo "Could not reach PostgreSQL. Check that:"
  echo "  - DATABASE_URL is set in backend/.env"
  echo "  - the password's '@' is percent-encoded as %40"
  echo "  - the host resolves (Supabase Direct connection, session mode, port 5432)"
  exit 1
}

echo
echo "Applying schema and importing data..."
python -m pgbootstrap "$@"

echo
echo "Done. Start the API with:"
echo "  uvicorn server:app --host 0.0.0.0 --port 8000"