"""Seed rich demo data so the dashboard shows real-looking activity.

Uses PostgreSQL via pgdb (PostgresDocumentDB) — no MongoDB dependency.
Run: DATABASE_URL=postgresql://... python seed_demo.py
"""
import os
import asyncio
import uuid
import random
import bcrypt
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv()

random.seed(7)
NOW = datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


SALES_REPS = [
    ("Rohan Mehta",   "rohan@hitechavl.com",  "Demo@123", ["L-Acoustics", "DiGiCo"]),
    ("Priya Singh",   "priya@hitechavl.com",  "Demo@123", ["RCF"]),
    ("Anil Kumar",    "anil@hitechavl.com",   "Demo@123", ["L-Acoustics", "RCF", "DiGiCo"]),
    ("Sneha Iyer",    "sneha@hitechavl.com",  "Demo@123", ["DiGiCo"]),
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
    "L-Acoustics": ["K2 line array for 3000-pax wedding", "L-Acoustics K2 + KS28 for festival",
                    "Kara II PA quote", "Syva install for clubhouse",
                    "X-Series install for auditorium", "L-Acoustics A15 for theatre"],
    "RCF": ["RCF HDL line array for outdoor concert", "RCF TT+ install for hotel ballroom",
            "RCF point source for conference hall", "RCF SUB 9007 for nightclub"],
    "DiGiCo": ["DiGiCo SD12 for festival mixing", "Quantum 338 console for tour",
               "DiGiCo SD9 for theatre", "Quantum 225 for broadcast", "SD-Rack with HMA optics"],
    "generic": ["Full PA system enquiry", "Touring rig requirement",
                "Broadcast audio upgrade", "Convention center AV refit"],
}

SOURCES = ["website", "whatsapp", "email", "manual", "referral", "exhibition"]
STAGE_WEIGHTS = [
    ("new", 0.25), ("contacted", 0.22), ("qualified", 0.18),
    ("quoted", 0.18), ("won", 0.10), ("lost", 0.07),
]


