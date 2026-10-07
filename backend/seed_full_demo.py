"""Comprehensive demo data seeder with real brand products."""
import os
import sys
import asyncio
import uuid
import random
import bcrypt
from datetime import datetime, timezone, timedelta
from _seed_db import connect_db

sys.stdout.reconfigure(encoding="utf-8")

random.seed(42)
NOW = datetime.now(timezone.utc)

def iso(dt):
    return dt.isoformat()

def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

# ---------- Real products from brand websites ----------
PRODUCTS = [
    # L-Acoustics (https://www.l-acoustics.com/products)
    ("L-Acoustics", "K2", "K2 Line Array Element", "Loudspeakers", 185000),
    ("L-Acoustics", "KS28", "KS28 Subwoofer", "Subwoofers", 245000),
    ("L-Acoustics", "KARA II", "KARA II Downfill Enclosure", "Loudspeakers", 98000),
    ("L-Acoustics", "LA12X", "LA12X Amplified Controller", "Amplified Controllers", 125000),
    ("L-Acoustics", "LA4X", "LA4X Amplified Controller", "Amplified Controllers", 145000),
    ("L-Acoustics", "LA-RAK II", "LA-RAK II AVB (3x LA12X touring rack)", "Racks", 265000),
    ("L-Acoustics", "K2-BUMP", "K2-BUMP Flying Frame", "Rigging", 48000),
    ("L-Acoustics", "K2-BAR", "K2-BAR Extension Bar", "Rigging", 16000),
    ("L-Acoustics", "K2-RIGBAR", "K2-RIGBAR Rigging Bar + Pullback", "Rigging", 28000),
    ("L-Acoustics", "K2-LINK", "K2-LINK Rear Attachment", "Rigging", 12000),
    ("L-Acoustics", "K2-RAKMOUNT", "K2-RAKMOUNT Cradle for LA-RAK", "Rigging", 8500),
    ("L-Acoustics", "K2-CHARIOT", "K2-CHARIOT (4x K2 transport)", "Transport", 42000),
    ("L-Acoustics", "K-BUMPFLIGHT", "K-BUMPFLIGHT (case for 2 K2-BUMP)", "Transport", 19500),
    ("L-Acoustics", "DO.7", "DO.7 Speaker Cable 8x4mm² CA-COM 0.7m", "Cables", 4000),
    ("L-Acoustics", "DO10", "DO10 Speaker Cable 8x4mm² CA-COM 10m", "Cables", 9000),
    ("L-Acoustics", "DO25", "DO25 Speaker Cable 8x4mm² CA-COM 25m", "Cables", 17000),
    ("L-Acoustics", "SB18", "SB18 Subwoofer", "Subwoofers", 195000),
    ("L-Acoustics", "KS21", "KS21 Subwoofer", "Subwoofers", 165000),
    ("L-Acoustics", "A15 Focus", "A15 Focus Line Array Element", "Loudspeakers", 145000),
    ("L-Acoustics", "A10 Focus", "A10 Focus Line Array Element", "Loudspeakers", 115000),
    ("L-Acoustics", "X4", "X4 Concert Enclosure", "Loudspeakers", 75000),
    ("L-Acoustics", "X8", "X8 Concert Enclosure", "Loudspeakers", 85000),
    ("L-Acoustics", "X12", "X12 Concert Enclosure", "Loudspeakers", 95000),
    ("L-Acoustics", "KS28-COV", "KS28-COV Protective Cover", "Protections & Transportation", 5500),
    ("L-Acoustics", "KS28-PLA", "KS28-PLA Removable front dolly", "Protections & Transportation", 12000),
    # RCF (https://www.rcf.it/products)
    ("RCF", "HDL 30-A", "HDL 30-A Active Two-Way Line Array Module", "Line Array", 175000),
    ("RCF", "HDL 28-A", "HDL 28-A Active Two-Way Line Array Module", "Line Array", 145000),
    ("RCF", "HDL 50-A 4K", "HDL 50-A 4K Active Three-Way Line Array Module", "Line Array", 340000),
    ("RCF", "HDL 6-A", "HDL 6-A Active Line Array Module", "Line Array", 85000),
    ("RCF", "HDL 38-AS", "HDL 38-AS Active Flyable Subwoofer Module", "Subwoofers", 225000),
    ("RCF", "SUB 9019-AS", "SUB 9019-AS High Power 19\" Active Subwoofer", "Subwoofers", 125000),
    ("RCF", "SUB 9029-AS", "SUB 9029-AS High Power Dual 19\" Active Subwoofer", "Subwoofers", 195000),
    ("RCF", "NX 915-SMA", "NX 915-SMA Professional Active Stage Monitor", "Stage Monitors", 65000),
    ("RCF", "KXM 25-A", "KXM 25-A Active High Performance Coaxial Stage Monitor", "Stage Monitors", 55000),
    ("RCF", "KXM 20-A", "KXM 20-A Active High Definition Stage Monitor", "Stage Monitors", 42000),
    ("RCF", "TT 25-CXA", "TT 25-CXA Active High Definition Coaxial Monitor", "Stage Monitors", 38000),
    ("RCF", "CR 16-ND", "CR 16-ND Control Rack", "Control Racks", 95000),
    # DiGiCo (https://digico.biz/consoles/)
    ("DiGiCo", "Quantum 338", "Quantum 338 Digital Mixing Console", "Consoles", 4800000),
    ("DiGiCo", "Quantum 225", "Quantum 225 Digital Mixing Console", "Consoles", 1950000),
    ("DiGiCo", "Quantum 112", "Quantum 112 Digital Mixing Console", "Consoles", 950000),
    ("DiGiCo", "SD12", "SD12 Digital Mixing Console", "Consoles", 780000),
    ("DiGiCo", "SD10", "SD10 Digital Mixing Console", "Consoles", 720000),
    ("DiGiCo", "SD9", "SD9 Digital Mixing Console", "Consoles", 620000),
    ("DiGiCo", "S21", "S21 Console with A168 Stage Rack", "S-Series", 420000),
    ("DiGiCo", "S31", "S31 Console with A168 Stage Rack", "S-Series", 580000),
    ("DiGiCo", "SD-Rack", "SD-Rack 192kHz (unloaded)", "Racks", 380000),
    ("DiGiCo", "SD-Rack-O", "SD-Rack 192kHz with HMA Optics", "Racks", 465000),
    ("DiGiCo", "SD-Rack-NC", "SD-Rack 192kHz with OpticalCON", "Racks", 395000),
    ("DiGiCo", "SD-Rack-ST", "SD-Rack 192kHz with ST Optics", "Racks", 380000),
    ("DiGiCo", "SD-MINI Rack", "SD-MINI Rack 192kHz (unloaded)", "Racks", 240000),
    ("DiGiCo", "SD-MINI Rack-O", "SD-MINI Rack 192kHz with HMA Optics", "Racks", 315000),
    ("DiGiCo", "SD-NANO Rack-O", "SD-NANO Rack with HMA Optics", "Racks", 165000),
    ("DiGiCo", "MQ-Rack", "MQ-Rack (with Q225 set, 15% disc)", "Racks", 95000),
    ("DiGiCo", "DQ-Rack", "DQ-Rack", "Racks", 115000),
    ("DiGiCo", "D-Rack-1", "D-Rack - Single PSU", "Racks", 118000),
    ("DiGiCo", "D-Rack-2", "D-Rack - Dual PSU", "Racks", 96000),
    ("DiGiCo", "Orange Box", "Orange Box (Format Converter)", "Interface Boxes", 14500),
    ("DiGiCo", "Purple Box-HMA", "Purple Box - Multimode HMA", "Interface Boxes", 465000),
    ("DiGiCo", "Fourier TE", "Fourier Audio transform.engine", "Fourier Engine", 550000),
    ("DiGiCo", "Fourier TG", "Fourier Audio transform.go", "Fourier Engine", 210000),
]

