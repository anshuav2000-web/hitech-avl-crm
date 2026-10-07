"""One-time DiGiCo catalog import.
Loads customer prices from the pricelist, dedupes by (brand, name, model, unit_price),
and keeps system/package SKUs intact.

Uses PostgreSQL via pgdb (PostgresDocumentDB) — no MongoDB dependency.
Run: DATABASE_URL=postgresql://... python seed_digico.py
"""
import asyncio
import uuid
from datetime import datetime, timezone

from _seed_db import connect_db

# Hand-curated, deduped subset of the DiGiCo 2026 customer pricelist
# (rows with null prices and obvious duplicate rows already filtered;
# package/system SKUs preserved as separate entries)
PRODUCTS = [
    # ---- Quantum 112 ----
    ("Quantum 112 Surface Only",            "X-Q112-WS",       "Quantum 112 Surface",   1411200),
    ("Quantum 112 System - MADI (pkg)",     "X-Q112-MQ",       "Quantum 112 Package",   2817990),
    ("Quantum 112 System - DANTE (pkg)",    "X-Q112-DQ",       "Quantum 112 Package",   2880612),
    # ---- Quantum 225 packages ----
    ("Quantum 225 Single Screen System - MADI (1x MQ Rack) (pkg)",  "X-Q225-WS-SS-MADI",  "Quantum 225 Package",  11152400),
    ("Quantum 225 Dual Screen System - MADI (2x MQ Rack) (pkg)",    "X-Q225-WS-DS-MADI",  "Quantum 225 Package",  13263672),
    ("Quantum 225 Single Screen System - Optics (1x SD Rack) (pkg)","X-Q225-WS-SS-OP",    "Quantum 225 Package",   7678800),
    ("Quantum 225 Dual Screen System - Optics (1x SD Rack) (pkg)",  "X-Q225-WS-DS-OP",    "Quantum 225 Package",   9060984),
    # ---- Quantum 225 surfaces ----
    ("Quantum 225 Single Screen Surface",   "X-Q225-WS",       "Quantum 225 Surface",   1808027),
    ("Quantum 225 Dual Screen Surface",     "X-Q225-WS-DS",    "Quantum 225 Surface",   2160900),
    # ---- Quantum 338 ----
    ("Quantum 338 32bit System (pkg)",      "X-Q338-SYS",      "Quantum 338 Package",   8988637),
    ("Quantum 338 Surface",                 "X-Q338-WS",       "Quantum 338 Surface",   6330026),
    ("Quantum 338 Surface - HMA Optics",    "X-Q338-WS-OP",    "Quantum 338 Surface",   5274338),
    ("Quantum 338 Surface - NC Optics",     "X-Q338-WS-NC",    "Quantum 338 Surface",   5950656),
    ("Quantum 338 Surface - ST Optics",     "X-Q338-WS-ST",    "Quantum 338 Surface",   5828918),
    # ---- Quantum 326 ----
    ("Quantum 326 Surface",                 "X-Q326-WS",       "Quantum 326 Surface",   4533165),
    ("Quantum 326 Surface - HMA Optics",    "X-Q326-WS-OP",    "Quantum 326 Surface",   5209482),
    ("Quantum 326 Surface - NC Optics",     "X-Q326-WS-NC",    "Quantum 326 Surface",   5107283),
    ("Quantum 326 Surface - ST Optics",     "X-Q326-WS-ST",    "Quantum 326 Surface",   5087745),
    # ---- Quantum 5 ----
    ("Quantum 5 32bit Touring System (pkg)","X-Q5-SYS",        "Quantum 5 Package",    16604198),
    ("Quantum 5 Surface - MADI",            "X-Q5-WS",         "Quantum 5 Surface",    11693097),
    ("Quantum 5 Surface - MADI / HMA Optics","X-Q5-WS-OP",     "Quantum 5 Surface",     8662490),
    ("Quantum 5 Surface - MADI / NC Optics","X-Q5-WS-NC",      "Quantum 5 Surface",    12148564),
    ("Quantum 5 Surface - MADI / ST Optics","X-Q5-WS-ST",      "Quantum 5 Surface",    12148564),
    # ---- Quantum 7 ----
    ("Quantum 7 32bit Touring System (pkg)","X-Q7-SYS",        "Quantum 7 Package",    20699598),
    ("Quantum 7 Surface - MADI / HMA Optics","X-SD7-Q7-OP",    "Quantum 7 Surface",    16589220),
    ("Quantum 7 Surface - MADI / NC Optics","X-SD7-Q7-NC",     "Quantum 7 Surface",    16333722),
    ("Quantum 7 Surface - MADI / ST Optics","X-SD7-Q7-ST",     "Quantum 7 Surface",    16284877),
    # ---- Quantum 852 ----
    ("Quantum 852 Surface - MADI / HMA Optics","X-Q852-WS-OP", "Quantum 852 Surface",  20188060),
    ("Quantum 852 Surface - MADI / NC Optics", "X-Q852-WS-NC", "Quantum 852 Surface",  16152468),
    ("Quantum 852 Surface - MADI / ST Optics", "X-Q852-WS-ST", "Quantum 852 Surface",  16113392),
    # ---- SD9 ----
    ("SD9 System - Single PSU (pkg)",       "X-SD9-1P",        "SD9 Package",           1758593),
    ("SD9 System - Dual PSU (pkg)",         "X-SD9-2P",        "SD9 Package",           1838916),
    ("SD9 Rack Pack System (pkg)",          "X-SD9-2P-2R",     "SD9 Package",           2135661),
    ("SD9 D2 System (pkg)",                 "X-SD9-D2-1",      "SD9 Package",           1954641),
    ("SD9 Surface - Single PSU",            "X-SD9-WS",        "SD9 Surface",           1238446),
    ("SD9 Surface - Dual PSU",              "X-SD9-WS-2P",     "SD9 Surface",           1295011),
    # ---- SD10 / SD12 packages ----
    ("SD10 with 2x MQ Rack (pkg)",          "X-SD10-MQ2",      "SD10 Package",          2160900),
    ("SD10 with 1x SD Rack (pkg)",          "X-SD10-SD1",      "SD10 Package",          2567398),
    ("SD12 with 1x D2 Rack (pkg)",          "X-SD12-D2-1",     "SD12 Package",          2567398),
    ("SD12 with 2x D2 Rack (pkg)",          "X-SD12-D2-2",     "SD12 Package",          2119652),
    ("SD12 with 1x DQ Rack (pkg)",          "X-SD12-DQ-1",     "SD12 Package",          2119652),
    # ---- S-Series ----
    ("S21 Console with A168 Stage Rack",    "X-S21-STAGE48",   "S-Series",               930053),
    ("S31 Console with A168 Stage Rack",    "X-S31-STAGE48",   "S-Series",               764051),
    # ---- Racks ----
    ("SD-Rack 192kHz (unloaded)",           "X-SD-RACK",       "Racks",                  402192),
    ("SD-Rack 192kHz with HMA Optics",      "X-SD-RACK-O",     "Racks",                  488055),
    ("SD-Rack 192kHz with OpticalCON",      "X-SD-RACK-NC",    "Racks",                  411585),
    ("SD-Rack 192kHz with ST Optics",       "X-SD-RACK-ST",    "Racks",                  396966),
    ("SD-MINI Rack 192kHz (unloaded)",      "X-SDRM-MADI",     "Racks",                  249088),
    ("SD-MINI Rack 192kHz with HMA Optics", "X-SDRM-OP",       "Racks",                  326682),
    ("SD-MINI Rack 192kHz with OpticalCON", "X-SDRM-NC",       "Racks",                  235593),
    ("SD-MINI Rack 192kHz with ST Optics",  "X-SDRM-ST",       "Racks",                  221536),
    ("SD-NANO Rack with HMA Optics",        "X-SDRN-OP",       "Racks",                  145067),
    ("SD-NANO Rack with OpticalCON",        "X-SDRN-NC",       "Racks",                  130448),
    ("SD-NANO Rack with ST Optics",         "X-SDRN-ST",       "Racks",                  111893),
    ("MQ-Rack (with Q225 set, 15% disc)",   "X-MQ-RACK",       "Racks",                   26654),
    ("DQ-Rack",                             "X-DQ-RACK",       "Racks",                   32168),
    ("D-Rack - Single PSU",                 "X-D-RACK-1",      "Racks",                   33174),
    ("D-Rack - Dual PSU",                   "X-D-RACK-2",      "Racks",                   26989),
    # ---- Interface boxes / Orange Box ----
    ("Orange Box (Format Converter)",       "X-OB",            "Interface Boxes",            449),
    ("Purple Box - Multimode HMA",          "X-PB-HMA",        "Interface Boxes",        489510),
    ("Purple Box - Multimode NC",           "X-PB-NC",         "Interface Boxes",        310905),
    ("Purple Box - Multimode ST",           "X-PB-ST",         "Interface Boxes",        121055),
    ("Purple Box - Singlemode HMA",         "X-PB-OP-S",       "Interface Boxes",        489510),
    ("Purple Box - Singlemode NC",          "X-PB-NC-S",       "Interface Boxes",        310905),
    ("Purple Box - Singlemode ST",          "X-PB-ST-S",       "Interface Boxes",        259970),
    # ---- Fourier Audio ----
    ("Fourier Audio transform.engine",      "X-FA-TE",         "Fourier Engine",         529200),
    ("Fourier Audio transform.go",          "X-FA-TG",         "Fourier Engine",         203742),
    # ---- KLANG ----
    ("KLANG:konductor 128 input Optocore (HMA) pkg",  "X-KG-KOND-OP",   "KLANG Package",          1253724),
    ("KLANG:konductor 128 input Optocore (NC) pkg",   "X-KG-KOND-NC",   "KLANG Package",           969459),
    ("KLANG:konductor 128 input Optocore (ST) pkg",   "X-KG-KOND-ST",   "KLANG Package",           969459),
    ("KLANG:konductor 128 input Dante pkg",           "X-KG-KOND-DAN2", "KLANG Package",           814399),
    ("KLANG:konductor 128 input MADI pkg",            "X-KG-KOND-MADI", "KLANG Package",           695339),
    ("KLANG:konductor",                                "X-KG-KOND",      "KLANG IEM Processor",     570009),
    ("KLANG:vokal",                                    "X-KG-VOKAL",     "KLANG IEM Processor",      84352),
    ("KLANG:dmi",                                      "MOD-DMI-KLANG",  "KLANG IEM Processor",      59403),
    ("KLANG:one Pro",                                  "X-KG-ONE-PRO",   "KLANG IEM Processor",       9158),
    ("KLANG:one",                                      "X-KG-ONE",       "KLANG IEM Processor",       9158),
    ("KLANG:kontroller",                               "X-KG-KONTROL",   "KLANG Controller",         14553),
    ("KLANG:kontroller bundle (6x)",                   "X-KG-KONTROL6",  "KLANG Controller",         20665),
    ("KLANG Immersive Personal Monitor System (pkg)",  "X-KG-IPMS",      "KLANG Package",            16532),
    ("KLANG:quelle - compact headphone amp",           "X-KG-QUELLE",    "KLANG Breakout",           11642),
    ("KLANG:quelle XDM Breakout Box - Dante & MADI",   "X-KG-QUELLE-XDM","KLANG Breakout",          141734),
]


async def main():
    pool, db = await connect_db()

    # Idempotent: drop all DiGiCo products and re-seed clean
    deleted = await db.products.delete_many({"brand": "DiGiCo"})
    print(f"Cleared {deleted.deleted_count} existing DiGiCo products")

    inserted = 0
    seen = set()
    for name, model, category, price in PRODUCTS:
        key = (name.strip().lower(), str(model).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        await db.products.insert_one({
            "id": str(uuid.uuid4()),
            "brand": "DiGiCo",
            "name": name,
            "model": model,
            "category": category,
            "unit_price": float(price),
            "description": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        inserted += 1
    print(f"Inserted {inserted} DiGiCo products")

    await pool.close()


asyncio.run(main())
