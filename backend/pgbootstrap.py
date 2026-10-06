"""Create the CRM schema in Postgres and import the 2026-10-01 backup.

Run it anywhere that can reach the database -- the Coolify host, or a laptop with
IPv6/port-5432 access::

    python -m backend.pgbootstrap            # apply schema, then import
    python -m backend.pgbootstrap --schema   # schema only
    python -m backend.pgbootstrap --import   # import only
    python -m backend.pgbootstrap --verify   # row counts per collection

The backup is the only readable copy of the CRM data: the original MongoDB data
directory cannot be opened because the mongod binary was removed from the machine.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DEFAULT_BACKUP = BACKEND_DIR / "backups" / "pre_brand_cleanup_20261001_155606"

sys.path.insert(0, str(BACKEND_DIR))

from pgschema import COLLECTIONS, build_schema, _table  # noqa: E402


def _load_dotenv() -> None:
    env = BACKEND_DIR / ".env"
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def database_url() -> str:
    _load_dotenv()
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(
            "DATABASE_URL is not set.\n"
            "  Supabase dashboard -> Project Settings -> Database -> Connection string\n"
            "  Choose the 'Direct connection' (session) string, URI mode, and put it in\n"
            "  backend/.env as DATABASE_URL=postgresql://..."
        )
    return _normalize_url(url)


def _normalize_url(url: str) -> str:
    """Percent-encode reserved characters (notably '@') in the password."""
    from urllib.parse import quote

    if "@" in url.split("://", 1)[-1]:
        head, _, tail = url.partition("://")
        creds, _, hostpart = tail.rpartition("@")
        if ":" in creds:
            user, _, pw = creds.partition(":")
            creds = f"{quote(user, safe='')}:{quote(pw, safe='')}"
            url = f"{head}://{creds}@{hostpart}"
    return url


def _redact(url: str) -> str:
    if "@" not in url:
        return url
    head, _, tail = url.partition("://")
    _, _, hostpart = tail.rpartition("@")
    return f"{head}://***:***@{hostpart}"


def _normalize(url: str) -> str:
    """Percent-encode reserved characters in the password."""
    return _normalize_url(url)


async def _connect():
    try:
        import asyncpg
    except ImportError:
        raise SystemExit("asyncpg is required: pip install asyncpg")
    return await asyncpg.connect(_normalize(database_url()))


def _norm(doc: Any) -> Dict[str, Any]:
    """Ensure the document has an _id and an id, exactly as the importer needs."""
    if not isinstance(doc, dict):
        return {}
    d = dict(doc)
    if "_id" not in d or d["_id"] in (None, ""):
        import uuid

        d["_id"] = uuid.uuid4().hex[:24]
    d["_id"] = str(d["_id"])
    if "id" in d and d["id"] is not None:
        d["id"] = str(d["id"])
    return d


async def apply_schema(conn) -> None:
    sql = build_schema()
    print(f"Applying schema for {len(COLLECTIONS)} collections ...")
    # asyncpg cannot run several statements in one execute(), so split on the
    # statement terminator at top level (no PL/pgSQL bodies are emitted).
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        await conn.execute(stmt)
    print("Schema applied.")


async def import_backup(conn, backup_dir: Path) -> Dict[str, int]:
    files = sorted(backup_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no .json files in {backup_dir}")

    counts: Dict[str, int] = {}
    for path in files:
        name = path.stem
        if name not in COLLECTIONS:
            # Keep the document anyway: the table list is a superset today, and a
            # stray collection must not silently lose data.
            print(f"  ! {name} is not in COLLECTIONS; adding the table")
            await conn.execute(
                f"CREATE TABLE IF NOT EXISTS {_table(name)} ("
                " doc_id text PRIMARY KEY, body jsonb NOT NULL,"
                " pub_id text, updated_at timestamptz NOT NULL DEFAULT now())"
            )
        table = _table(name)

        raw = json.loads(path.read_text(encoding="utf-8"))
        docs = raw if isinstance(raw, list) else [raw]
        docs = [d for d in (_norm(d) for d in docs) if d]

        if not docs:
            counts[name] = 0
            continue

        # Skip what is already there so the script can be re-run safely.
        existing = set()
        try:
            rows = await conn.fetch(f"SELECT doc_id FROM {table}")
            existing = {r["doc_id"] for r in rows}
        except Exception:
            pass

        todo = [d for d in docs if d["_id"] not in existing]
        if not todo:
            counts[name] = len(docs)
            print(f"  = {name:26s} {len(docs):5d} (already present)")
            continue

        # Deduplicate inside the batch, then upsert.
        seen = set()
        args = []
        for d in todo:
            if d["_id"] in seen:
                continue
            seen.add(d["_id"])
            args.append((d["_id"], json.dumps(d, default=str), d.get("id")))

        await conn.executemany(
            f"INSERT INTO {table} (doc_id, body, pub_id) VALUES ($1, $2::jsonb, $3) "
            "ON CONFLICT (doc_id) DO UPDATE SET body = EXCLUDED.body, pub_id = EXCLUDED.pub_id",
            args,
        )
        counts[name] = len(docs)
        print(f"  + {name:26s} {len(docs):5d} ({len(args)} written)")

    return counts


async def verify(conn) -> int:
    print("\nRow counts:")
    total = 0
    for name in COLLECTIONS:
        table = _table(name)
        try:
            n = await conn.fetchval(f"SELECT count(*) FROM {table}")
        except Exception:
            continue
        total += int(n or 0)
        if n:
            print(f"  {name:26s} {int(n):5d}")
    print(f"\n  TOTAL {total} documents")
    return total


async def main() -> int:
    ap = argparse.ArgumentParser(description="Create the CRM schema in Postgres and import the backup")
    ap.add_argument("--schema", action="store_true", help="apply schema only")
    ap.add_argument("--import", dest="do_import", action="store_true", help="import only")
    ap.add_argument("--verify", action="store_true", help="print row counts and exit")
    ap.add_argument("--backup-dir", default=str(DEFAULT_BACKUP))
    args = ap.parse_args()

    if not (args.schema or args.do_import or args.verify):
        args.schema = args.do_import = True

    conn = await _connect()
    try:
        print(f"Connected to {_redact(database_url())}\n")
        if args.verify:
            await verify(conn)
            return 0
        if args.schema:
            await apply_schema(conn)
        if args.do_import:
            print("\nImporting backup documents ...")
            counts = await import_backup(conn, Path(args.backup_dir))
            print(f"\nImported {sum(counts.values())} documents across {len(counts)} collections.")
        if args.schema or args.do_import:
            await verify(conn)
        return 0
    finally:
        await conn.close()


def _redact(url: str) -> str:
    if "@" not in url:
        return url
    head, _, tail = url.partition("://")
    _, _, hostpart = tail.rpartition("@")
    return f"{head}://***:***@{hostpart}"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))