# ---------- Demo data constants ----------
SALES_REPS = [
    ("Rohan Mehta", "rohan@hitechavl.com", "Demo@123", ["L-Acoustics", "DiGiCo"]),
    ("Priya Singh", "priya@hitechavl.com", "Demo@123", ["RCF"]),
    ("Anil Kumar", "anil@hitechavl.com", "Demo@123", ["L-Acoustics", "RCF", "DiGiCo"]),
    ("Sneha Iyer", "sneha@hitechavl.com", "Demo@123", ["DiGiCo"]),
]

COMPANIES = [
    ("Sunset Events Pvt Ltd", "Mumbai"), ("BlueWave Productions", "Bengaluru"),
    ("Resonance AV", "Delhi"), ("StageCraft India", "Hyderabad"),
    ("Acoustix Solutions", "Pune"), ("Marquee Live", "Chennai"),
    ("Aurora Audio", "Kolkata"), ("Echo Events", "Ahmedabad"),
    ("Soundscape Tech", "Goa"), ("Crescendo Productions", "Jaipur"),
    ("Magnum Live", "Indore"), ("Pinnacle AV", "Chandigarh"),
    ("Velocity Sound", "Kochi"), ("Skyline AV", "Lucknow"),
    ("Spectrum Events", "Surat"),
]

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Ananya", "Aadhya", "Diya", "Ishaan", "Krishna", "Riya", "Saanvi", "Aanya", "Myra", "Kabir"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Reddy", "Khan", "Mehta", "Joshi", "Iyer", "Nair", "Kapoor", "Malhotra", "Bose", "Gupta", "Rao"]

