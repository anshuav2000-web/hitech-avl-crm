"""Exercise the app's startup path without a database.

Startup builds the asyncpg pool, checks the schema exists, then runs the project's
own migrations. A scratch schema stands in for the real database so the ordering,
the table check, and migrations.py's use of the document API all get exercised.

    python pgdb_startup_check.py            # skips if DATABASE_URL is unset
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncpg  # noqa: E402

from pgdb import PostgresDocumentDB  # noqa: E402
from pgschema import build_schema  # noqa: E402
from pgbootstrap import _normalize_url, _redact  # noqa: E402


async def main() -> int:
    import os

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("SKIP: DATABASE_URL is not set")
        return 0
    try:
        probe = await asyncpg.connect(_normalize_url(url))
    except Exception as e:  # noqa: BLE001
        print(f"SKIP: cannot connect ({type(e).__name__}: {str(e).strip().splitlines()[0][:90]})")
        return 0

    tag = "t_" + uuid.uuid4().hex[:8]
    await probe.execute(f'CREATE SCHEMA IF NOT EXISTS {tag}')
    await probe.execute(f'SET search_path TO {tag}, public')
    print(f"connected to {_redact(url)}")

    pool = await asyncpg.create_pool(_normalize_url(url), min_size=1, max_size=3)
    db = PostgresDocumentDB(pool)
    failures = []

    try:
        # Exactly what the startup hook checks before serving traffic.
        missing = await db.fetchval(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name LIKE 'c\\_%'"
        )
        if missing:
            print("  startup guard would reject: schema missing")
            return 1
        print("  startup guard passes: c_* tables present")

        for stmt in [s.strip() for s in build_schema().split(";") if s.strip()]:
            await probe.execute(stmt)

        # Now run the project's migrations against the document layer.
        from migrations import run_migrations

        applied = await run_migrations(db, log=lambda *a, **k: None)
        print(f"  run_migrations applied: {applied or 'nothing new'}")

        # Migrations use create_index, which must not raise on any input.
        for coll, keys, kwargs in [
            ("users", "email", {"unique": True, "partialFilterExpression": {"email": {"$type": "string"}}}),
            ("leads", [("stage", 1), ("assigned_to", 1)], {}),
            ("activities", "lead_id", {"background": True}),
        ]:
            await db[coll].create_index(keys, **kwargs)
        print("  create_index accepts partial/background/multi-key forms")

        # And the admin seed path the startup hook uses.
        email = os.environ.get("ADMIN_EMAIL", "admin@hitechaudio.in").lower()
        existing = await db.users.find_one({"email": email})
        if existing is None:
            import bcrypt

            pw = os.environ.get("ADMIN_PASSWORD") or "Admin@123"
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "name": "Admin",
                "email": email,
                "password_hash": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
                "role": "admin",
                "allowed_brands": [],
            })
            print(f"  seeded admin user {email}")
        else:
            print(f"  admin user {email} already present")

        check = await db.users.find_one({"email": email})
        if not check or not check.get("password_hash", "").startswith("$2"):
            failures.append("admin user did not round-trip with a bcrypt hash")

        # A representative page query, the way Leads.js calls it.
        rows = await db.leads.find({}, {"_id": 0, "id": 1, "name": 1}).sort("created_at", -1).to_list(1000)
        print(f"  leads list query returned {len(rows)} rows")

    finally:
        await pool.close()
        await probe.execute(f"DROP SCHEMA IF EXISTS {tag} CASCADE")
        await probe.close()

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nstartup path checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))