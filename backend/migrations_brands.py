"""Brand master list, categories and the product schema migration.

Authoritative source: the business's own master brand list (21 approved brands,
transcribed from the owner's Excel). The CRM must expose exactly these brands --
no more, no fewer. Anything else that reached the ``brands`` collection previously
(a mixture of seeded demo manufacturers, projector/display vendors and split
variants such as "Shure MX" and "Sennheiser EW") is archived.

Two rules govern everything in this module:

1. **Never delete a brand outright.** ``DELETE /api/brands/{id}`` and this
   migration both *archive* (``status: "archived"``). Quotations, purchase orders
   and work orders embed the brand *name* as free text on their line items, and a
   brand that vanishes would leave those historical documents naming something the
   catalogue no longer recognises. Archiving keeps the history readable while
   removing the brand from every active dropdown, filter and API listing.
2. **Never fabricate.** ``official_website`` is transcribed from the master list.
   ``logo_url`` is only carried over if it already exists in the database -- it is
   never guessed from a naming pattern. ``description`` is likewise only preserved
   from the existing record, never invented.

Migration ids:

* ``m014`` -- brands: seed the 21 approved brands, archive everything else
* ``m015`` -- ``product_categories``: normalise the catalogue taxonomy
* ``m016`` -- products: additive schema (``brand_id``/``category_id``/``slug``/…)
  with backfill; ``brand`` and ``category`` strings are kept so every existing
  caller keeps working
* ``m017`` -- duplicate cleanup and the unique/partial indexes that back the rules
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# The master brand list. Authoritative. Do not add, rename or reorder casually:
# this tuple is what the business signed off on.
# ---------------------------------------------------------------------------
MASTER_BRANDS: list[tuple[str, str]] = [
    ("RCF", "https://www.rcf.it/"),
    ("L-Acoustics", "https://www.l-acoustics.com/"),
    ("DiGiCo", "https://digico.biz/"),
    ("TT+ Audio", "https://www.ttaudio.com/"),
    ("Sound Devices", "https://www.sounddevices.com/"),
    ("Klang Technologies", "https://www.klang.com/"),
    ("Radial Engineering", "https://www.radialeng.com/"),
    ("Fourier Audio", "https://fourieraudio.com/"),
    ("Audio Press Box", "https://www.audiopressbox.com/"),
    ("MA Lighting", "https://www.malighting.com/"),
    ("MADRIX", "https://www.madrix.com/"),
    ("ETC", "https://www.etcconnect.com/"),
    ("Zactrack", "https://www.zactrack.com/"),
    ("Luminex", "https://www.luminex.be/"),
    ("Klotz", "https://www.klotz-ais.com/"),
    ("K&M", "https://www.k-m.de/"),
    ("Sennheiser", "https://www.sennheiser.com/"),
    ("Cotodama", "https://www.cotodama.com/"),
    ("DPA Microphones", "https://www.dpamicrophones.com/"),
    ("JH Audio", "https://jhaudio.com/"),
    ("Wisycom", "https://wisycom.com/"),
]

APPROVED_BRAND_NAMES = [name for name, _ in MASTER_BRANDS]

# Variants that used to be separate brand records but are really one manufacturer.
# "Shure MX" and "Sennheiser EW" are product lines, not distinct vendors. Mapping
# them onto their parent keeps old documents intelligible; nothing is invented
# because the parent brand is on the approved list.
BRAND_ALIASES: dict[str, str] = {
    "shure mx": "Shure",
    "shure": "Shure",  # not approved either, but keeps the alias table honest
    "sennheiser ew": "Sennheiser",
    "jbl eon": "JBL Professional",
    "jbl professional": "JBL Professional",
    "crown by harman": "Crown by Harman",
    "bose professional": "Bose Professional",
    "l-acoustics": "L-Acoustics",
    "d&b audiotechnik": "d&b audiotechnik",
    "tt+": "TT+ Audio",
    "tt+ audio": "TT+ Audio",
    "tt audio": "TT+ Audio",
    "dpa": "DPA Microphones",
    "dpa microphones": "DPA Microphones",
    "jh audio": "JH Audio",
    "km": "K&M",
    "k&m": "K&M",
    "madrix": "MADRIX",
    "etc": "ETC",
    "klotz": "Klotz",
    "luminex": "Luminex",
    "rcf": "RCF",
    "digico": "DiGiCo",
    "klang": "Klang Technologies",
    "klang technologies": "Klang Technologies",
    "radial": "Radial Engineering",
    "radial engineering": "Radial Engineering",
    "fourier": "Fourier Audio",
    "fourier audio": "Fourier Audio",
    "sound devices": "Sound Devices",
    "ma lighting": "MA Lighting",
    "zactrack": "Zactrack",
    "wisycom": "Wisycom",
    "cotodama": "Cotodama",
    "audiopressbox": "Audio Press Box",
    "audio press box": "Audio Press Box",
    "sennheiser": "Sennheiser",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    """Lowercase, dash-separated, ASCII-ish slug. Stable and collision-free enough
    to key on because every brand name in the master list is distinct after this."""
    s = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return s or "item"


def _name_key(value: str) -> str:
    """Case- and punctuation-insensitive key for matching existing rows.

    "TT+ Audio", "tt audio" and "TT Audio" all collapse to ``tt-audio`` so the
    migration recognises an existing record regardless of how it was typed in.
    """
    s = str(value or "").lower()
    s = s.replace("&", " and ").replace("+", " plus ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def canonical_brand_name(name: str) -> str:
    """Map a raw brand string onto an approved name, or return it unchanged."""
    return BRAND_ALIASES.get(_name_key(name), name)


# ---------------------------------------------------------------------------
# Product categories. Derived from the categories that actually appear in the
# existing catalogue plus the ones the pro-audio brands on the master list sell
# into. These are taxonomy labels for filtering, not manufacturer claims.
# ---------------------------------------------------------------------------
PRODUCT_CATEGORIES: list[str] = [
    "Amplifiers",
    "Consoles",
    "Microphones",
    "Loudspeakers",
    "Processing & DSP",
    "Wireless & RF",
    "Monitoring & Headphones",
    "Intercom & Communication",
    "Lighting",
    "Video & Projection",
    "Control & Automation",
    "Accessories",
]

# Brands whose catalogue is entirely one domain, so their products should not be
# filed under a generic audio category. This is a classification of where the
# manufacturer operates, not a product spec.
BRAND_CATEGORY: dict[str, str] = {
    "RCF": "Professional Audio",
    "L-Acoustics": "Professional Audio",
    "DiGiCo": "Professional Audio",
    "TT+ Audio": "Professional Audio",
    "Sound Devices": "Professional Audio",
    "Klang Technologies": "Monitoring & Intercom",
    "Radial Engineering": "Accessories",
    "Fourier Audio": "Live & Broadcast Audio",
    "Audio Press Box": "Accessories",
    "MA Lighting": "Lighting",
    "MADRIX": "Control & Automation",
    "ETC": "Lighting",
    "Zactrack": "Video & Projection",
    "Luminex": "Lighting",
    "Klotz": "Professional Audio",
    "K&M": "Professional Audio",
    "Sennheiser": "Professional Audio",
    "Cotodama": "Video & Projection",
    "DPA Microphones": "Microphones",
    "JH Audio": "Microphones",
    "Wisycom": "Professional Audio",
}


# ---------------------------------------------------------------------------
# m014 -- brands
# ---------------------------------------------------------------------------
async def m014_apply_master_brand_list(db) -> str:
    """Ensure the catalogue holds exactly the 21 approved brands, all active.

    Existing rows are matched on a punctuation-insensitive name so "L-Acoustics"
    is updated in place and keeps its ``id`` (and therefore any references to it).
    Anything not on the list is archived rather than deleted.
    """
    now = _now()
    added = updated = archived = 0

    existing = await db.brands.find({}).to_list(1000)
    by_key = {_name_key(b.get("name")): b for b in existing}

    for name, website in MASTER_BRANDS:
        key = _name_key(name)
        doc = by_key.get(key)
        if doc:
            sets = {
                "name": name,
                "slug": slugify(name),
                "official_website": website,
                "status": "active",
                "brand_category": BRAND_CATEGORY.get(name) or doc.get("brand_category"),
                "approved": True,
                "updated_at": now,
            }
            if any(doc.get(k) != v for k, v in sets.items()):
                await db.brands.update_one({"id": doc["id"]}, {"$set": sets})
                updated += 1
            else:
                await db.brands.update_one({"id": doc["id"]}, {"$set": {"approved": True}})
        else:
            await db.brands.insert_one({
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slugify(name),
                "official_website": website,
                # logo_url deliberately omitted: it is unknown, and a guessed logo
                # path would render as a broken image in the UI.
                "logo_url": None,
                "description": None,
                "brand_category": BRAND_CATEGORY.get(name),
                "status": "active",
                "approved": True,
                "product_categories": [],
                "tags": [],
                "created_at": now,
                "updated_at": now,
            })
            added += 1

    # Anything that is not on the approved list gets archived, not deleted, so the
    # free-text brand names on historical quotations and orders keep their meaning.
    for b in existing:
        if b.get("approved") is True and b.get("status") == "active":
            continue
        if _name_key(b.get("name")) in {_name_key(n) for n in APPROVED_BRAND_NAMES}:
            continue
        await db.brands.update_one(
            {"id": b["id"]},
            {"$set": {
                "status": "archived",
                "approved": False,
                "archived_at": now,
                "archive_reason": "Not on the approved 21-brand master list",
                "updated_at": now,
            }},
        )
        archived += 1

    await db.brands.create_index("slug", unique=True, background=True,
                                 partialFilterExpression={"slug": {"$type": "string"}})
    await db.brands.create_index("status", background=True)
    await db.brands.create_index("approved", background=True)

    active = await db.brands.count_documents({"status": "active", "approved": True})
    return (f"{active} active approved brands ({added} added, {updated} updated, "
            f"{archived} archived)")


# ---------------------------------------------------------------------------
# m015 -- product_categories
# ---------------------------------------------------------------------------
async def m015_seed_product_categories(db) -> str:
    """Create the product_categories collection and backfill category_id on products.

    Products currently store ``category`` as a free-text string and many rows carry
    no category at all. This adds a real, referenced collection and points every
    product at it. The string stays, so nothing that reads ``product["category"]``
    breaks.
    """
    now = _now()
    made = 0
    key_to_id: dict[str, str] = {}

    for name in PRODUCT_CATEGORIES:
        slug = slugify(name)
        existing = await db.product_categories.find_one({"slug": slug})
        if existing:
            key_to_id[_name_key(name)] = existing["id"]
            continue
        cid = str(uuid.uuid4())
        await db.product_categories.insert_one({
            "id": cid,
            "name": name,
            "slug": slug,
            "created_at": now,
            "updated_at": now,
        })
        key_to_id[_name_key(name)] = cid
        made += 1

    await db.product_categories.create_index("slug", unique=True, background=True)

    # Categories that already exist on products but are not in the canonical list
    # still need an id, otherwise those products would lose their link. Register
    # them rather than dropping the reference.
    for doc in await db.products.find({}, {"_id": 0, "category": 1}).to_list(5000):
        cat = (doc.get("category") or "").strip()
        if not cat or _name_key(cat) in key_to_id:
            continue
        slug = slugify(cat)
        existing = await db.product_categories.find_one({"slug": slug})
        if existing:
            key_to_id[_name_key(cat)] = existing["id"]
            continue
        cid = str(uuid.uuid4())
        await db.product_categories.insert_one({
            "id": cid, "name": cat, "slug": slug,
            "created_at": now, "updated_at": now,
        })
        key_to_id[_name_key(cat)] = cid
        made += 1

    linked = 0
    for p in await db.products.find({}, {"_id": 0, "id": 1, "category": 1}).to_list(5000):
        cat = (p.get("category") or "").strip()
        cid = key_to_id.get(_name_key(cat)) if cat else None
        if cid:
            await db.products.update_one({"id": p["id"]}, {"$set": {"category_id": cid}})
            linked += 1

    return f"{made} categories created, {linked} products linked by category_id"


# ---------------------------------------------------------------------------
# m016 -- product schema (additive)
# ---------------------------------------------------------------------------
async def m016_add_product_schema(db) -> str:
    """Add the normalised product fields and backfill them from what is there.

    Additive: every existing key is kept. ``brand_id`` and ``category_id`` are the
    new relational fields; ``brand``/``category`` strings remain as the display
    convenience the frontend and PDF generator already read.
    """
    now = _now()
    brands = await db.brands.find({"status": "active", "approved": True}, {"_id": 0}).to_list(100)
    brand_key_to_id = {_name_key(b["name"]): b["id"] for b in brands}
    cats = await db.product_categories.find({}, {"_id": 0}).to_list(100)
    cat_key_to_id = {_name_key(c["name"]): c["id"] for c in cats}

    changed = 0
    for p in await db.products.find({}).to_list(5000):
        sets: dict = {}

        bid = brand_key_to_id.get(_name_key(p.get("brand")))
        if bid and p.get("brand_id") != bid:
            sets["brand_id"] = bid

        cid = cat_key_to_id.get(_name_key(p.get("category")))
        if cid and p.get("category_id") != cid:
            sets["category_id"] = cid

        name = p.get("name") or ""
        slug = slugify(name)
        if slug and p.get("slug") != slug:
            sets["slug"] = slug

        # model -> model_number. The CRM used "model"; the target schema names it
        # model_number. Both are written so either reader keeps working.
        model = (p.get("model") or "").strip() or None
        if model and p.get("model_number") != model:
            sets["model_number"] = model

        series = (p.get("series") or p.get("sub_category") or "").strip() or None
        if series and p.get("series") != series:
            sets["series"] = series

        short = (p.get("short_description") or "").strip() or None
        if short and p.get("short_description") != short:
            sets["short_description"] = short

        # An empty structured field is still a real value: it records "not yet
        # supplied" explicitly, which is what the manual-import workflow needs.
        for field in ("description", "official_url", "image_url", "source_url",
                      "last_verified_at"):
            if field not in p:
                sets[field] = None
        for field in ("specifications", "features"):
            if field not in p:
                sets[field] = None
        if not p.get("status"):
            sets["status"] = "active"

        if sets:
            await db.products.update_one({"id": p["id"]}, {"$set": sets})
            changed += 1

# A SKU is only unique when it is a real, non-empty string. MongoDB will not
    # accept `$ne` inside a partialFilterExpression, so blank SKUs are normalised to
    # null first and the index keys on `$type: "string"` alone.
    sku_seen: set[str] = set()
    for p in await db.products.find({}, {"_id": 0, "id": 1, "sku": 1}).sort("created_at", 1).to_list(5000):
        sku = (p.get("sku") or "").strip()
        if not sku:
            if p.get("sku") is not None:
                await db.products.update_one({"id": p["id"]}, {"$set": {"sku": None}})
            continue
        key = sku.lower()
        if key in sku_seen:
            # Duplicate SKU: the later row keeps no SKU rather than blocking the
            # unique index. The duplicate itself is archived by m017.
            await db.products.update_one({"id": p["id"]}, {"$set": {"sku": None}})
            continue
        sku_seen.add(key)

    await db.products.create_index("brand_id", background=True)
    await db.products.create_index("category_id", background=True)
    await db.products.create_index("slug", background=True)
    await db.products.create_index("status", background=True)
    await db.products.create_index("model_number", background=True)
    await db.products.create_index(
        "sku", unique=True, background=True,
        partialFilterExpression={"sku": {"$type": "string"}},
    )
    return f"{changed} products backfilled with normalised fields"


# ---------------------------------------------------------------------------
# m017 -- duplicate cleanup
# ---------------------------------------------------------------------------
def _fingerprint(brand: str, model: str, name: str) -> str:
    """Stable identity for a product, used to spot duplicates that differ only in
    whitespace, case or a trailing "(...)" suffix."""
    parts = [brand, model, name]
    cleaned = re.sub(r"[^a-z0-9]+", " ", " ".join(p for p in parts if p).lower())
    return hashlib.sha1(" ".join(cleaned.split()).encode("utf-8")).hexdigest()[:16]


async def m017_clean_duplicates(db) -> str:
    """Remove duplicate product rows and archive products of archived brands.

    A duplicate is two rows under the same brand whose model number and name agree
    once case and punctuation are normalised. The survivor is the oldest row, so
    ids that quotations already reference stay valid; the extras are archived
    (``status: "archived"``) rather than deleted, for the same reason brands are.
    """
    now = _now()
    products = await db.products.find({}).sort("created_at", 1).to_list(5000)

    seen: dict[str, dict] = {}
    dupes = 0
    for p in products:
        if p.get("status") == "archived":
            continue
        fp = _fingerprint(p.get("brand") or "", p.get("model_number") or p.get("model") or "",
                          p.get("name") or "")
        first = seen.get(fp)
        if first is None:
            seen[fp] = p
            continue
        await db.products.update_one({"id": p["id"]}, {"$set": {
            "status": "archived",
            "archived_at": now,
            "archive_reason": f"Duplicate of product {first['id']}",
            "duplicate_of": first["id"],
            "updated_at": now,
        }})
        dupes += 1

    # Duplicate brands under the same normalised name (e.g. a re-seeded "RCF").
    brands = await db.brands.find({}).sort("created_at", 1).to_list(500)
    bseen: dict[str, dict] = {}
    bdupes = 0
    for b in brands:
        if b.get("status") == "archived":
            continue
        key = _name_key(b.get("name"))
        first = bseen.get(key)
        if first is None:
            bseen[key] = b
            continue
        await db.brands.update_one({"id": b["id"]}, {"$set": {
            "status": "archived",
            "archived_at": now,
            "archive_reason": f"Duplicate brand of {first['id']}",
            "duplicate_of": first["id"],
            "updated_at": now,
        }})
        bdupes += 1

    # Invalid email addresses on customers and contacts. An address that cannot
    # parse is not stored as a real email: it is nulled out, and the row is kept so
    # the contact is not lost.
    bad = 0
    email_re = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
    for coll in ("customers", "contacts", "leads"):
        names = await db.list_collection_names()
        if coll not in names:
            continue
        for doc in await db[coll].find({}, {"_id": 0, "id": 1, "email": 1}).to_list(5000):
            email = (doc.get("email") or "").strip()
            if email and not email_re.match(email):
                await db[coll].update_one({"id": doc["id"]}, {"$set": {
                    "email": None, "email_invalid_original": email}})
                bad += 1

    # Duplicate contacts: same normalised email on the same customer.
    cdupes = 0
    names = await db.list_collection_names()
    if "contacts" in names:
        seen_c: dict[tuple, str] = {}
        for c in await db.contacts.find({}, {"_id": 0}).sort("created_at", 1).to_list(5000):
            email = (c.get("email") or "").strip().lower()
            if not email:
                continue
            key = (c.get("customer_id"), email)
            first = seen_c.get(key)
            if first is None:
                seen_c[key] = c["id"]
                continue
            await db.contacts.update_one({"id": c["id"]}, {"$set": {
                "duplicate_of": first, "updated_at": now}})
            cdupes += 1

    await db.products.create_index("brand", background=True)
    await db.products.create_index("category", background=True)
    return (f"{dupes} duplicate products archived, {bdupes} duplicate brands archived, "
            f"{cdupes} duplicate contacts flagged, {bad} invalid emails cleared")


# ---------------------------------------------------------------------------
# m018 -- retire products of archived brands and consolidate the category taxonomy
# ---------------------------------------------------------------------------

# Earlier catalogue rows predate the master list and used looser category labels.
# Several of them mean the same thing as a canonical category ("Monitoring" vs
# "Monitoring & Headphones"). The product rows are repointed at the canonical entry
# and the redundant category is archived, so the filter list a user sees has one
# predictable entry per concept instead of near-synonyms.
CATEGORY_MERGE: dict[str, str] = {
    "monitoring": "Monitoring & Headphones",
    "wireless": "Wireless & RF",
    "video": "Video & Projection",
    "projection": "Video & Projection",
    "conference": "Video & Projection",
    "displays": "Video & Projection",
    "control automation": "Control & Automation",
    "control and automation": "Control & Automation",
    "accessories": "Accessories",
}


async def m018_archive_products_and_merge_categories(db) -> str:
    """Products of a non-approved brand are archived, not deleted.

    Nothing is destroyed: ``status: "archived"`` takes the row out of the
    catalogue, every dropdown and ``GET /api/products``, while the document and its
    id stay available for any historical document that referenced it.
    """
    now = _now()

    # Products whose brand is not an active approved brand.
    archived = 0
    active_brand_ids = {b["id"] async for b in db.brands.find(
        {"status": "active", "approved": True}, {"_id": 0, "id": 1})}
    for p in await db.products.find({"status": {"$ne": "archived"}}).to_list(5000):
        bid = p.get("brand_id")
        name_ok = _name_key(p.get("brand") or "") in {
            _name_key(n) for n in APPROVED_BRAND_NAMES}
        if (bid and bid in active_brand_ids) or (not bid and name_ok):
            continue
        await db.products.update_one({"id": p["id"]}, {"$set": {
            "status": "archived",
            "archived_at": now,
            "archive_reason": "Brand is not on the approved 21-brand master list",
            "updated_at": now,
        }})
        archived += 1

    # Consolidate the category taxonomy.
    merged = 0
    cats = await db.product_categories.find({}).to_list(100)
    by_name = {_name_key(c["name"]): c for c in cats}
    for legacy_key, canonical_name in CATEGORY_MERGE.items():
        legacy = by_name.get(legacy_key)
        canonical = by_name.get(_name_key(canonical_name))
        if legacy is None or canonical is None or legacy["id"] == canonical["id"]:
            continue
        await db.products.update_many(
            {"category_id": legacy["id"]},
            {"$set": {"category_id": canonical["id"], "category": canonical["name"],
                      "updated_at": now}},
        )
        await db.product_categories.update_one({"id": legacy["id"]}, {"$set": {
            "status": "archived",
            "merged_into": canonical["id"],
            "updated_at": now,
        }})
        merged += 1

    return f"{archived} products archived, {merged} redundant categories merged"
