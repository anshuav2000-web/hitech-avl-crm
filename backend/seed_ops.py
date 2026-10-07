"""Seed demo shipments, inventory, and AMC data so the new pages have life."""
import os
import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from _seed_db import connect_db

random.seed(11)
NOW = datetime.now(timezone.utc)

async def main():
    pool, db = await connect_db()
    await db.shipments.delete_many({"demo": True})
    await db.inventory.delete_many({"demo": True})
    await db.amcs.delete_many({"demo": True})

    # Get a handful of products per brand
    prods = await db.products.find({}, {"_id": 0}).to_list(2000)
    by_brand = {}
    for p in prods:
        by_brand.setdefault(p["brand"], []).append(p)

    # ---- Shipments ----
    shipments = []
    plans = [
        ("HAI-PO-2026-01", "L-Acoustics", "EUR", "received", -45),
        ("HAI-PO-2026-02", "DiGiCo",      "GBP", "cleared", -8),
        ("HAI-PO-2026-03", "RCF",         "EUR", "customs", -2),
        ("HAI-PO-2026-04", "L-Acoustics", "EUR", "in_transit", 18),
        ("HAI-PO-2026-05", "DiGiCo",      "GBP", "in_transit", 25),
        ("HAI-PO-2026-06", "RCF",         "EUR", "planned",   42),
    ]
    for po, oem, ccy, status, eta_offset in plans:
        if oem not in by_brand or not by_brand[oem]:
            continue
        # 2-4 line items
        picks = random.sample(by_brand[oem], min(len(by_brand[oem]), random.randint(2, 4)))
        items = [{"product_id": p["id"], "qty": random.choice([2, 4, 6, 8, 10]), "fob_unit": round(random.uniform(800, 22000), 2)} for p in picks]
        eta = (NOW + timedelta(days=eta_offset)).date().isoformat()
        actual = eta if status == "received" else None
        sid = str(uuid.uuid4())
        shipments.append({
            "id": sid, "po_no": po, "oem": oem, "currency": ccy,
            "items": items,
            "bl_awb": f"BL{random.randint(100000, 999999)}",
            "eta": eta, "actual_arrival": actual,
            "freight_cost_inr": round(random.uniform(120000, 850000), 0) if status != "planned" else 0.0,
            "duty_paid_inr": round(random.uniform(180000, 1500000), 0) if status in ("cleared", "received") else 0.0,
            "status": status,
            "notes": f"Container via {'sea' if random.random() > 0.3 else 'air'} freight",
            "created_at": (NOW - timedelta(days=max(0, -eta_offset) + 30)).isoformat(),
            "demo": True,
        })
        # If status >= cleared, create inventory units
        if status in ("cleared", "received"):
            for it in items:
                for k in range(it["qty"]):
                    serial = f"{oem[:2].upper()}-{po[-2:]}-{k+1:03d}"
                    sold = random.random() < 0.25
                    await db.inventory.insert_one({
                        "id": str(uuid.uuid4()),
                        "product_id": it["product_id"],
                        "serial_no": serial,
                        "shipment_id": sid,
                        "location": "Main Warehouse, Mumbai",
                        "status": "sold" if sold else "in_stock",
                        "landed_cost_inr": round(it["fob_unit"] * (90 if ccy == "EUR" else 105 if ccy == "GBP" else 85) * 1.45, 0),
                        "sold_to_lead_id": None,
                        "warranty_expires": ((NOW + timedelta(days=365)).date().isoformat() if sold else None),
                        "created_at": NOW.isoformat(),
                        "demo": True,
                    })
        elif status == "in_transit":
            for it in items:
                for k in range(it["qty"]):
                    await db.inventory.insert_one({
                        "id": str(uuid.uuid4()),
                        "product_id": it["product_id"],
                        "serial_no": f"{oem[:2].upper()}-{po[-2:]}-T{k+1:03d}",
                        "shipment_id": sid,
                        "location": "In transit",
                        "status": "in_transit",
                        "landed_cost_inr": None,
                        "sold_to_lead_id": None,
                        "warranty_expires": None,
                        "created_at": NOW.isoformat(),
                        "demo": True,
                    })
    await db.shipments.insert_many(shipments)
    print(f"Inserted {len(shipments)} shipments + inventory units")

    # ---- AMCs ----
    amcs = []
    customers = [
        ("Sunset Events Pvt Ltd",       "Mumbai"),
        ("BlueWave Productions",        "Bengaluru"),
        ("Marquee Live",                "Chennai"),
        ("Resonance AV",                "Delhi"),
        ("Crescendo Productions",       "Jaipur"),
        ("Skyline AV",                  "Lucknow"),
        ("Velocity Sound",              "Kochi"),
    ]
    for name, city in customers:
        start_offset = random.randint(-330, -30)
        duration = random.choice([365, 365, 730])
        start = (NOW + timedelta(days=start_offset)).date().isoformat()
        end_date = (NOW + timedelta(days=start_offset + duration)).date()
        end_iso = end_date.isoformat()
        # Some expiring soon
        if random.random() < 0.5:
            end_date = (NOW + timedelta(days=random.randint(5, 55))).date()
            end_iso = end_date.isoformat()
        days_to_end = (end_date - NOW.date()).days
        status = "active" if days_to_end > 0 else "expired"
        amcs.append({
            "id": str(uuid.uuid4()),
            "customer_name": name,
            "customer_company": city,
            "lead_id": None,
            "serial_numbers": [f"LA-01-{i:03d}" for i in random.sample(range(1, 50), random.randint(2, 6))],
            "start_date": start, "end_date": end_iso,
            "value": random.choice([85000, 125000, 240000, 380000, 620000]),
            "status": status,
            "notes": "Includes 2 site visits + spares + OEM escalation",
            "created_at": NOW.isoformat(),
            "demo": True,
        })
    await db.amcs.insert_many(amcs)
    print(f"Inserted {len(amcs)} AMCs")
    await pool.close()

asyncio.run(main())
