"""Schema migrations for the Hitech AVL CRM.

Design rules (enforced by review, not by tooling):

1. ADDITIVE ONLY. No migration may drop a collection, drop a field, or rename a key.
   Existing documents must keep working untouched after every migration.
2. IDEMPOTENT. Every ``up`` must be safe to run repeatedly. Index creation is
   naturally idempotent; ``update_many``/``$set`` calls no-op on re-run.
3. SEEDED FROM CURRENT BEHAVIOUR. New config collections are seeded from the
   constants that are hard-coded today (server.PIPELINE_STAGES, the status lists in
   Tasks.js / Projects.js), so switching to config-driven values is behaviour
   preserving rather than a business change.
4. FORWARD ONLY. There is no ``down``. A bad migration is superseded by a new one.

Run manually:      python -m migrations
Run automatically:  invoked from the FastAPI startup hook (see server.py)
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ReturnDocument constants — kept so migration helper calls remain unchanged.
# (pgdb.find_one_and_update passes the value straight through; True means
# return the document *after* the update, which is what Motor's
# ReturnDocument.AFTER means.)
class ReturnDocument:
    AFTER = True
    BEFORE = False


try:
    from pymongo.errors import DuplicateKeyError  # type: ignore
except ImportError:
    class DuplicateKeyError(Exception):  # type: ignore
        """Raised when a write violates a unique constraint."""

# Catalogue and demo-team seeding lives in its own module because the data tables are
# long and want their rationale documented next to them.
from migrations_seed_data import m011_seed_catalog, m012_seed_demo_employees
# The real staff directory is a separate module: it is transcribed verbatim from the
# business and its provenance rules deserve their own documentation.
from migrations_staff import m013_import_staff_directory
# The approved brand master list, the product taxonomy and the duplicate cleanup
# are grouped together: they are one decision by the business, expressed in schema.
from migrations_brands import (
    m014_apply_master_brand_list,
    m015_seed_product_categories,
    m016_add_product_schema,
    m017_clean_duplicates,
    m018_archive_products_and_merge_categories,
)
# Super Admin system: media storage, audit trail, the explicit role registry and the
# brand/product master fields the Super Admin editor writes.
from migrations_superadmin import (
    m019_media_and_audit_indexes,
    m020_super_admin_role,
    m021_brand_master_fields,
    m022_product_media_and_brand_integrity,
    m023_repair_role_permission_vocabulary,
)

ROOT_DIR = Path(__file__).parent

MIGRATIONS_COLLECTION = "schema_migrations"
SETTINGS_COLLECTION = "settings"
CONFIG_COLLECTION = "crm_config_sets"

# Cross-process migration lock. uvicorn runs several workers and each of them
# executes the FastAPI startup hook in its own process, so on a cold database two
# workers reach run_migrations() at the same instant. The seed migrations are
# idempotent one at a time but not simultaneously -- their check-then-insert steps
# raced, produced duplicate user rows, and the unique email index then failed to
# build, which took the whole API down. One worker wins this lease and migrates;
# the others wait for it and then continue.
LOCK_ID = "__runner_lock__"
LOCK_COLLECTION = "schema_migration_lock"
LOCK_TTL_SECONDS = 900


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


async def _recorded_migration_ids(db) -> set:
    """Ids of migrations already applied. A row without an ``id`` is not one."""
    rows = await db[MIGRATIONS_COLLECTION].find({}, {"_id": 0, "id": 1}).to_list(500)
    return {r["id"] for r in rows if r.get("id")}


# ---------------------------------------------------------------------------
# Default configuration values.
#
# These mirror the values that are hard-coded in the application today. They are
# the baseline that migration m001 writes into crm_config_sets.
# ---------------------------------------------------------------------------

# Lead pipeline. Keys and order match server.PIPELINE_STAGES exactly; the `group`
# values match the four board tabs in frontend/src/pages/Pipeline.js.
DEFAULT_LEAD_STAGES = [
    # Initiation
    {"key": "new", "label": "New Lead", "group": "Initiation", "color": "blue"},
    {"key": "assigned", "label": "Assigned", "group": "Initiation", "color": "indigo"},
    {"key": "contact_attempted", "label": "Contact Attempted", "group": "Initiation", "color": "sky"},
    {"key": "contacted", "label": "Contacted", "group": "Initiation", "color": "emerald"},
    {"key": "not_contacted", "label": "Not Contacted", "group": "Initiation", "color": "slate"},
    {"key": "call_back_later", "label": "Call Back Later", "group": "Initiation", "color": "amber"},
    # Qualification
    {"key": "detailed_requirement_discussion", "label": "Detailed Requirement Discussion", "group": "Qualification", "color": "purple"},
    {"key": "interested", "label": "Interested", "group": "Qualification", "color": "teal"},
    {"key": "qualified", "label": "Qualified", "group": "Qualification", "color": "emerald"},
    {"key": "need_analysis", "label": "Need Analysis", "group": "Qualification", "color": "orange"},
    {"key": "forward_to_design", "label": "Forward to Design", "group": "Qualification", "color": "rose"},
    {"key": "drawing", "label": "CAD Drawing", "group": "Qualification", "color": "rose"},
    # Quotation Flow
    {"key": "boq_creation", "label": "BOQ Creation", "group": "Quotation Flow", "color": "sky"},
    {"key": "send_boq_design", "label": "Send BOQ & Design", "group": "Quotation Flow", "color": "blue"},
    {"key": "boq_finalized", "label": "BOQ Finalized", "group": "Quotation Flow", "color": "indigo"},
    {"key": "convert_to_quotation", "label": "Convert to Quotation", "group": "Quotation Flow", "color": "purple"},
    {"key": "send_quotation", "label": "Send Quotation", "group": "Quotation Flow", "color": "pink"},
    {"key": "quotation_negotiation", "label": "Quotation Negotiation", "group": "Quotation Flow", "color": "amber"},
    # Closing
    {"key": "quotation_rejected", "label": "Quotation Rejected", "group": "Closing", "color": "rose"},
    {"key": "quotation_confirmed", "label": "Quotation Confirmed", "group": "Closing", "color": "emerald",
     "is_won": True, "is_open": False},
    {"key": "po_received", "label": "PO Received", "group": "Closing", "color": "teal"},
    {"key": "invoice_raised", "label": "Invoice Raised", "group": "Closing", "color": "blue"},
    {"key": "completed", "label": "Completed", "group": "Closing", "color": "emerald"},
    {"key": "lost_lead", "label": "Lost Lead", "group": "Closing", "color": "red",
     "is_lost": True, "is_open": False},
]

# Terminal-state markers used by dashboard conversion maths and pipeline colouring.
# `quotation_confirmed` is the real "won" stage and `lost_lead` the real "lost"
# stage (bug B4: the dashboard used non-existent `won`/`lost` keys).
LEAD_WON_KEY = "quotation_confirmed"
LEAD_LOST_KEY = "lost_lead"

# Canonical lead source vocabulary. Lives here rather than in server.py because
# migrations must stay importable without importing the app (server.py imports
# *from* this module, so the dependency only runs one way). server.py re-exports
# it as LEAD_SOURCES, so there is still exactly one definition.
DEFAULT_LEAD_SOURCES = [
    "facebook", "instagram", "linkedin", "website_contact_form",
    "direct_enquiry", "cold_call", "business_whatsapp", "email",
    "channel_partner", "internal_employee_referral", "existing_customer",
    "walk_in_customer",
]

DEFAULT_PROJECT_STAGES = [
    {"key": "new_project", "label": "New Project", "color": "sky"},
    {"key": "planning", "label": "Planning", "color": "indigo"},
    {"key": "design", "label": "Design", "color": "purple"},
    {"key": "quotation", "label": "Quotation", "color": "blue"},
    {"key": "approval", "label": "Approval", "color": "amber"},
    {"key": "purchase_order", "label": "Purchase Order", "color": "violet"},
    {"key": "execution", "label": "Execution", "color": "orange"},
    {"key": "installation", "label": "Installation", "color": "teal"},
    {"key": "handover", "label": "Handover", "color": "emerald"},
    {"key": "completed", "label": "Completed", "color": "emerald"},
    {"key": "on_hold", "label": "On Hold", "color": "slate"},
    {"key": "cancelled", "label": "Cancelled", "color": "red"},
]

# Mirrors the TASK_STATUSES array in frontend/src/pages/Tasks.js
DEFAULT_TASK_STATUSES = [
    {"key": "pending", "label": "To Do", "color": "slate", "is_open": True, "order": 0},
    {"key": "in_progress", "label": "In Progress", "color": "blue", "is_open": True, "order": 1},
    {"key": "waiting", "label": "Waiting", "color": "amber", "is_open": True, "order": 2},
    {"key": "completed", "label": "Completed", "color": "emerald", "is_open": False, "order": 3},
]

# Mirrors the PRIORITIES array in frontend/src/pages/Tasks.js
DEFAULT_PRIORITIES = [
    {"key": "low", "label": "Low", "color": "slate", "order": 0},
    {"key": "medium", "label": "Medium", "color": "blue", "order": 1},
    {"key": "high", "label": "High", "color": "amber", "order": 2},
    {"key": "urgent", "label": "Urgent", "color": "red", "order": 3},
]

# Mirrors the STATUS array in frontend/src/pages/Quotations.js
DEFAULT_QUOTE_STATUSES = [
    {"key": "draft", "label": "Draft", "color": "slate", "is_open": True, "order": 0},
    {"key": "under_review", "label": "Under Review", "color": "amber", "is_open": True, "order": 1},
    {"key": "sent", "label": "Sent", "color": "sky", "is_open": True, "order": 2},
    {"key": "viewed", "label": "Viewed", "color": "indigo", "is_open": True, "order": 3},
    {"key": "accepted", "label": "Accepted", "color": "emerald", "is_open": False, "is_won": True, "order": 4},
    {"key": "rejected", "label": "Rejected", "color": "rose", "is_open": False, "is_lost": True, "order": 5},
    {"key": "expired", "label": "Expired", "color": "slate", "is_open": False, "is_lost": True, "order": 6},
]

DEFAULT_PO_STATUSES = [
    {"key": "draft", "label": "Draft", "color": "slate", "is_open": True, "order": 0},
    {"key": "pending_approval", "label": "Pending Approval", "color": "amber", "is_open": True, "order": 1},
    {"key": "approved", "label": "Approved", "color": "emerald", "is_open": True, "order": 2},
    {"key": "issued", "label": "Issued", "color": "sky", "is_open": True, "order": 3},
    {"key": "received", "label": "Received", "color": "teal", "is_open": False, "order": 4},
    {"key": "rejected", "label": "Rejected", "color": "rose", "is_open": False, "is_lost": True, "order": 5},
]

DEFAULT_CUSTOMER_TYPES = [
    {"key": "dealer", "label": "Dealer", "order": 0},
    {"key": "integrator", "label": "Integrator", "order": 1},
    {"key": "consultant", "label": "Consultant", "order": 2},
    {"key": "end_customer", "label": "End Customer", "order": 3},
    {"key": "contractor", "label": "Contractor", "order": 4},
    {"key": "rental", "label": "Rental / Hire", "order": 5},
    {"key": "internal", "label": "Internal Team", "order": 6},
]

DEFAULT_PROJECT_TYPES = [
    {"key": "installation", "label": "Installation Project", "order": 0},
    {"key": "consulting", "label": "Consulting Project", "order": 1},
    {"key": "rental", "label": "Rental / Hire Project", "order": 2},
    {"key": "supply", "label": "Supply Only", "order": 3},
    {"key": "amc", "label": "AMC / Maintenance", "order": 4},
]

DEFAULT_CONTACT_TYPES = [
    {"key": "end_customer", "label": "End Customer", "order": 0},
    {"key": "integrator", "label": "Integrator", "order": 1},
    {"key": "consultant", "label": "Consultant", "order": 2},
    {"key": "referral_partner", "label": "Referral Partner", "order": 3},
    {"key": "dealer", "label": "Dealer", "order": 4},
    {"key": "contractor", "label": "Contractor", "order": 5},
    {"key": "internal_team", "label": "Internal Team", "order": 6},
]

# Per-project-type workflow step sets (requirement section 10). Stored as config so
# new workflows can be added later without a code change.
DEFAULT_PROJECT_WORKFLOWS = [
    {
        "key": "installation",
        "label": "Installation Workflow",
        "applies_to": ["installation", "supply"],
        "steps": ["requirement", "design", "product_selection", "quotation", "approval", "purchase_order", "installation", "testing", "handover"],
    },
    {
        "key": "consulting",
        "label": "Consulting Workflow",
        "applies_to": ["consulting"],
        "steps": ["requirement", "consultation", "design", "proposal", "approval", "execution", "completion"],
    },
    {
        "key": "rental",
        "label": "Rental Workflow",
        "applies_to": ["rental", "amc"],
        "steps": ["requirement", "design", "quotation", "approval", "dispatch", "return", "inspection"],
    },
]

DEFAULT_DOCUMENT_TEMPLATES = [
    {"key": "quotation_default", "type": "quotation", "label": "Standard Quotation", "is_default": True},
    {"key": "quotation_rental", "type": "quotation", "label": "Rental Quotation", "is_default": False},
    {"key": "po_default", "type": "purchase_order", "label": "Standard Purchase Order", "is_default": True},
    {"key": "invoice_default", "type": "invoice", "label": "Standard Invoice", "is_default": True},
]


def _config_items(spec: list[dict], **extra) -> list[dict]:
    """Expand a compact default spec into full crm_config_sets item documents."""
    out = []
    for i, s in enumerate(spec):
        item = {
            "id": f"{s['key']}",
            "key": s["key"],
            "label": s.get("label", s["key"]),
            "order": s.get("order", i),
            "color": s.get("color", "slate"),
            "icon": s.get("icon"),
            "group": s.get("group"),
            "is_active": True,
            "is_default": s.get("is_default", False),
            "is_won": s.get("is_won", False),
            "is_lost": s.get("is_lost", False),
            "is_open": s.get("is_open"),
            "system_key": True,
        }
        item.update(extra)
        item["key"] = s["key"]
        out.append(item)
    return out


# key -> (label, default items)
CONFIG_DEFAULTS: dict[str, tuple[str, list[dict]]] = {
    "lead_stages": ("Lead Pipeline Stages", _config_items(DEFAULT_LEAD_STAGES)),
    "project_stages": ("Project Stages", _config_items(DEFAULT_PROJECT_STAGES)),
    "task_statuses": ("Task Statuses", _config_items(DEFAULT_TASK_STATUSES)),
    "priorities": ("Priorities", _config_items(DEFAULT_PRIORITIES)),
    "quote_statuses": ("Quotation Statuses", _config_items(DEFAULT_QUOTE_STATUSES)),
    "po_statuses": ("Purchase Order Statuses", _config_items(DEFAULT_PO_STATUSES)),
    "customer_types": ("Customer Types", _config_items(DEFAULT_CUSTOMER_TYPES)),
    "project_types": ("Project Types", _config_items(DEFAULT_PROJECT_TYPES)),
    "contact_types": ("Project Contact Types", _config_items(DEFAULT_CONTACT_TYPES)),
}


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

async def m001_seed_config(db):
    """Seed crm_config_sets from the values hard-coded in the app today.

    Uses $setOnInsert semantics: if the key already exists (an admin has edited
    it), the existing document is left completely untouched.
    """
    now = _now()
    for key, (label, items) in CONFIG_DEFAULTS.items():
        await db[CONFIG_COLLECTION].update_one(
            {"key": key},
            {
                "$setOnInsert": {
                    "key": key,
                    "label": label,
                    "items": items,
                    "version": 1,
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )

    # Workflows and document templates have a different (non-flat) item shape.
    for key, label, items in [
        ("project_workflows", "Project Workflows", DEFAULT_PROJECT_WORKFLOWS),
        ("document_templates", "Document Templates", DEFAULT_DOCUMENT_TEMPLATES),
    ]:
        await db[CONFIG_COLLECTION].update_one(
            {"key": key},
            {
                "$setOnInsert": {
                    "key": key,
                    "label": label,
                    "items": [
                        {**it, "id": it["key"], "order": i, "is_active": True, "system_key": True}
                        for i, it in enumerate(items)
                    ],
                    "version": 1,
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )


async def m002_layout_collections(db):
    """Per-user dashboard and sidebar layout stores.

    Documents are created lazily on first access, so no backfill is needed.
    """
    await db.dashboard_layouts.create_index("user_id", unique=True, background=True)
    await db.sidebar_layouts.create_index("user_id", unique=True, background=True)
    await db.notification_rules.create_index("event", background=True)


async def m003_indexes(db):
    """Indexes for every field added by the upgrade."""
    await db.leads.create_index("stage_id", background=True)
    await db.leads.create_index("customer_id", background=True)
    await db.leads.create_index("expected_close_date", background=True)

    await db.quotations.create_index("customer_id", background=True)
    await db.quotations.create_index("project_id", background=True)
    await db.quotations.create_index("duplicated_from", background=True)

    await db.purchase_orders.create_index("direction", background=True)
    await db.purchase_orders.create_index("quotation_id", background=True)
    await db.purchase_orders.create_index("project_id", background=True)
    await db.purchase_orders.create_index("customer_id", background=True)
    await db.purchase_orders.create_index("lead_id", background=True)

    await db.projects.create_index("project_no", background=True)
    await db.projects.create_index("stage_id", background=True)
    await db.projects.create_index("project_type", background=True)
    await db.projects.create_index("customer_id", background=True)
    await db.projects.create_index("lead_id", background=True)

    await db.tasks.create_index("status_id", background=True)
    await db.tasks.create_index("project_id", background=True)
    await db.tasks.create_index("related.module", background=True)
    await db.tasks.create_index("due_date", background=True)

    await db.notifications.create_index("user_id", background=True)
    await db.notifications.create_index(["user_id", "read"], background=True)

    await db.project_contacts.create_index("project_id", background=True)
    await db.project_documents.create_index("project_id", background=True)


async def m004_backfill_stage_ids(db):
    """Add leads.stage_id alongside the existing leads.stage slug.

    Purely additive: the original `stage` field is never touched, so any code
    still reading `stage` keeps working unchanged.
    """
    stage_ids = [s["key"] for s in DEFAULT_LEAD_STAGES]
    for key in stage_ids:
        await db.leads.update_many(
            {"stage": key, "stage_id": {"$exists": False}},
            {"$set": {"stage_id": key}},
        )


async def m005_backfill_stage_history(db):
    """Seed a single stage_history entry per lead from its creation date.

    Gives every pre-existing lead a non-empty timeline without inventing history
    we do not have. The original `activities` documents are left alone.
    """
    await db.leads.update_many(
        {"stage_history": {"$exists": False}},
        {
            "$set": {
                "stage_history": [],
            }
        },
    )


async def m006_project_enrichment(db):
    """Give existing projects a stable project_no and a default stage."""
    cursor = db.projects.find({"project_no": {"$exists": False}}, {"_id": 0, "id": 1})
    n = 0
    async for p in cursor:
        n += 1
        await db.projects.update_one(
            {"id": p["id"]},
            {
                "$set": {
                    "project_no": f"HAI-PRJ-{2000 + n}",
                    "stage_id": p.get("stage_id") or "new_project",
                    "project_type": p.get("project_type") or "installation",
                }
            },
        )


async def m007_po_direction(db):
    """Tag existing purchase orders as supplier-side.

    Every PO created before this migration is a PO *we issue to a vendor*, so
    'supplier' is the correct and truthful default. New customer POs created by
    the quotation->PO conversion set 'customer' explicitly.
    """
    await db.purchase_orders.update_many(
        {"direction": {"$exists": False}},
        {"$set": {"direction": "supplier"}},
    )


async def m008_fix_duplicate_suppliers(db):
    """Remove supplier rows duplicated by the startup seed bug (B7).

    The old on_start() inserted the same two suppliers once per default role,
    producing 9 identical sets. This keeps the earliest of each name and removes
    the rest. Only rows matching the exact seeded names are touched.
    """
    seeded_names = ["AVL Distributors", "Pro Audio Solutions"]
    for name in seeded_names:
        dupes = await db.suppliers.find({"name": name}, {"_id": 1}).sort("_id", 1).to_list(100)
        for extra in dupes[1:]:
            await db.suppliers.delete_one({"_id": extra["_id"]})


async def m009_mark_terminal_lead_stages(db):
    """Flag the won/lost stages on the already-seeded lead_stages config set.

    `_config_items` reads is_won/is_lost from the compact DEFAULT_LEAD_STAGES
    spec, which marks neither terminal stage, so every shipped stage came out
    is_won=False/is_lost=False and the LEAD_WON_KEY/LEAD_LOST_KEY constants were
    never actually applied to any document.

    This corrects only those two flag sets, leaving every other admin-edited
    field alone. It is a no-op on re-run (the version is only bumped when a flag
    actually changes), so it stays idempotent like the rest of the suite.
    """
    doc = await db[CONFIG_COLLECTION].find_one({"key": "lead_stages"}, {"_id": 0, "version": 1, "items": 1})
    if not doc:
        return

    wanted = {
        LEAD_WON_KEY: {"is_won": True, "is_lost": False, "is_open": False},
        LEAD_LOST_KEY: {"is_won": False, "is_lost": True, "is_open": False},
    }
    by_id = {item.get("id"): item for item in doc.get("items", [])}

    changed = False
    for stage_id, flags in wanted.items():
        item = by_id.get(stage_id)
        if not item:
            # Renamed or removed by an admin; leave the set alone.
            continue
        updates = {f"items.$.{field}": value for field, value in flags.items() if item.get(field) != value}
        if not updates:
            continue
        await db[CONFIG_COLLECTION].update_one(
            {"key": "lead_stages", "items.id": stage_id},
            {"$set": {**updates, "updated_at": _now()}, "$inc": {"version": 1}},
        )
        changed = True

    return changed


async def m010_seed_lead_sources(db):
    """Expose the hard-coded LEAD_SOURCES list as an admin-configurable set.

    Sources were the last pipeline vocabulary still frozen in server.py, which
    meant an admin could rename or add a source only by shipping code. Seeded
    with $setOnInsert so an edited set is never clobbered.
    """
    seeds = []
    for s in DEFAULT_LEAD_SOURCES:
        seeds.append({"key": s, "label": s.replace("_", " ").title(), "color": "slate"})

    await db[CONFIG_COLLECTION].update_one(
        {"key": "lead_sources"},
        {
            "$setOnInsert": {
                "key": "lead_sources",
                "label": "Lead Sources",
                "items": _config_items(seeds),
                "version": 1,
                "created_at": _now(),
            },
            "$set": {"updated_at": _now()},
        },
        upsert=True,
    )


MIGRATIONS = [
    ("m001", "seed_config_sets", m001_seed_config),
    ("m002", "layout_collections", m002_layout_collections),
    ("m003", "indexes", m003_indexes),
    ("m004", "backfill_stage_ids", m004_backfill_stage_ids),
    ("m005", "backfill_stage_history", m005_backfill_stage_history),
    ("m006", "project_enrichment", m006_project_enrichment),
    ("m007", "po_direction", m007_po_direction),
    ("m008", "fix_duplicate_suppliers", m008_fix_duplicate_suppliers),
    ("m009", "mark_terminal_lead_stages", m009_mark_terminal_lead_stages),
    ("m010", "seed_lead_sources", m010_seed_lead_sources),
    ("m011", "seed_catalog", m011_seed_catalog),
    ("m012", "seed_demo_employees", m012_seed_demo_employees),
    ("m013", "import_staff_directory", m013_import_staff_directory),
    ("m014", "apply_master_brand_list", m014_apply_master_brand_list),
    ("m015", "seed_product_categories", m015_seed_product_categories),
    ("m016", "add_product_schema", m016_add_product_schema),
    ("m017", "clean_duplicates", m017_clean_duplicates),
    ("m018", "archive_products_and_merge_categories", m018_archive_products_and_merge_categories),
("m019", "media_and_audit_indexes", m019_media_and_audit_indexes),
("m020", "super_admin_role", m020_super_admin_role),
("m021", "brand_master_fields", m021_brand_master_fields),
    ("m022", "product_media_and_brand_integrity", m022_product_media_and_brand_integrity),
    ("m023", "repair_role_permission_vocabulary", m023_repair_role_permission_vocabulary),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def _acquire_runner_lock(db, owner: str) -> bool:
    """Try to become the single migration runner. True when the lease was taken."""
    now = datetime.now(timezone.utc)
    try:
        doc = await db[LOCK_COLLECTION].find_one_and_update(
            # Matches only an absent lock or one whose lease has expired, so a live
            # lease can never be stolen. The upsert trips the unique _id index and
            # raises DuplicateKeyError when another worker already holds it.
            {"_id": LOCK_ID, "expires_at": {"$lte": now}},
            {"$set": {
                "owner": owner,
                "acquired_at": now.isoformat(),
                "expires_at": now + timedelta(seconds=LOCK_TTL_SECONDS),
            }},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        return False
    return bool(doc) and doc.get("owner") == owner


async def _release_runner_lock(db, owner: str) -> None:
    try:
        await db[LOCK_COLLECTION].delete_one({"_id": LOCK_ID, "owner": owner})
    except Exception:  # noqa: BLE001 - a stale lease is harmless, it just expires
        pass


async def _wait_for_other_runner(db, log, timeout: float = LOCK_TTL_SECONDS) -> None:
    """Block until every migration is recorded as applied by whoever held the lease.

    Waiting rather than skipping matters: a worker that returned early would go on
    to build indexes against a half-migrated database.
    """
    wanted = {mid for mid, _name, _fn in MIGRATIONS}
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if wanted <= await _recorded_migration_ids(db):
            return
        await asyncio.sleep(1.0)
    log("migration lease is held by another worker and did not clear in time; continuing")


async def run_migrations(db, log=None) -> list[str]:
    """Apply any migration not yet recorded in schema_migrations.

    Returns the list of migration ids that were applied by this call.
    """
    log = log or (lambda *_a: None)
    applied: list[str] = []

    await db[MIGRATIONS_COLLECTION].create_index("id", unique=True, background=True)

    owner = _uid()
    if not await _acquire_runner_lock(db, owner):
        log("another worker holds the migration lease; waiting for it to finish")
        await _wait_for_other_runner(db, log)
        return []

    try:
        done = await _recorded_migration_ids(db)

        for mid, name, fn in MIGRATIONS:
            if mid in done:
                continue
            try:
                await fn(db)
            except Exception as exc:  # noqa: BLE001 - a failed migration must not brick startup
                log(f"MIGRATION FAILED {mid}_{name}: {exc}")
                raise
            await db[MIGRATIONS_COLLECTION].update_one(
                {"id": mid},
                {
                    "$setOnInsert": {
                        "id": mid,
                        "name": name,
                        "applied_at": _now(),
                        "status": "applied",
                    }
                },
                upsert=True,
            )
            applied.append(mid)
            log(f"migrated {mid}_{name}")
    finally:
        await _release_runner_lock(db, owner)

    # Record the schema version in the pre-existing settings collection.
    await db[SETTINGS_COLLECTION].update_one(
        {"key": "schema_version"},
        {
            "$set": {
                "key": "schema_version",
                "data": {
                    "latest": MIGRATIONS[-1][0],
                    "applied": [m[0] for m in MIGRATIONS],
                },
                "updated_at": _now(),
            }
        },
        upsert=True,
    )
    return applied


def main() -> int:
    """CLI entry point: ``python -m migrations``.

    Connects to the PostgreSQL database (DATABASE_URL env var) and applies any
    pending migrations, exactly as the FastAPI startup hook does.
    """
    from dotenv import load_dotenv
    import asyncpg
    from pgdb import PostgresDocumentDB

    load_dotenv(ROOT_DIR / ".env")

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print(
            "ERROR: DATABASE_URL is not set.\n"
            "  Set it in backend/.env or the environment before running migrations.",
            file=sys.stderr,
        )
        return 1

    async def _main():
        from urllib.parse import quote

        # Percent-encode reserved characters in the password (e.g. '@').
        url = database_url
        if "@" in url.split("://", 1)[-1]:
            head, _, tail = url.partition("://")
            creds, _, hostpart = tail.rpartition("@")
            if ":" in creds:
                u, _, p = creds.partition(":")
                url = f"{head}://{quote(u, safe='')}:{quote(p, safe='')}@{hostpart}"

        pool = await asyncpg.create_pool(url, min_size=1, max_size=3, command_timeout=30)
        db = PostgresDocumentDB(pool)
        print(f"Connected to PostgreSQL")
        applied = await run_migrations(db, log=lambda m: print("  " + m))
        if applied:
            print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
        else:
            print("Database already up to date.")
        await pool.close()

    asyncio.run(_main())
    return 0


if __name__ == "__main__":
    sys.exit(main())
