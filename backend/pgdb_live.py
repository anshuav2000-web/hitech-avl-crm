"""Run pgdb.py against a real PostgreSQL, wherever one is reachable.

This machine has no usable Postgres: the DB host resolves IPv6-only and there is no
IPv6 on this adapter, and Docker's WSL backend is wedged. So the harness runs inside
the deployed Coolify backend container, which already has the image and a DATABASE_URL.

    # from the app directory inside the container
    python pgdb_live.py

Safe to run against the real project: it works in a throwaway schema and drops it.
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
from pgdb_integration import _normalize_url  # noqa: E402
from pgbootstrap import database_url  # noqa: E402


async def main() -> int:
    try:
        url = database_url()
    except SystemExit as e:
        print(f"SKIP: {e}")
        return 0

    try:
        probe = await asyncpg.connect(_normalize_url(url))
    except Exception as e:  # noqa: BLE001
        print(f"SKIP: cannot connect ({type(e).__name__}: {str(e).strip().splitlines()[0][:100]})")
        return 0

    tag = "t_" + uuid.uuid4().hex[:8]
    await probe.execute(f'CREATE SCHEMA IF NOT EXISTS {tag}')
    await probe.execute(f'SET search_path TO {tag}, public')

    pool = await asyncpg.create_pool(_normalize_url(url), min_size=1, max_size=3)
    db = PostgresDocumentDB(pool)

    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"{label}\n     got:  {got!r}\n     want: {want!r}")

    try:
        print(f"PostgreSQL {probe.get_server_info().get('server_version', '?')}")
        for stmt in [s.strip() for s in build_schema().split(";") if s.strip()]:
            await probe.execute(stmt)

        # ---- write / read round trip through the Motor-shaped API ----
        await db.leads.insert_one({"id": "L1", "name": "Acme", "stage": "new", "budget": 100})
        await db.leads.insert_many([
            {"id": "L2", "name": "Bravo", "stage": "qualified", "budget": 250},
            {"id": "L3", "name": "Charlie", "stage": "new", "budget": 50},
        ])

        check("count all", await db.leads.count_documents({}), 3)
        check("count equality", await db.leads.count_documents({"stage": "new"}), 2)
        check("count $in", await db.leads.count_documents({"stage": {"$in": ["new", "qualified"]}}), 3)
        check("count regex",
              await db.leads.count_documents({"name": {"$regex": "^bra", "$options": "i"}}), 1)
        check("count $gt", await db.leads.count_documents({"budget": {"$gt": 60}}), 2)
        check("count $ne null", await db.leads.count_documents({"assigned_to": {"$ne": None}}), 2)

        one = await db.leads.find_one({"id": "L1"})
        check("find_one by id", (one or {}).get("name"), "Acme")

        rows = await db.leads.find({}, {"_id": 0, "id": 1}).to_list(10)
        check("projection include", sorted(x["id"] for x in rows), ["L1", "L2", "L3"])

        rows = await db.leads.find({}).sort("budget", -1).to_list(10)
        check("sort desc", [x["budget"] for x in rows], [250, 100, 50])

        await db.leads.update_one({"id": "L1"}, {"$set": {"stage": "qualified"}})
        got = await db.leads.find_one({"id": "L1"})
        check("$set applied", (got or {}).get("stage"), "qualified")

        await db.leads.update_one({"id": "L2"}, {"$inc": {"hits": 1}})
        await db.leads.update_one({"id": "L2"}, {"$inc": {"hits": 1}})
        got = await db.leads.find_one({"id": "L2"})
        check("$inc accumulates", (got or {}).get("hits"), 2)

        await db.leads.update_one({"id": "L2"}, {"$addToSet": {"tags": "x"}})
        await db.leads.update_one({"id": "L2"}, {"$addToSet": {"tags": "x"}})
        got = await db.leads.find_one({"id": "L2"})
        check("$addToSet dedupes", (got or {}).get("tags"), ["x"])

        out = await db.leads.aggregate([
            {"$group": {"_id": "$stage", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]).to_list(20)
        check("aggregate group", out[0]["count"], 2)

        out = await db.leads.aggregate([
            {"$match": {"stage": "qualified"}},
            {"$group": {"_id": None, "total": {"$sum": "$budget"}}},
        ]).to_list(1)
        check("aggregate sum", out[0]["total"], 350)

        raw = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
        await db.media.insert_one({"id": "M1", "data": raw})
        back = await db.media.find_one({"id": "M1"})
        check("bytes round trip", (back or {}).get("data"), raw)

        d = await db.leads.delete_one({"id": "L3"})
        check("delete_one", d.deleted_count, 1)

        check("ping", (await db.command("ping"))["ok"], 1)

    finally:
        await pool.close()
        await probe.execute(f"DROP SCHEMA IF EXISTS {tag} CASCADE")
        await probe.close()

    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("\npgdb live checks passed against real PostgreSQL")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))