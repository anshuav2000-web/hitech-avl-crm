"""End-to-end check of pgdb.py against a real Postgres, when one is reachable.

Skips cleanly when DATABASE_URL is unset or unreachable, so it can live in the repo
without breaking CI. Run with a URL that points at a throwaway database::

    DATABASE_URL=postgresql://... python pgdb_integration.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncpg  # noqa: E402

from pgdb import PostgresDocumentDB  # noqa: E402
from pgschema import build_schema  # noqa: E402


def _normalize_url(url: str) -> str:
    if "@" in url.split("://", 1)[-1]:
        from urllib.parse import quote

        head, _, tail = url.partition("://")
        creds, _, host = tail.rpartition("@")
        if ":" in creds:
            u, _, p = creds.partition(":")
            creds = f"{quote(u, safe='')}:{quote(p, safe='')}"
            url = f"{head}://{creds}@{host}"
    return url


async def main() -> int:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("SKIP: DATABASE_URL is not set")
        return 0

    try:
        conn = await asyncpg.connect(_normalize_url(url))
    except Exception as e:  # noqa: BLE001
        print(f"SKIP: cannot connect ({type(e).__name__}: {str(e).strip().splitlines()[0][:90]})")
        return 0

    pool = await asyncpg.create_pool(_normalize_url(url), min_size=1, max_size=3)
    db = PostgresDocumentDB(pool)

    # A scratch schema keeps the test from touching anything real.
    tag = "t_" + uuid.uuid4().hex[:8]
    await conn.execute(f'CREATE SCHEMA IF NOT EXISTS {tag}')
    await conn.execute(f'SET search_path TO {tag}, public')

    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"{label}\n     got:  {got!r}\n     want: {want!r}")

    try:
        for stmt in [s.strip() for s in build_schema().split(";") if s.strip()]:
            await conn.execute(stmt)

        # ---------------------------------------------------------- insert
        r = await db.leads.insert_one({
            "id": "L1", "name": "Acme", "stage": "new",
            "budget": 100, "assigned_to": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "stage_history": [{"to_stage": "new"}],
        })
        check("insert_one returns an id", bool(r.inserted_id), True)

        await db.leads.insert_many([
            {"id": "L2", "name": "Bravo", "stage": "qualified", "budget": 250},
            {"id": "L3", "name": "Charlie", "stage": "new", "budget": 50},
        ])

        # ---------------------------------------------------------- read
        n = await db.leads.count_documents({})
        check("count all", n, 3)

        one = await db.leads.find_one({"name": "Acme"})
        check("find_one by field", (one or {}).get("id"), "L1")

        one_id = await db.leads.find_one({"id": "L2"})
        check("find_one by id", (one_id or {}).get("name"), "Bravo")

        n = await db.leads.count_documents({"stage": "new"})
        check("count by equality", n, 2)

        n = await db.leads.count_documents({"stage": {"$in": ["new", "qualified"]}})
        check("count by $in", n, 3)

        n = await db.leads.count_documents({"stage": {"$nin": ["new"]}})
        check("count by $nin", n, 1)

        n = await db.leads.count_documents({"name": {"$regex": "^bra", "$options": "i"}})
        check("count by regex", n, 1)

        n = await db.leads.count_documents({"assigned_to": None})
        check("count explicit null", n, 1)

        n = await db.leads.count_documents({"assigned_to": {"$ne": None}})
        check("$ne excludes null", n, 2)

        n = await db.leads.count_documents({"budget": {"$gt": 60}})
        check("numeric $gt", n, 2)

        n = await db.leads.count_documents({"$or": [{"name": "Acme"}, {"stage": "qualified"}]})
        check("$or", n, 2)

        n = await db.leads.count_documents({"stage_history.0.to_stage": "new"})
        check("dotted path into an array", n, 1)

        rows = await db.leads.find({}, {"_id": 0, "id": 1}).to_list(10)
        check("projection include", sorted(x["id"] for x in rows), ["L1", "L2", "L3"])
        check("projection drops _id", any("_id" in x for x in rows), False)

        rows = await db.leads.find({}, {"_id": 0, "name": 0}).to_list(10)
        check("projection exclude", any("name" in x for x in rows), False)

        rows = await db.leads.find({}).sort("budget", -1).to_list(10)
        check("sort desc numeric", [x["budget"] for x in rows], [250, 100, 50])

        rows = await db.leads.find({}).sort("budget", 1).limit(2).to_list(10)
        check("sort + limit", [x["budget"] for x in rows], [50, 100])

        rows = await db.leads.find({}).sort("budget", 1).skip(1).limit(1).to_list(10)
        check("skip + limit", [x["budget"] for x in rows], [100])

        # ---------------------------------------------------------- update
        u = await db.leads.update_one({"id": "L1"}, {"$set": {"stage": "qualified"}})
        check("update matched", u.matched_count, 1)
        check("update modified", u.modified_count, 1)
        got = await db.leads.find_one({"id": "L1"})
        check("update applied", (got or {}).get("stage"), "qualified")

        await db.leads.update_one({"id": "L2"}, {"$push": {"tags": "hot"}})
        await db.leads.update_one({"id": "L2"}, {"$push": {"tags": "hot"}})
        got = await db.leads.find_one({"id": "L2"})
        check("$push twice appends twice", (got or {}).get("tags"), ["hot", "hot"])

        await db.leads.update_one({"id": "L2"}, {"$addToSet": {"tags": "hot"}})
        got = await db.leads.find_one({"id": "L2"})
        check("$addToSet dedupes", (got or {}).get("tags"), ["hot", "hot"])

        await db.leads.update_one({"id": "L2"}, {"$inc": {"hits": 1}})
        await db.leads.update_one({"id": "L2"}, {"$inc": {"hits": 1}})
        got = await db.leads.find_one({"id": "L2"})
        check("$inc accumulates", (got or {}).get("hits"), 2)

        await db.leads.update_one({"id": "L2"}, {"$unset": {"tags": ""}})
        got = await db.leads.find_one({"id": "L2"})
        check("$unset removes", "tags" in (got or {}), False)

        u = await db.leads.update_one({"id": "nope"}, {"$set": {"stage": "new"}}, upsert=True)
        check("upsert reports an id", bool(u.upserted_id), True)
        check("upsert created a row", await db.leads.count_documents({"id": "nope"}), 1)

        await db.leads.update_many({"stage": "new"}, {"$set": {"bulk": True}})
        got = await db.leads.find_one({"id": "L3"})
        check("update_many applied", (got or {}).get("bulk"), True)

        # ----------------------------------------------------- aggregation
        out = await db.leads.aggregate([
            {"$group": {"_id": "$stage", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]).to_list(20)
        check("group by stage, top first", out[0]["count"], 2)

        out = await db.leads.aggregate([
            {"$match": {"stage": "qualified"}},
            {"$group": {"_id": None, "total": {"$sum": "$budget"}}},
        ]).to_list(1)
        check("sum with _id null", out[0]["total"], 350)

        # ------------------------------------------------------- deletion
        d = await db.leads.delete_one({"id": "L3"})
        check("delete_one count", d.deleted_count, 1)
        check("delete_one removed", await db.leads.count_documents({"id": "L3"}), 0)

        d = await db.leads.delete_many({"stage": "qualified"})
        check("delete_many count", d.deleted_count >= 2, True)

        # ------------------------------------------------- binary round trip
        raw = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
        await db.media.insert_one({"id": "M1", "data": raw})
        back = await db.media.find_one({"id": "M1"})
        check("bytes survive the round trip", (back or {}).get("data"), raw)

        # ------------------------------------------------------- ping/health
        check("command ping", (await db.command("ping"))["ok"], 1)
        check("list_collection_names sees the tables", "leads" in await db.list_collection_names(), True)

    finally:
        await pool.close()
        await conn.execute(f"DROP SCHEMA IF EXISTS {tag} CASCADE")
        await conn.close()

    if failures:
        print(f"FAILED ({len(failures)}):\n")
        for f in failures:
            print("  -", f)
        return 1
    print("pgdb integration checks passed against a live PostgreSQL")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))