async def main():
    import asyncpg
    from pgdb import PostgresDocumentDB
    from urllib.parse import quote

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set.")

    # Percent-encode reserved chars in the password.
    url = database_url
    if "@" in url.split("://", 1)[-1]:
        head, _, tail = url.partition("://")
        creds, _, hostpart = tail.rpartition("@")
        if ":" in creds:
            u, _, p = creds.partition(":")
            url = f"{head}://{quote(u, safe='')}:{quote(p, safe='')}@{hostpart}"

    pool = await asyncpg.create_pool(url, min_size=1, max_size=3, command_timeout=30)
    db = PostgresDocumentDB(pool)

    # Get brands list for mapping interests
    brands = [b["name"] for b in await db.brands.find({}, {"_id": 0, "name": 1}).to_list(20)]
    print(f"Found brands: {brands}")

    # Upsert sales reps with allowed_brands
    rep_ids = []
    for name, email, pw, allowed in SALES_REPS:
        existing = await db.users.find_one({"email": email})
        if existing:
            await db.users.update_one(
                {"email": email},
                {"$set": {
                    "name": name, "role": "sales",
                    "allowed_brands": allowed,
                    "password_hash": hash_pw(pw),
                }},
            )
            rep_ids.append(existing["id"])
        else:
            uid = str(uuid.uuid4())
            await db.users.insert_one({
                "id": uid, "name": name, "email": email,
                "password_hash": hash_pw(pw),
                "role": "sales",
                "allowed_brands": allowed,
                "created_at": iso(NOW - timedelta(days=60)),
            })
            rep_ids.append(uid)
    # also include existing demo Rahul Sharma
    rahul = await db.users.find_one({"email": "sales@hitechaudio.in"})
    if rahul:
        await db.users.update_one({"id": rahul["id"]}, {"$set": {"allowed_brands": ["L-Acoustics", "DiGiCo"]}})
        rep_ids.append(rahul["id"])
    print(f"{len(rep_ids)} sales reps ready")

    # Clear demo leads (keep manual ones not from this script if any — we use a tag)
    await db.leads.delete_many({"demo_seed": True})
    await db.activities.delete_many({"demo_seed": True})
    await db.quotations.delete_many({"demo_seed": True})

    # Get products and brand-fronted choices
    products_by_brand = {}
    for b in brands:
        ps = await db.products.find({"brand": b}, {"_id": 0, "id": 1, "name": 1, "model": 1, "unit_price": 1}).to_list(200)
        products_by_brand[b] = [p for p in ps if p.get("unit_price")]  # only priced products

    # Generate leads spread over 14 days
    leads = []
    for i in range(45):
        days_ago = random.choices(range(0, 14), weights=[1, 2, 3, 3, 4, 4, 5, 4, 5, 6, 7, 6, 6, 5])[0]
        created = NOW - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        comp, city = random.choice(COMPANIES)
        stage = random.choices([s for s, _ in STAGE_WEIGHTS], weights=[w for _, w in STAGE_WEIGHTS])[0]
        source = random.choice(SOURCES)
        # choose interested_in: 70% chance from a real brand string so brand-interest bars populate
        if random.random() < 0.75 and brands:
            brand = random.choice(brands)
            interested = random.choice(INTERESTS.get(brand, INTERESTS["generic"]))
        else:
            interested = random.choice(INTERESTS["generic"])
        budget = random.choice([None, 250000, 500000, 1200000, 3500000, 8000000, 15000000])
        lid = str(uuid.uuid4())
        assigned = random.choice(rep_ids)
        leads.append({
            "id": lid,
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}@{comp.split()[0].lower()}.in",
            "phone": f"+91 9{random.randint(100000000, 999999999)}",
            "company": f"{comp} · {city}",
            "source": source,
            "interested_in": interested,
            "budget": budget,
            "notes": None,
            "stage": stage,
            "assigned_to": assigned,
            "created_by": rep_ids[0],
            "created_at": iso(created),
            "updated_at": iso(created),
            "demo_seed": True,
        })
    await db.leads.insert_many(leads)
    print(f"Inserted {len(leads)} demo leads")

    # Activities (notes + some follow-ups in next 7 days)
    acts = []
    for ld in leads:
        # 1-3 historic activities
        n_acts = random.randint(1, 3)
        base = datetime.fromisoformat(ld["created_at"])
        for j in range(n_acts):
            t = base + timedelta(hours=random.randint(2, 48) * (j + 1))
            if t > NOW:
                t = NOW - timedelta(hours=1)
            acts.append({
                "id": str(uuid.uuid4()),
                "lead_id": ld["id"],
                "user_id": ld["assigned_to"],
                "type": random.choice(["note", "call", "email", "whatsapp", "meeting"]),
                "content": random.choice([
                    "Sent initial product catalogue and spec sheet.",
                    "Discussed venue dimensions and SPL targets.",
                    "Awaiting confirmation on budget approval.",
                    "Customer requested demo at their facility.",
                    "Shared package quotation v1 via email.",
                    "Site visit scheduled for next week.",
                    "Asked about service/AMC options after install.",
                ]),
                "follow_up_at": None,
                "created_at": iso(t),
                "demo_seed": True,
            })
        # 30% chance of an upcoming follow-up in next 7 days
        if random.random() < 0.30 and ld["stage"] not in ("won", "lost"):
            future = NOW + timedelta(days=random.randint(1, 7), hours=random.randint(0, 8))
            acts.append({
                "id": str(uuid.uuid4()),
                "lead_id": ld["id"],
                "user_id": ld["assigned_to"],
                "type": random.choice(["call", "meeting", "follow_up"]),
                "content": random.choice([
                    "Follow up on quotation acceptance.",
                    "Site recce and final dimension confirmation.",
                    "Send revised commercials post negotiation.",
                    "Demo session at client venue.",
                    "Confirm GST + shipping terms before PO.",
                ]),
                "follow_up_at": iso(future),
                "created_at": iso(NOW - timedelta(hours=2)),
                "demo_seed": True,
            })
    await db.activities.insert_many(acts)
    print(f"Inserted {len(acts)} demo activities")

    # Quotations — for ~half of qualified+ leads
    qs = []
    counter = await db.quotations.count_documents({})
    for ld in leads:
        if ld["stage"] not in ("qualified", "quoted", "won", "lost"):
            continue
        if random.random() > 0.65:
            continue
        # pick 2-5 priced products
        candidates = [p for ps in products_by_brand.values() for p in ps if p.get("unit_price", 0) > 0]
        if not candidates:
            continue
        items = []
        for _ in range(random.randint(2, 5)):
            p = random.choice(candidates)
            qty = random.choice([1, 1, 2, 2, 4])
            items.append({
                "product": f"{p['name']}{' (' + p['model'] + ')' if p.get('model') else ''}",
                "brand": next((b for b, ps in products_by_brand.items() if any(x["id"] == p["id"] for x in ps)), ""),
                "qty": qty,
                "unit_price": p["unit_price"],
                "tax_pct": 18.0,
            })
        subtotal = sum(i["qty"] * i["unit_price"] for i in items)
        tax = sum(i["qty"] * i["unit_price"] * 0.18 for i in items)
        total = subtotal + tax
        counter += 1
        # status weighted by lead stage
        if ld["stage"] == "won":
            status = "accepted"
        elif ld["stage"] == "lost":
            status = "rejected"
        elif ld["stage"] == "quoted":
            status = random.choice(["sent", "sent", "draft"])
        else:
            status = "draft"
        created = datetime.fromisoformat(ld["created_at"]) + timedelta(days=random.randint(1, 5))
        if created > NOW:
            created = NOW - timedelta(hours=2)
        qs.append({
            "id": str(uuid.uuid4()),
            "quote_no": f"HAI-Q-{1000 + counter}",
            "lead_id": ld["id"],
            "items": items,
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(total, 2),
            "valid_until": iso(created + timedelta(days=15)),
            "terms": "Payment: 50% advance, 50% on delivery. Validity: 15 days.",
            "status": status,
            "created_by": ld["assigned_to"],
            "created_at": iso(created),
            "demo_seed": True,
        })
    if qs:
        await db.quotations.insert_many(qs)
    print(f"Inserted {len(qs)} demo quotations")
    print("Done.")

    await pool.close()


asyncio.run(main())