INTERESTS = {
    "L-Acoustics": ["K2 line array for 3000-pax wedding", "K2 + KS28 for festival", "KARA II PA quote", "Syva install for clubhouse", "A15 for theatre", "L-Acoustics X-Series install for auditorium"],
    "RCF": ["RCF HDL 30 line array for concert", "RCF HDL 28-A for hotel ballroom", "RCF SUB 9019-AS for nightclub", "RCF NX 915-SMA for conference hall"],
    "DiGiCo": ["DiGiCo Quantum 338 for festival mixing", "Quantum 225 console for tour", "DiGiCo SD12 for theatre", "Quantum 112 for corporate events", "SD9 with SD-Rack for broadcast"],
}

SOURCES = ["website", "whatsapp", "email", "manual", "referral", "exhibition"]
STAGE_WEIGHTS = [("new", 0.25), ("contacted", 0.22), ("qualified", 0.18), ("quoted", 0.18), ("won", 0.10), ("lost", 0.07)]

PACKAGES = [
    ("L-Acoustics", "K2 PA · Small (≤1500 pax)", "Single-side hang: 8x K2 + 4x KS28 + 2x LA12X + rigging + cabling.", 2850000),
    ("L-Acoustics", "K2 PA · Medium (≤5000 pax)", "Stereo hang: 16x K2 + 8x KS28 + 4x LA12X + full rigging + cabling.", 5200000),
    ("L-Acoustics", "K2 PA · Large touring (10000+ pax)", "Stadium/touring: 24x K2 + 16x KS28 + 8x LA12X (3 racks) + transport.", 8500000),
    ("L-Acoustics", "KARA II Club System", "12x KARA II + 4x SB18 + 2x LA4X + cabling. For mid-size venues.", 2100000),
    ("L-Acoustics", "A15 Theatre Package", "8x A15 Focus + 4x KS21 + 2x LA12X. Theatrical / performing arts.", 3200000),
    ("RCF", "HDL 30-A Line Array · Small", "8x HDL 30-A + 4x HDL 38-AS + cabling. Medium halls / banquets.", 2300000),
    ("RCF", "HDL 30-A Line Array · Medium", "16x HDL 30-A + 8x HDL 38-AS + cabling. Auditoriums / concerts.", 4400000),
    ("RCF", "HDL 28-A Compact System", "8x HDL 28-A + 4x SUB 9019-AS. Compact touring / corporate.", 1800000),
    ("RCF", "HDL 50-A 4K Large Format", "12x HDL 50-A 4K + 8x SUB 9029-AS. Stadium / large festivals.", 7800000),
    ("DiGiCo", "Quantum 338 Touring Package", "Quantum 338 + SD-Rack + D-Rack-2 + HMA Optics. Full touring I/O.", 6800000),
    ("DiGiCo", "Quantum 225 Single Screen", "Quantum 225 + SD-Rack + MADI. Medium shows / theatre.", 3200000),
    ("DiGiCo", "SD12 Live Package", "SD12 + 2x MQ-Rack + cabling. Live / broadcast / corporate.", 2400000),
    ("DiGiCo", "SD9 Broadcast Package", "SD9 Dual PSU + SD-Rack + MADI. Broadcast / IEM.", 1800000),
    ("DiGiCo", "S21 House of Worship", "S21 + A168 Stage Rack + cabling. HOw / install.", 1200000),
]

