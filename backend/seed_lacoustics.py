"""Seed L-Acoustics K2-ecosystem products and 3 package templates.
Prices are placeholders (0.00) until the official L-Acoustics pricelist is loaded.
Idempotent: re-running clears L-Acoustics products+packages and re-seeds.
"""
import os
import asyncio
import uuid
from datetime import datetime, timezone
from _seed_db import connect_db

# L-Acoustics K2 ecosystem (model | name | category)
PRODUCTS = [
    # Enclosures
    ("K2",          "K2 Line Array Element",                      "Loudspeakers"),
    ("KS28",        "KS28 Subwoofer",                             "Subwoofers"),
    ("KARA-II",     "KARA II Downfill Enclosure",                 "Loudspeakers"),
    # Amplified controllers
    ("LA12X",       "LA12X Amplified Controller",                 "Amplified Controllers"),
    ("LA-RAK-II",   "LA-RAK II AVB (3x LA12X touring rack)",      "Racks"),
    # Rigging
    ("K2-BUMP",     "K2-BUMP Flying Frame",                       "Rigging"),
    ("K2-BAR",      "K2-BAR Extension Bar",                       "Rigging"),
    ("K2-RIGBAR",   "K2-RIGBAR Rigging Bar + Pullback",           "Rigging"),
    ("K2-LINK",     "K2-LINK Rear Attachment",                    "Rigging"),
    ("K2-RAKMOUNT", "K2-RAKMOUNT Cradle for LA-RAK",              "Rigging"),
    ("LA-SLING2T",  "LA-SLING2T 1m Chain Sling (2t)",             "Rigging"),
    # Cables
    ("DO.7",        "DO.7 Speaker Cable 8x4mm² CA-COM 0.7m",      "Cables"),
    ("DO10",        "DO10 Speaker Cable 8x4mm² CA-COM 10m",       "Cables"),
    ("DO25",        "DO25 Speaker Cable 8x4mm² CA-COM 25m",       "Cables"),
    # Transport
    ("K2-CHARIOT",  "K2-CHARIOT (4x K2 transport)",               "Transport"),
    ("K-BUMPFLIGHT","K-BUMPFLIGHT (case for 2 K2-BUMP)",          "Transport"),
]

# Package templates: (name, description, items by model + qty)
PACKAGES = [
    (
        "K2 PA · Small (≤1500 pax)",
        "Single-side hang of 8x K2 + 4x KS28 + 2x LA12X. For mid-size halls, banquets, corporate events.",
        [("K2", 8), ("KS28", 4), ("LA12X", 2), ("LA-RAK-II", 1),
         ("K2-BUMP", 1), ("K2-RIGBAR", 1), ("DO25", 2), ("DO.7", 4),
         ("K2-CHARIOT", 2)],
    ),
    (
        "K2 PA · Medium (≤5000 pax)",
        "Stereo hang: 16x K2 + 8x KS28 + 4x LA12X + full rigging + cabling. Auditoriums, concerts, festivals.",
        [("K2", 16), ("KS28", 8), ("LA12X", 4), ("LA-RAK-II", 2),
         ("K2-BUMP", 2), ("K2-BAR", 2), ("K2-RIGBAR", 2),
         ("DO25", 4), ("DO10", 2), ("DO.7", 8),
         ("K2-CHARIOT", 4), ("K-BUMPFLIGHT", 1)],
    ),
    (
        "K2 PA · Large touring (10000+ pax)",
        "Stadium / large touring: 24x K2 + 16x KS28 + 8x LA12X (3 racks) + redundant rigging + transport.",
        [("K2", 24), ("KS28", 16), ("LA12X", 8), ("LA-RAK-II", 3),
         ("K2-BUMP", 2), ("K2-BAR", 4), ("K2-RIGBAR", 2),
         ("K2-LINK", 4), ("LA-SLING2T", 4),
         ("DO25", 8), ("DO10", 4), ("DO.7", 12),
         ("K2-CHARIOT", 6), ("K-BUMPFLIGHT", 2)],
    ),
]

async def main():
    pool, db = await connect_db()

    # clear L-Acoustics products + packages
    pr = await db.products.delete_many({"brand": "L-Acoustics"})
    pk = await db.packages.delete_many({"brand": "L-Acoustics"})
    print(f"Cleared {pr.deleted_count} products, {pk.deleted_count} packages")

    # Insert products keyed by model for lookup
    model_to_id = {}
    for model, name, cat in PRODUCTS:
        pid = str(uuid.uuid4())
        await db.products.insert_one({
            "id": pid,
            "brand": "L-Acoustics",
            "name": name,
            "model": model,
            "category": cat,
            "unit_price": 0.0,
            "description": "Placeholder price — awaiting L-Acoustics pricelist",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        model_to_id[model] = pid
    print(f"Inserted {len(PRODUCTS)} L-Acoustics products")

    for name, desc, items in PACKAGES:
        await db.packages.insert_one({
            "id": str(uuid.uuid4()),
            "brand": "L-Acoustics",
            "name": name,
            "description": desc,
            "items": [{"product_id": model_to_id[m], "qty": q} for m, q in items],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    print(f"Inserted {len(PACKAGES)} L-Acoustics package templates")
    await pool.close()

asyncio.run(main())
