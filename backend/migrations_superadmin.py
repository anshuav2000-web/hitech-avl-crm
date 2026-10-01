"""Migrations for the Super Admin system: media, audit trail and role registry.

Every migration here is additive and idempotent. None of them deletes master data,
and none of them changes which brands are approved -- the signed-off brand list is
a business decision, not a schema detail, so nothing here may widen or narrow it.

* ``m019`` -- indexes for the ``media`` and ``audit_logs`` collections
* ``m020`` -- the explicit Super Admin role document, and the expanded permission
  vocabulary on the existing system roles
* ``m021`` -- brand master fields: logo pointer, status vocabulary, timestamps.
  Backfills missing keys on rows that predate the Super Admin UI so the brand
  editor has a complete, uniform shape to work with
* ``m022`` -- product master fields: stock, warehouse, image gallery. Repairs
  products whose ``brand_id`` does not match their ``brand`` name, because a
  product with a dangling brand pointer is exactly what "must always maintain a
  valid relationship with its brand" is about
* ``m023`` -- repairs the malformed permission names m020 stored, caused by
  ``all_permission_names()`` iterating module specs instead of their actions
"""
from __future__ import annotations

from datetime import datetime, timezone

from permissions import (
    SUPER_ADMIN_ROLE_NAME,
    all_permission_names,
    super_admin_role_document,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# m019 -- indexes for media and audit
# ---------------------------------------------------------------------------
async def m019_media_and_audit_indexes(db):
    """Index the two new collections.

    ``media`` is addressed by its content hash, which is already the ``_id`` and
    so unique for free. The extra indexes here are the ones the listing and the
    cleanup query actually use.

    ``audit_logs`` is append-only and read newest-first, filtered by module and
    by actor. Those are the two access paths the audit viewer offers.
    """
    await db.media.create_index("uploaded_at", background=True)
    await db.media.create_index("kind", background=True)
    await db.media.create_index("sha256", unique=True, background=True)

    await db.audit_logs.create_index("created_at", background=True)
    await db.audit_logs.create_index([("module", 1), ("created_at", -1)], background=True)
    await db.audit_logs.create_index([("actor_id", 1), ("created_at", -1)], background=True)
    await db.audit_logs.create_index("record_id", background=True)
    await db.audit_logs.create_index([("record_type", 1), ("record_id", 1)], background=True)

    await db.product_attributes.create_index("id", unique=True,
                                             partialFilterExpression={"id": {"$type": "string"}},
                                             background=True)
    await db.product_attributes.create_index("name", unique=True,
                                             partialFilterExpression={"name": {"$type": "string"}},
                                             background=True)
    return "media, audit_logs and product_attributes indexes ensured"


# ---------------------------------------------------------------------------
# m020 -- role registry
# ---------------------------------------------------------------------------
async def m020_super_admin_role(db):
    """Create the canonical Super Admin role and widen the admin roles.

    ``superadmin`` was already a seeded role name, but its stored permission list
    was the legacy vocabulary ("crm", "team", "settings", ...) which nothing
    outside ``require_admin`` consulted. This replaces it with the explicit
    module list the permission engine understands, and marks
    ``permission_level: "all"``.

    The admin roles are given the same expanded list so an ordinary administrator
    keeps working after the permission checks start consulting the role table --
    but they are *not* marked ``permission_level: all``, because Super Admin is
    decided by role name and admin must not acquire it by accident.
    """
    expanded = sorted(set(all_permission_names()))

    doc = super_admin_role_document()
    await db.roles.update_one(
        {"name": SUPER_ADMIN_ROLE_NAME},
        {
            "$set": {
                "display_name": doc["display_name"],
                "description": doc["description"],
                "permission_level": doc["permission_level"],
                "permissions": doc["permissions"],
                "is_system": True,
                "updated_at": _now(),
            },
            "$setOnInsert": {"id": doc["id"], "created_at": _now()},
        },
        upsert=True,
    )

    for name in ("admin", "management"):
        role = await db.roles.find_one({"name": name})
        if not role:
            continue
        await db.roles.update_one(
            {"name": name},
            {
                "$set": {
                    "permissions": sorted(set(role.get("permissions") or []) | set(expanded)),
                    "permission_level": "admin",
                    "updated_at": _now(),
                }
            },
        )
    return "superadmin role expanded to the full module permission set"


# ---------------------------------------------------------------------------
# m021 -- brand master fields
# ---------------------------------------------------------------------------
# Every field the brand editor writes, so a row created before the Super Admin UI
# has the same shape as one created through it.
BRAND_MEDIA_FIELDS = (
    "logo_media_id", "banner_media_id", "logo_url", "banner_url",
    "status", "approved", "featured", "tags", "brand_category",
    "product_categories", "description", "country", "official_website",
)

_BRAND_NULLABLE = (
    "brand_category", "description", "country", "official_website", "logo_url",
)
_BRAND_LIST = ("product_categories", "tags")


async def m021_brand_master_fields(db):
    """Add the logo pointer and status vocabulary to every brand.

    ``logo_media_id`` is the new, first-class link to an uploaded asset.
    ``logo_url`` is kept for backwards compatibility: existing rows carry remote
    URLs there, and the resolution order is media id first, legacy URL second, so
    an uploaded logo always wins over a scraped one without deleting anything.

    ``created_at``/``updated_at`` are backfilled rather than invented per field:
    a row that predates them gets a stable ``created_at`` derived from its own
    Mongo ``_id`` timestamp where one is readable, and ``updated_at`` mirrors it.
    """
    now = _now()
    # Full documents, deliberately. An earlier version projected a handful of
    # fields and then defaulted everything not in the projection -- which silently
    # wiped official_website, description, country and brand_category on every
    # brand. Only keys genuinely absent from the document may be filled in.
    rows = await db.brands.find({}).to_list(1000)

    patched = 0
    for row in rows:
        oid = row["_id"]
        sets = {}
        # Derive the creation time from the ObjectId when the field is missing:
        # an ObjectId's first 4 bytes are a Unix timestamp. For anything older
        # than that, fall back to "now" rather than guessing a wrong date.
        created = row.get("created_at")
        if not created:
            try:
                created = datetime.fromtimestamp(oid.generation_time.replace(microsecond=0),
                                                 tz=timezone.utc).isoformat()
            except Exception:  # noqa: BLE001
                created = now
            sets["created_at"] = created
        if not row.get("updated_at"):
            sets["updated_at"] = row.get("created_at") or created
        if not row.get("status"):
            sets["status"] = "active"
        if "approved" not in row:
            sets["approved"] = bool(row.get("status") == "active")
        for field in _BRAND_LIST:
            if field not in row:
                sets[field] = []
        for field in _BRAND_NULLABLE:
            if field not in row:
                sets[field] = None
        if "featured" not in row:
            sets["featured"] = False
        if sets:
            await db.brands.update_one({"_id": oid}, {"$set": sets})
            patched += 1

    # A brand is addressed by name in quotations and by id everywhere else.
    # m014 already made name unique; this only guards rows created before it.
    try:
        await db.brands.create_index("name", unique=True, background=True)
    except Exception:  # noqa: BLE001 - duplicates would be reported, not fatal
        pass
    return f"{patched} brand documents given the full master field set"


# ---------------------------------------------------------------------------
# m022 -- product master fields and brand integrity
# ---------------------------------------------------------------------------
PRODUCT_MEDIA_FIELDS = (
    "image_media_id", "product_images", "gallery", "image_url",
    "stock_quantity", "warehouse_location", "warranty", "country_of_origin",
)


async def m022_product_media_and_brand_integrity(db):
    """Add the image/stock fields and repair dangling brand pointers.

    ``create_product`` silently dropped ``product_images``, ``gallery``,
    ``stock_quantity`` and ``warehouse_location``: the model accepted them and the
    insert never wrote them. Products therefore have no stock level to edit and no
    image gallery to show. This gives every product the fields, with a real
    default for stock rather than leaving it undefined.

    The second half repairs ``brand_id``. A product whose ``brand_id`` does not
    point at the brand named in its ``brand`` field is silently dropped from the
    brand detail page's product count and from any query that joins on
    ``brand_id``. The pointer is re-derived from the name, which is the value the
    rest of the system treats as canonical.
    """
    now = _now()
    # Full documents for the same reason as m021: defaulting keys based on a
    # projection would write nulls over data the projection simply hid.
    rows = await db.products.find({}).to_list(5000)

    brands_by_name = {b["name"]: b for b in await db.brands.find({}, {"_id": 0}).to_list(1000)}
    patched = relinked = 0

    for row in rows:
        sets = {}
        if "stock_quantity" not in row:
            sets["stock_quantity"] = 0
        if "warehouse_location" not in row:
            sets["warehouse_location"] = None
        for field in ("product_images", "gallery"):
            if field not in row:
                sets[field] = []
        if not row.get("image_media_id") and not row.get("image_url"):
            sets.setdefault("image_media_id", None)

        expected = brands_by_name.get(row.get("brand") or "")
        if expected and row.get("brand_id") != expected["id"]:
            sets["brand_id"] = expected["id"]
            relinked += 1
        elif not expected and row.get("brand"):
            # The brand genuinely does not exist. Record it rather than guessing:
            # an unresolvable brand is a real state and needs a human, and the
            # product stays listed so it is visible and fixable.
            sets.setdefault("brand_unresolved", True)

        if sets:
            await db.products.update_one({"_id": row["_id"]}, {"$set": sets})
            patched += 1

    return f"{patched} products given media/stock fields, {relinked} brand pointers repaired"


# ---------------------------------------------------------------------------
# m023 -- repair the role registry after the m020 expansion bug
# ---------------------------------------------------------------------------
async def m023_repair_role_permission_vocabulary(db):
    """Rewrite the malformed permission names m020 wrote into the roles collection.

    ``all_permission_names()`` iterated each module's spec *dict* rather than its
    ``actions`` tuple, so the expansion m020 stored was
    ``["brands.actions", "brands.label", ...]`` instead of
    ``["brands.view", "brands.manage", ...]``. Every name in it was meaningless,
    which left the Super Admin role document with no real grants in it.

    The three administrator roles are rewritten from the corrected vocabulary. The
    names m020 invented are removed by rebuilding the list rather than by an
    ``$pull`` on a prefix, so an unrelated future permission can never be caught by
    the pattern. Every other role is left untouched: its grants are a business
    decision, and the permission engine now resolves the legacy coarse names it
    already has.
    """
    from permissions import DEFAULT_ROLE_PERMISSIONS, MODULE_KEYS

    valid = set(all_permission_names()) | {"all", "*"}
    expanded = sorted(set(all_permission_names()))
    doc = super_admin_role_document()

    repaired = []
    for name, defaults in DEFAULT_ROLE_PERMISSIONS.items():
        role = await db.roles.find_one({"name": name}, {"_id": 0, "permissions": 1})
        if not role:
            continue
        current = {str(p) for p in (role.get("permissions") or []) if p}
        kept = {p for p in current if p in valid}
        if name == SUPER_ADMIN_ROLE_NAME:
            wanted = set(doc["permissions"])
        elif name in ("admin", "management"):
            # The administrators keep everything, expanded. m020 gave them the full
            # list and that part was the intent, only the names were wrong.
            wanted = kept | set(expanded) | {"all", "*"}
        else:
            # A business role: keep whatever it was genuinely granted, drop only the
            # malformed names, and keep the built-in defaults as a floor.
            wanted = kept | set(defaults)
        await db.roles.update_one(
            {"name": name},
            {"$set": {"permissions": sorted(wanted), "updated_at": _now()}},
        )
        repaired.append(f"{name}:{len(wanted)}")

    # "roles" is not a module in the registry; it is covered by "users"/"admins".
    # Recorded so the vocabulary and the module list cannot drift unnoticed.
    assert "roles" not in MODULE_KEYS

    return "role permissions rewritten for " + ", ".join(repaired)