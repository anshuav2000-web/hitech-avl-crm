"""Re-run the brand migrations after the accidental brand/product deletion.

restore_from_backup.py removed 17 brand rows and 2,510 product rows because it
compared against a backup taken after earlier test runs. The migrations are
idempotent, so re-applying them is the correct repair rather than restoring from
that backup.

m014 through m018 are async, so they are awaited here.
"""
from __future__ import annotations

import asyncio

import pymongo

import migrations_brands as m


async def run() -> None:
    # Motor, not pymongo: the migrations await db.<collection>.find() and
    # db.<collection>.update_one(), which is the async driver's API.
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["hitech_crm"]
    steps = [
        m.m014_apply_master_brand_list,
        m.m015_seed_product_categories,
        m.m016_add_product_schema,
        m.m017_clean_duplicates,
        m.m018_archive_products_and_merge_categories,
    ]
    for fn in steps:
        try:
            r = await fn(db)
            print(f"  {fn.__name__:44} {r if r is not None else 'ok'}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {fn.__name__:44} FAILED {type(exc).__name__}: {exc}")

    print()
    print(f"  brands total:            {await db.brands.count_documents({})}")
    print(f"  brands active+approved:  {await db.brands.count_documents({'status': 'active', 'approved': True})}")
    print(f"  brands archived:         {await db.brands.count_documents({'status': 'archived'})}")
    print(f"  product categories:      {await db.product_categories.count_documents({})}")
    print(f"  products total:          {await db.products.count_documents({})}")
    print(f"  products active:         {await db.products.count_documents({'status': 'active'})}")

    approved = [
        "RCF", "L-Acoustics", "DiGiCo", "TT+ Audio", "Sound Devices",
        "Klang Technologies", "Radial Engineering", "Fourier Audio", "Audio Press Box",
        "MA Lighting", "MADRIX", "ETC", "Zactrack", "Luminex", "Klotz", "K&M",
        "Sennheiser", "Cotodama", "DPA Microphones", "JH Audio", "Wisycom",
    ]
    have = {b["name"] async for b in db.brands.find(
        {"status": "active", "approved": True})}
    missing = [n for n in approved if n not in have]
    print(f"  missing approved brands: {missing or 'none'}")
    client.close()


if __name__ == "__main__":
    asyncio.run(run())