async def main():
    pool, db = await connect_db()
    print("=== Seeding comprehensive demo data ===")

    # ---------- Users ----------
    rep_ids = []
    for name, email, pw, allowed in SALES_REPS:
        existing = await db.users.find_one({"email": email})
        if existing:
            await db.users.update_one({"email": email}, {"$set": {"name": name, "role": "sales", "allowed_brands": allowed, "password_hash": hash_pw(pw)}})
            rep_ids.append(existing["id"])
        else:
            uid = str(uuid.uuid4())
            await db.users.insert_one({"id": uid, "name": name, "email": email, "password_hash": hash_pw(pw), "role": "sales", "allowed_brands": allowed, "created_at": iso(NOW - timedelta(days=60))})
            rep_ids.append(uid)
    rahul = await db.users.find_one({"email": "sales@hitechaudio.in"})
    if rahul:
        await db.users.update_one({"id": rahul["id"]}, {"$set": {"allowed_brands": ["L-Acoustics", "DiGiCo"]}})
        rep_ids.append(rahul["id"])
    print(f"✓ {len(rep_ids)} sales reps ready")

    # ---------- Products ----------
    brand_models = {}
    for brand, model, name, cat, price in PRODUCTS:
        existing = await db.products.find_one({"brand": brand, "name": name})
        if existing:
            await db.products.update_one({"brand": brand, "name": name}, {"$set": {"unit_price": float(price), "model": model, "category": cat}})
            pid = existing["id"]
        else:
            pid = str(uuid.uuid4())
            await db.products.insert_one({"id": pid, "brand": brand, "name": name, "model": model, "category": cat, "unit_price": float(price), "description": f"{brand} {model} — real product sourced from official catalog.", "created_at": iso(NOW - timedelta(days=30))})
        brand_models.setdefault(brand, []).append({"id": pid, "name": name, "model": model, "unit_price": float(price)})
    print(f"✓ Seeded {len(PRODUCTS)} real products across {len(brand_models)} brands")

    # ---------- Packages ----------
    await db.packages.delete_many({})
    model_to_id = {p["model"]: p["id"] for ps in brand_models.values() for p in ps}
    for brand, name, desc, fixed in PACKAGES:
        items = []
        if brand == "L-Acoustics" and "K2" in name:
            if "Small" in name:
                items = [("K2", 8), ("KS28", 4), ("LA12X", 2), ("LA-RAK II", 1), ("K2-BUMP", 1), ("K2-RIGBAR", 1), ("DO25", 2), ("DO.7", 4), ("K2-CHARIOT", 2)]
            elif "Large" in name:
                items = [("K2", 24), ("KS28", 16), ("LA12X", 8), ("LA-RAK II", 3), ("K2-BUMP", 2), ("K2-BAR", 4), ("K2-RIGBAR", 2), ("K2-LINK", 4), ("DO25", 8), ("DO10", 4), ("DO.7", 12), ("K2-CHARIOT", 6), ("K-BUMPFLIGHT", 2)]
            else:
                items = [("K2", 16), ("KS28", 8), ("LA12X", 4), ("LA-RAK II", 2), ("K2-BUMP", 2), ("K2-BAR", 2), ("K2-RIGBAR", 2), ("DO25", 4), ("DO10", 2), ("DO.7", 8), ("K2-CHARIOT", 4), ("K-BUMPFLIGHT", 1)]
        elif brand == "L-Acoustics" and "KARA" in name:
            items = [("KARA II", 12), ("SB18", 4), ("LA4X", 2), ("DO25", 2), ("DO10", 2), ("DO.7", 6)]
        elif brand == "L-Acoustics" and "A15" in name:
            items = [("A15 Focus", 8), ("KS21", 4), ("LA12X", 2), ("DO25", 2), ("DO.7", 8)]
        elif brand == "RCF" and "HDL 30-A" in name and "Small" in name:
            items = [("HDL 30-A", 8), ("HDL 38-AS", 4)]
        elif brand == "RCF" and "HDL 30-A" in name and "Medium" not in name and "Large" not in name:
            items = [("HDL 30-A", 16), ("HDL 38-AS", 8)]
        elif brand == "RCF" and "HDL 28-A" in name:
            items = [("HDL 28-A", 8), ("SUB 9019-AS", 4)]
        elif brand == "RCF" and "HDL 50-A" in name:
            items = [("HDL 50-A 4K", 12), ("SUB 9029-AS", 8)]
        elif brand == "DiGiCo" and "Quantum 338" in name:
            items = [("Quantum 338", 1), ("SD-Rack", 1), ("D-Rack-2", 1), ("SD-Rack-O", 1)]
        elif brand == "DiGiCo" and "Quantum 225" in name:
            items = [("Quantum 225", 1), ("SD-Rack", 1), ("D-Rack-1", 1)]
        elif brand == "DiGiCo" and "SD12" in name:
            items = [("SD12", 1), ("MQ-Rack", 2)]
        elif brand == "DiGiCo" and "SD9" in name:
            items = [("SD9", 1), ("SD-Rack", 1), ("D-Rack-1", 1)]
        elif brand == "DiGiCo" and "S21" in name:
            items = [("S21", 1), ("A168 Stage Rack", 1)]
        else:
            continue
        pkg_items = [{"product_id": model_to_id[m], "qty": q} for m, q in items if m in model_to_id]
        await db.packages.insert_one({"id": str(uuid.uuid4()), "brand": brand, "name": name, "description": desc, "items": pkg_items, "fixed_price_inr": float(fixed), "created_at": iso(NOW - timedelta(days=25))})
    print(f"✓ Seeded {len(PACKAGES)} packages")

    # ---------- Clear old demo data ----------
    await db.leads.delete_many({"demo_seed": True})
    await db.activities.delete_many({"demo_seed": True})
    await db.quotations.delete_many({"demo_seed": True})
    await db.shipments.delete_many({"demo_seed": True})
    await db.inventory.delete_many({"demo_seed": True})
    await db.amcs.delete_many({"demo_seed": True})

    # ---------- Leads ----------
    leads = []
    for i in range(60):
        days_ago = random.choices(range(0, 30), weights=[1, 2, 3, 3, 4, 4, 5, 4, 5, 6, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1])[0]
        created = NOW - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        comp, city = random.choice(COMPANIES)
        stage = random.choices([s for s, _ in STAGE_WEIGHTS], weights=[w for _, w in STAGE_WEIGHTS])[0]
        source = random.choice(SOURCES)
        brand = random.choice(list(brand_models.keys()))
        interested = random.choice(INTERESTS.get(brand, INTERESTS["L-Acoustics"]))
        budget = random.choice([None, 250000, 500000, 1200000, 3500000, 8000000, 15000000, 25000000])
        lid = str(uuid.uuid4())
        assigned = random.choice(rep_ids)
        leads.append({
            "id": lid, "name": f"{first} {last}", "email": f"{first.lower()}.{last.lower()}@{comp.split()[0].lower()}.in",
            "phone": f"+91 9{random.randint(100000000, 999999999)}", "company": f"{comp} · {city}",
            "source": source, "interested_in": interested, "budget": budget, "notes": None,
            "stage": stage, "assigned_to": assigned, "created_by": rep_ids[0],
            "created_at": iso(created), "updated_at": iso(created), "demo_seed": True,
        })
    await db.leads.insert_many(leads)
    print(f"✓ Inserted {len(leads)} demo leads")

    # ---------- Activities ----------
    acts = []
    for ld in leads:
        n_acts = random.randint(1, 4)
        base = datetime.fromisoformat(ld["created_at"])
        for j in range(n_acts):
            t = base + timedelta(hours=random.randint(2, 72) * (j + 1))
            if t > NOW:
                t = NOW - timedelta(hours=1)
            acts.append({
                "id": str(uuid.uuid4()), "lead_id": ld["id"], "user_id": ld["assigned_to"],
                "type": random.choice(["note", "call", "email", "whatsapp", "meeting"]),
                "content": random.choice([
                    "Sent initial product catalogue and spec sheet.",
                    "Discussed venue dimensions and SPL targets.",
                    "Awaiting confirmation on budget approval.",
                    "Customer requested demo at their facility.",
                    "Shared package quotation v1 via email.",
                    "Site visit scheduled for next week.",
                    "Asked about service/AMC options after install.",
                    "Followed up on quotation — asked for revised pricing.",
                    "Provided technical specs for K2 vs HDL comparison.",
                    "Client confirmed venue date; need final rigging plan.",
                ]),
                "follow_up_at": None, "created_at": iso(t), "demo_seed": True,
            })
        if random.random() < 0.35 and ld["stage"] not in ("won", "lost"):
            future = NOW + timedelta(days=random.randint(1, 14), hours=random.randint(0, 8))
            acts.append({
                "id": str(uuid.uuid4()), "lead_id": ld["id"], "user_id": ld["assigned_to"],
                "type": random.choice(["call", "meeting", "follow_up"]),
                "content": random.choice(["Follow up on quotation acceptance.", "Site recce and final dimension confirmation.", "Send revised commercials post negotiation.", "Demo session at client venue.", "Confirm GST + shipping terms before PO."]),
                "follow_up_at": iso(future), "created_at": iso(NOW - timedelta(hours=2)), "demo_seed": True,
            })
    await db.activities.insert_many(acts)
    print(f"✓ Inserted {len(acts)} demo activities")

    # ---------- Quotations ----------
    qs = []
    counter = await db.quotations.count_documents({})
    for ld in leads:
        if ld["stage"] not in ("qualified", "quoted", "won", "lost"):
            continue
        if random.random() > 0.6:
            continue
        brand = random.choice(list(brand_models.keys()))
        candidates = brand_models.get(brand, [])
        if not candidates:
            continue
        items = []
        for _ in range(random.randint(2, 6)):
            p = random.choice(candidates)
            qty = random.choice([1, 1, 2, 2, 4, 8])
            items.append({"product": f"{p['name']} ({p['model']})", "brand": brand, "qty": qty, "unit_price": p["unit_price"], "tax_pct": 18.0})
        subtotal = sum(i["qty"] * i["unit_price"] for i in items)
        tax = sum(i["qty"] * i["unit_price"] * 0.18 for i in items)
        total = subtotal + tax
        counter += 1
        if ld["stage"] == "won":
            status = "accepted"
        elif ld["stage"] == "lost":
            status = "rejected"
        elif ld["stage"] == "quoted":
            status = random.choice(["sent", "sent", "draft"])
        else:
            status = "draft"
        created = datetime.fromisoformat(ld["created_at"]) + timedelta(days=random.randint(1, 7))
        if created > NOW:
            created = NOW - timedelta(hours=4)
        qs.append({
            "id": str(uuid.uuid4()), "quote_no": f"HAI-Q-{1000 + counter}", "lead_id": ld["id"],
            "items": items, "subtotal": round(subtotal, 2), "tax": round(tax, 2), "total": round(total, 2),
            "valid_until": iso(created + timedelta(days=15)),
            "terms": "Payment: 50% advance, 50% on delivery. Validity: 15 days.",
            "status": status, "created_by": ld["assigned_to"], "created_at": iso(created), "demo_seed": True,
        })
    if qs:
        await db.quotations.insert_many(qs)
    print(f"✓ Inserted {len(qs)} demo quotations")

    # ---------- Shipments ----------
    shipments = []
    for i in range(8):
        oem = random.choice(list(brand_models.keys()))
        po_no = f"PO-2026-{1000 + i}"
        created = NOW - timedelta(days=random.randint(10, 60))
        status = random.choice(["planned", "in_transit", "customs", "cleared", "received"])
        eta = (NOW + timedelta(days=random.randint(-5, 30))).date().isoformat()
        items = []
        for _ in range(random.randint(2, 5)):
            p = random.choice(brand_models.get(oem, []))
            items.append({"product_id": p["id"], "qty": random.choice([1, 2, 4, 8]), "fob_unit": round(p["unit_price"] * random.uniform(0.6, 0.85), 2)})
        shipments.append({
            "id": str(uuid.uuid4()), "po_no": po_no, "oem": oem, "currency": "EUR",
            "items": items, "bl_awb": f"AWB{random.randint(100000,999999)}", "eta": eta,
            "status": status, "notes": f"Demo shipment for {oem} PO {po_no}",
            "created_at": iso(created), "demo_seed": True,
        })
    await db.shipments.insert_many(shipments)
    print(f"✓ Inserted {len(shipments)} demo shipments")

    # ---------- Inventory ----------
    inventory = []
    for sh in shipments:
        if sh["status"] in ("cleared", "received"):
            for it in sh["items"]:
                for _ in range(it["qty"]):
                    inventory.append({
                        "id": str(uuid.uuid4()), "product_id": it["product_id"],
                        "serial_no": f"SN-{uuid.uuid4().hex[:8].upper()}", "shipment_id": sh["id"],
                        "location": random.choice(["Main Warehouse", "Gurgaon Godown", "Mumbai Office"]),
                        "status": random.choice(["in_stock", "in_stock", "reserved", "sold"]),
                        "landed_cost_inr": round(it["fob_unit"] * 83, 2),
                        "sold_to_lead_id": None, "warranty_expires": None,
                        "created_at": iso(NOW - timedelta(days=random.randint(1, 20))), "demo_seed": True,
                    })
    if inventory:
        await db.inventory.insert_many(inventory)
    print(f"✓ Inserted {len(inventory)} demo inventory units")

    # ---------- AMCs ----------
    amcs = []
    for ld in random.sample(leads, min(15, len(leads))):
        if ld["stage"] in ("won",):
            start = NOW - timedelta(days=random.randint(30, 180))
            end = start + timedelta(days=365)
            amcs.append({
                "id": str(uuid.uuid4()), "customer_name": ld["name"], "customer_company": ld["company"],
                "lead_id": ld["id"], "serial_numbers": [f"SN-{uuid.uuid4().hex[:8].upper()}" for _ in range(random.randint(1, 3))],
                "start_date": iso(start), "end_date": iso(end), "value": round(random.uniform(50000, 500000), 2),
                "status": "active", "notes": "Annual maintenance contract — on-site support, 48hr response.", "created_at": iso(start), "demo_seed": True,
            })
    if amcs:
        await db.amcs.insert_many(amcs)
    print(f"✓ Inserted {len(amcs)} demo AMCs")

    print("\n=== Demo data seeded successfully ===")
    print(f"Backend: http://localhost:8000")
    print(f"Frontend: http://localhost:3000")
    print(f"Login: admin@hitechaudio.in / Admin@123")
    print(f"\nSales reps: {', '.join(name for name,_,_,_ in SALES_REPS)}")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
