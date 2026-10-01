"""Idempotent catalogue + demo-team seeding.

Deliberate choices, so nobody mistakes this for data that came from the business:

* **Brand names and product model names are real** manufacturers and real model
  lines in the pro-audio / AV space. That is public catalogue information.
* **Prices are intentionally left unset** (``unit_price: None``,
  ``price_status: "pending"``). We do not know this dealer's actual price list, and a
  guessed figure that reaches a customer quotation is worse than a blank one.
* **Employees are fictional demo accounts**, tagged ``is_demo: True`` with a
  ``demo-<name>@hitech.example`` address. They exist so permissions, round-robin lead
  assignment and the team dashboard have more than one person to work with. They are
  NOT staff records and must be replaced before go-live (see ``PURGE_DEMO_EMPLOYEES``
  in the cleanup notes).

Every statement is an upsert keyed on a natural key, so re-running is a no-op and a
manually corrected price is never overwritten.
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone


def _sid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# m011 -- real brands + real product model names, prices pending
# ---------------------------------------------------------------------------

CATALOG_BRANDS = [
    # (name, country, website, brand_category, description, tags)
    ("L-Acoustics", "France", "https://www.l-acoustics.com", "Professional Audio",
     "Touring and installed line array, point source and touring systems.", ["line array", "loudspeaker", "touring"]),
    ("d&b audiotechnik", "Germany", "https://www.dbaudio.com", "Professional Audio",
     "Line array and point source loudspeaker systems.", ["line array", "loudspeaker"]),
    ("RCF", "Italy", "https://www.rcf.it", "Professional Audio",
     "Loudspeakers, mixers and installed sound systems.", ["loudspeaker", "mixer"]),
    ("DiGiCo", "United Kingdom", "https://www.digico.global", "Professional Audio",
     "Digital mixing consoles for live, broadcast and theatre.", ["digital console", "live"]),
    ("Soundcraft", "United Kingdom", "https://www.soundcraft.com", "Professional Audio",
     "Digital and analogue mixing consoles and stageboxes.", ["console", "stagebox"]),
    ("Behringer", "Germany", "https://www.behringer.com", "Professional Audio",
     "Mixers, amplifiers, in-ear monitoring and signal processing.", ["mixer", "amplifier", "iem"]),
    ("Shure", "United States", "https://www.shure.com", "Professional Audio",
     "Microphones, wireless systems and conferencing audio.", ["microphone", "wireless", "iem"]),
    ("Sennheiser", "Germany", "https://www.sennheiser.com", "Professional Audio",
     "Microphones, wireless systems and monitoring.", ["microphone", "wireless", "iem"]),
    ("Electro-Voice", "United States", "https://www.electrovoice.com", "Professional Audio",
     "Microphones, loudspeakers and amplifiers.", ["microphone", "loudspeaker"]),
    ("JBL Professional", "United States", "https://www.jblpro.com", "Professional Audio",
     "Loudspeakers, amplifiers and DSP.", ["loudspeaker", "amplifier"]),
    ("QSC", "United States", "https://www.qsc.com", "Professional Audio",
     "Loudspeakers, amplifiers and digital mixing consoles.", ["loudspeaker", "amplifier", "console"]),
    ("Mackie", "United States", "https://www.mackie.com", "Professional Audio",
     "Mixers, loudspeakers and in-ear monitoring.", ["mixer", "loudspeaker"]),
    ("Yamaha", "Japan", "https://www.yamaha.com", "Professional Audio",
     "Digital mixing consoles, amplifiers and installed audio.", ["console", "amplifier"]),
    ("Allen & Heath", "United Kingdom", "https://www.allen-heath.com", "Professional Audio",
     "Digital and analogue mixing consoles.", ["console"]),
    ("Calrec", "United Kingdom", "https://www.calrec.com", "Professional Audio",
     "Broadcast audio consoles and routing.", ["console", "broadcast"]),
    ("LAX", "United Kingdom", "https://www.laxaudio.com", "Professional Audio",
     "Digital matrix mixing and DSP.", ["dsp", "matrix"]),
    ("BSS Audio", "United Kingdom", "https://www.bssaudio.com", "Professional Audio",
     "Speaker processing, amplifiers and sound management.", ["dsp", "amplifier"]),
    ("Crown by Harman", "United States", "https://www.harman.com", "Professional Audio",
     "Power amplifiers for installed and portable sound.", ["amplifier"]),
    ("dbx", "United States", "https://www.dbx.com", "Professional Audio",
     "Signal processing, crossovers and speaker management.", ["dsp", "crossover"]),
    ("NEXO", "France", "https://www.nexo.com", "Professional Audio",
     "Line array, point source and column loudspeakers.", ["line array", "loudspeaker"]),
    ("DAS Audio", "Spain", "https://www.dasaudio.com", "Professional Audio",
     "Touring and installed loudspeakers.", ["loudspeaker", "touring"]),
    ("JBL EON", "United States", "https://www.jblpro.com", "Professional Audio",
     "Compact powered loudspeakers.", ["loudspeaker", "powered"]),
    ("Martin Audio", "United Kingdom", "https://www.martin-audio.com", "Professional Audio",
     "Touring, fill and distributed loudspeakers.", ["loudspeaker", "touring"]),
    ("Turbosound", "United Kingdom", "https://www.turbosound.com", "Professional Audio",
     "Touring loudspeakers and amplifiers.", ["loudspeaker", "touring"]),

    # Video / AV / integration
    ("Samsung", "South Korea", "https://www.samsung.com", "Video & AV",
     "Commercial displays, video walls and signage.", ["display", "video wall"]),
    ("LG", "South Korea", "https://www.lg.com", "Video & AV",
     "Commercial displays and LED video walls.", ["display", "video wall"]),
    ("Sony", "Japan", "https://www.sony.com", "Video & AV",
     "Projectors, displays, cameras and broadcast equipment.", ["projector", "display", "broadcast"]),
    ("Panasonic", "Japan", "https://www.panasonic.com", "Video & AV",
     "Projectors, displays and professional video.", ["projector", "display"]),
    ("Epson", "Japan", "https://www.epson.com", "Video & AV",
     "Projectors and interactive displays.", ["projector", "display"]),
    ("Canon", "Japan", "https://www.canon.com", "Video & AV",
     "Projectors, cameras and broadcast lenses.", ["projector", "camera"]),
    ("Christie", "Canada", "https://www.christiedigital.com", "Video & AV",
     "Digital cinema projection and video walls.", ["projector", "cinema"]),
    ("Barco", "Belgium", "https://www.barco.com", "Video & AV",
     "Projectors, LED walls and collaboration displays.", ["projector", "led"]),
    ("Crestron", "United States", "https://www.crestron.com", "Control & Automation",
     "Room control, automation and AV distribution.", ["control", "automation"]),
    ("Extron", "United States", "https://www.extron.com", "Control & Automation",
     "Signal distribution, control and switching.", ["control", "distribution"]),
    ("Kramer", "Israel", "https://www.kramerav.com", "Control & Automation",
     "Signal distribution, switching and control.", ["distribution", "switcher"]),
    ("Bose Professional", "United States", "https://pro.bose.com", "Professional Audio",
     "Loudspeakers, amplifiers and conferencing audio.", ["loudspeaker", "conference"]),
    ("Shure MX", "United States", "https://www.shure.com", "Conference",
     "Digital conferencing microphone systems.", ["conference", "microphone"]),
    ("Sennheiser EW", "Germany", "https://www.sennheiser.com", "Professional Audio",
     "Wireless microphone and in-ear monitoring systems.", ["wireless", "iem"]),
]

# (brand, model, name, category, sub_category)
CATALOG_PRODUCTS = [
    ("L-Acoustics", "K2", "K2 Line Array Element", "Loudspeakers", "Line Array"),
    ("L-Acoustics", "K1", "K1 Line Array Element", "Loudspeakers", "Line Array"),
    ("L-Acoustics", "K2 Solo", "K2 Solo Line Array", "Loudspeakers", "Line Array"),
    ("L-Acoustics", "XTG12", "XTG12 Loudspeaker", "Loudspeakers", "Point Source"),
    ("L-Acoustics", "DP12", "DP12 Delay Loudspeaker", "Loudspeakers", "Point Source"),
    ("L-Acoustics", "SB18", "SB18 Subwoofer", "Loudspeakers", "Subwoofer"),
    ("d&b audiotechnik", "KSL", "KSL Line Array", "Loudspeakers", "Line Array"),
    ("d&b audiotechnik", "XSL", "XSL Line Array", "Loudspeakers", "Line Array"),
    ("d&b audiotechnik", "GSL", "GSL Subwoofer", "Loudspeakers", "Subwoofer"),
    ("d&b audiotechnik", "DP12", "DP12 Delay Loudspeaker", "Loudspeakers", "Point Source"),
    ("d&b audiotechnik", "D40", "D40 Loudspeaker", "Loudspeakers", "Point Source"),
    ("RCF", "MDX", "MDX Loudspeaker Series", "Loudspeakers", "Point Source"),
    ("RCF", "ART 9", "ART 9 Loudspeaker", "Loudspeakers", "Point Source"),
    ("RCF", "SUB 8", "SUB 8 Subwoofer", "Loudspeakers", "Subwoofer"),
    ("RCF", "C-Mix 6", "C-Mix 6 Digital Console", "Consoles", "Digital Console"),
    ("DiGiCo", "SD7", "SD7 Digital Console", "Consoles", "Digital Console"),
    ("DiGiCo", "SD12", "SD12 Digital Console", "Consoles", "Digital Console"),
    ("DiGiCo", "Quantum 338", "Quantum 338 Digital Console", "Consoles", "Digital Console"),
    ("Soundcraft", "ViVX 240", "ViVX 240 Console", "Consoles", "Digital Console"),
    ("Soundcraft", "GB4", "GB4 Console", "Consoles", "Analogue Console"),
    ("Behringer", "X32", "X32 Digital Console", "Consoles", "Digital Console"),
    ("Behringer", "X18", "X18 Compact Console", "Consoles", "Digital Console"),
    ("Behringer", "EuX", "EuX Wireless In-Ear Monitor", "Monitoring", "Wireless IEM"),
    ("Shure", "SM58", "SM58 Vocal Microphone", "Microphones", "Dynamic"),
    ("Shure", "SM57", "SM57 Instrument Microphone", "Microphones", "Dynamic"),
    ("Shure", "Beta 87A", "Beta 87A Vocal Microphone", "Microphones", "Dynamic"),
    ("Shure", "SLX24", "SLX24 Wireless System", "Wireless", "UHF Wireless"),
    ("Shure", "Axient Digital", "Axient Digital Wireless System", "Wireless", "UHF Wireless"),
    ("Shure", "MV88+", "MV88+ Video Conference Microphone", "Conference", "Conference"),
    ("Sennheiser", "e965", "e965 Handheld Transmitter", "Wireless", "UHF Wireless"),
    ("Sennheiser", "EW 112P G4", "EW 112P G4 Wireless Lav", "Wireless", "UHF Wireless"),
    ("Sennheiser", "HD 25", "HD 25 Headphones", "Monitoring", "Headphones"),
    ("Electro-Voice", "RE20", "RE20 Dynamic Microphone", "Microphones", "Dynamic"),
    ("Electro-Voice", "EVP-2272", "EVP-2272 Loudspeaker", "Loudspeakers", "Point Source"),
    ("JBL Professional", "PRX400", "PRX400 Powered Amplifier", "Amplifiers", "Powered Amplifier"),
    ("JBL Professional", "EON One Compact", "EON One Compact", "Loudspeakers", "Powered"),
    ("QSC", "CPX", "CPX Series Loudspeaker", "Loudspeakers", "Point Source"),
    ("QSC", "Q-SYS Core 110", "Q-SYS Core 110 Processor", "Control & Automation", "DSP"),
    ("Mackie", "DLZ", "DLZ Digital Console", "Consoles", "Digital Console"),
    ("Yamaha", "DM7", "DM7 Digital Console", "Consoles", "Digital Console"),
    ("Yamaha", "TF-Q160", "TF-Q160 Digital Console", "Consoles", "Digital Console"),
    ("Yamaha", "D-Cruiser", "D-Cruiser Compact Console", "Consoles", "Digital Console"),
    ("Allen & Heath", "dLive S73", "dLive S73 Digital Console", "Consoles", "Digital Console"),
    ("Allen & Heath", "CQ-18T", "CQ-18T Compact Console", "Consoles", "Digital Console"),
    ("LAX", "208i", "208i Digital Matrix Processor", "Control & Automation", "DSP"),
    ("BSS Audio", "SoundWeb", "SoundWeb Speaker Processor", "Control & Automation", "DSP"),
    ("BSS Audio", "D-80", "D-80 Amplifier", "Amplifiers", "Amplifier"),
    ("Crown by Harman", "XLi 2500", "XLi 2500 Amplifier", "Amplifiers", "Amplifier"),
    ("dbx", "DriveRack PA2", "DriveRack PA2 Processor", "Control & Automation", "DSP"),
    ("NEXO", "NEXO GEO", "NEXO GEO Line Array", "Loudspeakers", "Line Array"),
    ("NEXO", "NEXO STM", "NEXO STM Module", "Loudspeakers", "Line Array"),
    ("DAS Audio", "Event 8", "Event 8 Line Array", "Loudspeakers", "Line Array"),
    ("Martin Audio", "CDD", "CDD Loudspeaker Series", "Loudspeakers", "Line Array"),
    ("Turbosound", "NUQ", "NUQ Loudspeaker Series", "Loudspeakers", "Line Array"),
    ("Bose Professional", "Panaray MA12", "Panaray MA12 Array", "Loudspeakers", "Column Array"),
    ("Samsung", "QM55R", "QM55R 55in Commercial Display", "Displays", "Commercial Display"),
    ("Samsung", "Video Wall 46in", "46in Video Wall Panel", "Displays", "Video Wall"),
    ("LG", "55UH5F", "55UH5F 55in Commercial Display", "Displays", "Commercial Display"),
    ("Sony", "VPL-FH75", "VPL-FH75 Projector", "Projection", "Projector"),
    ("Sony", "PXW-Z45", "PXW-Z45 Broadcast Camera", "Video", "Broadcast Camera"),
    ("Panasonic", "PT-VMZ71", "PT-VMZ71 Projector", "Projection", "Projector"),
    ("Epson", "EB-L530U", "EB-L530U Projector", "Projection", "Laser Projector"),
    ("Canon", "XE4", "XE4 Projector", "Projection", "Laser Projector"),
    ("Barco", "PKIX", "PKIX Cinema Projector", "Projection", "Cinema Projector"),
    ("Crestron", "CPH-100", "CPH-100 Processor", "Control & Automation", "Control Processor"),
    ("Extron", "DTP", "DTP Series Distribution", "Control & Automation", "Distribution"),
    ("Kramer", "VP-728", "VP-728 Presentation Switcher", "Control & Automation", "Switcher"),
]

# ---------------------------------------------------------------------------
# m012 -- fictional demo team
# ---------------------------------------------------------------------------

DEMO_EMPLOYEES = [
    # (name, email local-part, role, department, designation)
    ("Aarav Deshmukh", "aarav.deshmukh", "sales", "Sales", "Senior Sales Executive"),
    ("Ishita Ranganathan", "ishita.ranganathan", "sales", "Sales", "Sales Executive"),
    ("Farhan Qureshi", "farhan.qureshi", "sales", "Sales", "Sales Executive"),
    ("Neha Pillai", "neha.pillai", "sales", "Sales", "Inside Sales Executive"),
    ("Vikram Sethi", "vikram.sethi", "sales", "Sales", "Key Account Manager"),
    ("Ritu Malhotra", "ritu.malhotra", "service", "Service", "Service Manager"),
    ("Karthik Subramanian", "karthik.subramanian", "service", "Service", "Field Service Engineer"),
    ("Sanjana Iyer", "sanjana.iyer", "service", "Service", "Field Service Engineer"),
    ("Pranav Joshi", "pranav.joshi", "accounts", "Accounts", "Accounts Executive"),
    ("Divya Menon", "divya.menon", "accounts", "Accounts", "Accounts Manager"),
    ("Mohammed Irfan", "mohammed.irfan", "purchase", "Purchase", "Purchase Manager"),
    ("Sneha Kulkarni", "sneha.kulkarni", "purchase", "Purchase", "Purchase Executive"),
    ("Aditya Rao", "aditya.rao", "project", "Projects", "Project Manager"),
    ("Meera Krishnan", "meera.krishnan", "project", "Projects", "Project Coordinator"),
    ("Harsh Vardhan", "harsh.vardhan", "design", "Design", "System Design Engineer"),
    ("Pooja Nair", "pooja.nair", "design", "Design", "CAD Designer"),
]

DEMO_PASSWORD = os.environ.get("SALES_DEMO_PASSWORD", "Sales@123")
DEMO_EMAIL_DOMAIN = "hitech.example"


async def m011_seed_catalog(db):
    """Seed real brands and real product model names. Prices stay unset."""
    now = _now()
    brands_added, products_added = 0, 0

    for name, country, website, category, description, tags in CATALOG_BRANDS:
        # Keyed on name so a re-run updates in place and never duplicates.
        existing = await db.brands.find_one({"name": name}, {"_id": 0, "id": 1})
        if existing:
            await db.brands.update_one(
                {"name": name},
                {"$set": {
                    "country": country, "official_website": website,
                    "brand_category": category, "description": description,
                    "tags": tags, "product_categories": [], "updated_at": now,
                }},
            )
            continue
        await db.brands.insert_one({
            "id": _sid(), "name": name, "country": country,
            "description": description, "official_website": website,
            "brand_category": category, "product_categories": [], "tags": tags,
            "logo_url": None, "featured": False, "locked": False,
            "is_seed": True, "created_at": now,
        })
        brands_added += 1

    for brand, model, name, category, sub_category in CATALOG_PRODUCTS:
        # Natural key: brand + model + name.
        key = {"brand": brand, "model": model, "name": name}
        if await db.products.find_one(key, {"_id": 0, "id": 1}):
            # Never overwrite a price a human has since entered.
            await db.products.update_one(key, {"$set": {"category": category,
                                                        "sub_category": sub_category}})
            continue
        await db.products.insert_one({
            "id": _sid(), "brand": brand, "name": name, "model": model,
            "sku": None, "category": category, "sub_category": sub_category,
            # Price is deliberately unknown. price_status makes that explicit so the
            # catalogue can show "pending" rather than a misleading zero.
            "unit_price": None, "msrp": None,
            "dealer_price": None, "distributor_price": None,
            "price_status": "pending", "price_required": True,
            "description": None, "is_seed": True, "created_at": now,
        })
        products_added += 1

    await db.brands.create_index("name", unique=True, background=True)
    await db.products.create_index([("brand", 1), ("model", 1)], background=True)
    await db.products.create_index("name", background=True)
    return f"{brands_added} brands, {products_added} products added ({len(CATALOG_BRANDS)}/{len(CATALOG_PRODUCTS)} total)"


async def m012_seed_demo_employees(db):
    """Seed clearly-fictitious demo accounts so permissions and lead routing are exercisable."""
    now = _now()
    added = 0
    for name, local, role, department, designation in DEMO_EMPLOYEES:
        email = f"demo-{local}@{DEMO_EMAIL_DOMAIN}"
        if await db.users.find_one({"email": email}, {"_id": 0, "id": 1}):
            continue
        await db.users.insert_one({
            "id": _sid(), "name": name, "email": email, "role": role,
            "department": department, "designation": designation,
            "phone": None, "allowed_brands": [], "active": True,
            # Loud, machine-checkable markers so these are never mistaken for staff and
            # can be purged with a single query before go-live.
            "is_demo": True,
            "demo_note": "Fictional demo account seeded by m012. Replace or purge before go-live.",
            "password_hash": _demo_hash(),
            "created_at": now,
        })
        added += 1

    # Unique only when present. m013 imports staff who have no email address, and a
    # plain unique index would reject the second missing-email row as a duplicate.
    await db.users.create_index(
        "email",
        unique=True,
        background=True,
        partialFilterExpression={"email": {"$type": "string"}},
    )
    await db.users.create_index("is_demo", background=True)
    return f"{added} demo employees added ({len(DEMO_EMPLOYEES)} total)"


def _demo_hash() -> str:
    """bcrypt hash of the demo password, matching the app's storage format."""
    try:
        import bcrypt
        return bcrypt.hashpw(DEMO_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        # bcrypt unavailable at migration time: leave it unset rather than storing a
        # bogus value. These accounts are not usable until a real password is set.
        return ""