"""PostgreSQL schema for the Hitech AVL CRM.

This module is the **single source of truth** for the database shape.
``build_schema()`` produces the exact SQL that ``backend/supabase_schema.sql``
contains; ``backend/supabase_schema.sql`` is generated from here and a test
(``tests/test_schema_sync.py``) fails if the two ever drift. Change the schema
here, then regenerate the .sql.

Storage model
-------------
The backend (``server.py``) is written against the Motor API, and ``pgdb.py``
keeps that call surface intact by storing each MongoDB document verbatim in a
``jsonb`` column. So the database is a document store built out of relational
tables: one table per collection, three columns.

    create table c_leads (
        doc_id     text primary key,   -- the document's _id
        body       jsonb not null,     -- the whole document, verbatim
        pub_id     text,               -- the document's public "id" field
        updated_at timestamptz not null default now()
    )

Why jsonb and not typed columns: the app stores whatever fields a module needs,
and new fields are added by Python migrations, not by DDL. A typed schema would
have to be edited in lockstep with every endpoint and would silently drop data
the running code expects. Nothing is lost this way, and nothing has to be
declared up front.

``pub_id`` is the one denormalisation, and it is load-bearing: "look up by id" is
the single hottest query in the API (``db.users.find_one({"id": ...})`` and its
equivalent in every module). As a plain indexed text column it is an equality
scan, and on a jsonb expression index Postgres cannot answer it at all.

Two indexes back every table:

* ``ix_c_x_pub_id``    -- equality lookups by public id
* ``ix_c_x_body``      -- ``gin (body jsonb_path_ops)`` for containment queries

On top of those, :data:`INDEXES` declares an expression btree per field the
application actually filters, sorts or joins on. Those matter: ``jsonb_path_ops``
cannot serve ``body #>> '{assigned_to}' = $1``, so without them every list
endpoint is a sequential scan. The list is derived from the ``create_index``
calls in ``server.py``'s startup hook plus the filter and sort keys of every
endpoint.

Supabase specifics
------------------
Supabase grants ``anon`` and ``authenticated`` full access to new tables in the
``public`` schema through default privileges. This schema holds password
hashes, customer PII and revenue. :func:`build_schema` therefore revokes those
grants explicitly -- see :data:`REVOKE_FROM_ANON`. The application connects
directly over ``asyncpg`` as the ``postgres`` role, which is unaffected.
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------
# Every collection the backend reads or writes, unioned with everything present
# in the 2026-10-01 backup so importing the backup needs no DDL change.
#
# Keep this list closed: ``pgdb.PostgresDocumentDB.__getattr__`` happily returns a
# Collection handle for *any* name, so a collection that is missing here does not
# fail loudly at import -- it fails as "relation c_<name> does not exist" on the
# first request that touches it. That is how the Inventory, AMC, Packages,
# Product Categories, Product Attributes, Meta Marketing, Tally, Brand Access
# Requests and Activity Logs modules were all dead in the running application.
COLLECTIONS: List[str] = [
    # -- Application, auth, configuration --------------------------------
    "users",
    "roles",
    "schema_migrations",
    "schema_migration_lock",
    "settings",
    "crm_config_sets",
    "sidebar_layouts",
    "dashboard_layouts",
    "audit_logs",
    "activity_logs",
    "notification_rules",
    # -- Sales pipeline ---------------------------------------------------
    "leads",
    "lost_leads",
    "lead_qualifications",
    "activities",
    "follow_ups",
    "negotiations",
    "requirement_discussions",
    "contact_attempts",
    "sales_targets",
    "notifications",
    # -- Customers --------------------------------------------------------
    "customers",
    "contacts",
    "project_contacts",
    # -- Catalogue --------------------------------------------------------
    "products",
    "brands",
    "product_categories",
    "product_attributes",
    "packages",
    "inventory",
    "amcs",
    # -- Quotes, orders, delivery ----------------------------------------
    "quotations",
    "purchase_orders",
    "boqs",
    "work_orders",
    "shipments",
    "bookings",
    "design_tasks",
    "accounting",
    "invoices",
    # -- Projects ---------------------------------------------------------
    "projects",
    "project_documents",
    "reports",
    # -- Suppliers --------------------------------------------------------
    "suppliers",
    "brand_requests",
    # -- Comms / integrations --------------------------------------------
    "email_logs",
    "webhook_settings",
    "webhook_logs",
    "resend_settings",
    "meta_settings",
    "tally_settings",
    "sync_logs",
    "events",
    "campaigns",
    "social_posts",
    # -- Binary payloads (uploaded media) --------------------------------
    "media",
]

# Collections where the document's public ``id`` is the natural key. The
# application relies on these being unique (it fetches by id and updates by id),
# so a partial unique index enforces it. Partial, not plain: a row imported from
# the backup may carry no public id, and a plain unique index would collide on
# every such row.
UNIQUE_PUB_ID: List[str] = [
    "users",
    "roles",
    "schema_migrations",
    "settings",
    "crm_config_sets",
    "webhook_settings",
    "resend_settings",
    "meta_settings",
    "tally_settings",
    "leads",
    "customers",
    "contacts",
    "products",
    "brands",
    "product_categories",
    "product_attributes",
    "packages",
    "projects",
    "project_documents",
    "quotations",
    "purchase_orders",
    "boqs",
    "work_orders",
    "accounting",
    "invoices",
    "events",
    "tasks",
    "shipments",
    "bookings",
    "design_tasks",
    "suppliers",
    "social_posts",
    "campaigns",
    "amcs",
    "inventory",
    "reports",
    "sales_targets",
]

# Collections that hold no rows of their own and are excluded from the
# dashboard "row count" summary. Kept for readability of the generated SQL.


# ---------------------------------------------------------------------------
# Expression indexes
# ---------------------------------------------------------------------------
class Index:
    """One btree index over ``body #>> '{field}'`` (one column per field).

    ``unique`` indexes are emitted inside a DO block that downgrades a failure
    to a WARNING, so duplicate legacy data can never abort the whole schema
    script. ``where`` restricts the index to the rows the uniqueness applies to.
    """

    __slots__ = ("collection", "fields", "unique", "where", "include")

    def __init__(
        self,
        collection: str,
        fields: Sequence[str],
        unique: bool = False,
        where: Optional[str] = None,
        include: Sequence[str] = (),
    ) -> None:
        self.collection = collection
        self.fields = tuple(fields)
        self.unique = unique
        self.where = where
        self.include = tuple(include)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        kind = "UNIQUE " if self.unique else ""
        return f"<Index {kind}{self.collection} {'+'.join(self.fields)}>"


# Rows where the field is present at all. Used for the "unique if not null"
# indexes, which mirror the application's own ``partialFilterExpression`` rules.
_NOT_NULL = "((body #>> '{%s}') IS NOT NULL)"

# Natural-key indexes the application enforces in code. They are declared here so
# the constraint survives outside the app and so lookups do not scan.
def _U(field: str) -> str:
    return _NOT_NULL % field


def _indexes() -> List[Index]:
    out: List[Index] = [
        # -- users / auth ------------------------------------------------
        Index("users", ["email"], unique=True, where=_U("email")),
        Index("users", ["role"]),
        Index("users", ["name"]),
        Index("roles", ["name"], unique=True, where=_U("name")),
        Index("settings", ["key"], unique=True, where=_U("key")),
        Index("crm_config_sets", ["key"], unique=True, where=_U("key")),
        Index("schema_migrations", ["id"], unique=True, where=_U("id")),
        Index("notification_rules", ["event"]),
        Index("audit_logs", ["user_id"]),
        Index("audit_logs", ["record_type"]),
        Index("audit_logs", ["record_id"]),
        Index("audit_logs", ["created_at"]),
        Index("activity_logs", ["user_id"]),
        Index("activity_logs", ["module"]),
        Index("activity_logs", ["record_id"]),
        Index("activity_logs", ["created_at"]),
        Index("dashboard_layouts", ["user_id"], unique=True, where=_U("user_id")),
        Index("sidebar_layouts", ["user_id"], unique=True, where=_U("user_id")),
        # -- leads --------------------------------------------------------
        Index("leads", ["assigned_to"]),
        Index("leads", ["stage"]),
        Index("leads", ["stage_id"]),
        Index("leads", ["source"]),
        Index("leads", ["customer_id"]),
        Index("leads", ["created_by"]),
        Index("leads", ["email"]),
        Index("leads", ["created_at"]),
        Index("leads", ["follow_up_date"]),
        Index("leads", ["expected_close_date"]),
        # (assigned_to, stage) is the sales dashboard's main query.
        Index("leads", ["assigned_to", "stage"]),
        # -- pipeline companions -----------------------------------------
        Index("activities", ["lead_id"]),
        Index("activities", ["user_id"]),
        Index("activities", ["project_id"]),
        Index("activities", ["created_at"]),
        Index("activities", ["follow_up_at"]),
        Index("follow_ups", ["lead_id"]),
        Index("follow_ups", ["created_by"]),
        Index("follow_ups", ["status"]),
        Index("follow_ups", ["follow_up_date"]),
        Index("contact_attempts", ["lead_id"]),
        Index("contact_attempts", ["created_at"]),
        # Not unique: qualify_lead inserts a fresh row on every re-qualification,
        # so one lead legitimately has several.
        Index("lead_qualifications", ["lead_id"]),
        Index("lost_leads", ["lead_id"], unique=True, where=_U("lead_id")),
        Index("lost_leads", ["reason"]),
        Index("requirement_discussions", ["lead_id"]),
        Index("negotiations", ["lead_id"]),
        Index("negotiations", ["quotation_id"]),
        Index("notifications", ["user_id"]),
        Index("notifications", ["read"]),
        Index("notifications", ["created_at"]),
        # (user_id, read) backs the unread-count badge.
        Index("notifications", ["user_id", "read"]),
        Index("sales_targets", ["user_id"]),
        Index("reports", ["generated_by"]),
        Index("reports", ["generated_at"]),
        # -- customers ----------------------------------------------------
        Index("customers", ["name"]),
        Index("customers", ["email"]),
        Index("contacts", ["name"]),
        Index("contacts", ["email"]),
        Index("contacts", ["customer_id"]),
        Index("contacts", ["company"]),
        # -- catalogue ----------------------------------------------------
        Index("brands", ["name"], unique=True, where=_U("name")),
        Index("products", ["brand_id"]),
        Index("products", ["category_id"]),
        Index("products", ["sku"], unique=True, where=_U("sku")),
        Index("products", ["status"]),
        Index("products", ["name"]),
        Index("product_categories", ["name"], unique=True, where=_U("name")),
        Index("product_categories", ["parent_id"]),
        Index("product_attributes", ["name"], unique=True, where=_U("name")),
        Index("packages", ["name"]),
        Index("inventory", ["product_id"]),
        Index("inventory", ["shipment_id"]),
        Index("inventory", ["status"]),
        Index("inventory", ["created_at"]),
        Index("amcs", ["status"]),
        Index("amcs", ["end_date"]),
        Index("amcs", ["customer_id"]),
        # -- quotations / orders / delivery ------------------------------
        Index("quotations", ["lead_id"]),
        Index("quotations", ["created_by"]),
        Index("quotations", ["status"]),
        Index("quotations", ["quote_status"]),
        Index("quotations", ["customer_id"]),
        Index("quotations", ["project_id"]),
        Index("quotations", ["created_at"]),
        Index("quotations", ["due_date"]),
        # The public share link is looked up by token on an unauthenticated route.
        Index("quotations", ["share_token"], unique=True, where=_U("share_token")),
        Index("purchase_orders", ["po_no"], unique=True, where=_U("po_no")),
        Index("purchase_orders", ["supplier_id"]),
        Index("purchase_orders", ["customer_id"]),
        Index("purchase_orders", ["quotation_id"]),
        Index("purchase_orders", ["lead_id"]),
        Index("purchase_orders", ["project_id"]),
        Index("purchase_orders", ["direction"]),
        Index("purchase_orders", ["status"]),
        Index("purchase_orders", ["created_at"]),
        Index("boqs", ["lead_id"]),
        Index("boqs", ["status"]),
        Index("work_orders", ["customer_id"]),
        Index("work_orders", ["assigned_to"]),
        Index("work_orders", ["status"]),
        Index("work_orders", ["scheduled_date"]),
        Index("shipments", ["status"]),
        Index("shipments", ["eta"]),
        Index("shipments", ["oem"]),
        Index("shipments", ["created_at"]),
        Index("bookings", ["service"]),
        Index("bookings", ["date"]),
        Index("design_tasks", ["lead_id"]),
        Index("design_tasks", ["assigned_to"]),
        Index("design_tasks", ["status"]),
        Index("accounting", ["doc_no"]),
        Index("accounting", ["type"]),
        Index("accounting", ["status"]),
        Index("accounting", ["date"]),
        Index("invoices", ["invoice_no"], unique=True, where=_U("invoice_no")),
        Index("invoices", ["customer_name"]),
        Index("invoices", ["quotation_id"]),
        Index("invoices", ["po_id"]),
        Index("invoices", ["status"]),
        Index("invoices", ["due_date"]),
        Index("suppliers", ["name"]),
        Index("brand_requests", ["user_id"]),
        Index("brand_requests", ["brand"]),
        Index("brand_requests", ["status"]),
        # -- projects -----------------------------------------------------
        Index("projects", ["project_no"], unique=True, where=_U("project_no")),
        Index("projects", ["name"]),
        Index("projects", ["created_by"]),
        Index("projects", ["manager_id"]),
        Index("projects", ["stage_id"]),
        Index("projects", ["status"]),
        Index("projects", ["lead_id"]),
        Index("projects", ["customer_id"]),
        Index("projects", ["created_at"]),
        Index("project_contacts", ["project_id"]),
        Index("project_documents", ["project_id"]),
        # -- calendar / marketing / comms ---------------------------------
        Index("events", ["title"]),
        Index("events", ["start_time"]),
        Index("events", ["lead_id"]),
        Index("campaigns", ["name"]),
        Index("social_posts", ["title"]),
        Index("social_posts", ["status"]),
        Index("social_posts", ["scheduled_at"]),
        Index("email_logs", ["event"]),
        Index("email_logs", ["created_at"]),
        Index("webhook_logs", ["event"]),
        Index("webhook_logs", ["created_at"]),
        Index("sync_logs", ["started_at"]),
        Index("media", ["uploaded_at"]),
        Index("media", ["entity"]),
        Index("media", ["brand_id"]),
        Index("media", ["product_id"]),
    ]
    return out


INDEXES: List[Index] = _indexes()

# Supabase grants these roles full access to new tables in ``public`` through
# default privileges. The CRM tables must not be reachable through PostgREST with
# the project's anon key: they contain bcrypt password hashes, customer contact
# details and revenue figures. The application authenticates with its own JWT and
# connects over ``asyncpg`` as ``postgres``, so it does not need these roles at
# all.
REVOKE_FROM_ANON: List[str] = ["anon", "authenticated"]


# ---------------------------------------------------------------------------
# SQL rendering
# ---------------------------------------------------------------------------
def _table(name: str) -> str:
    return "c_" + re.sub(r"[^a-z0-9_]", "_", name.lower())


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _ident(name: str) -> str:
    """Shorten an identifier to Postgres' 63-character limit, deterministically."""
    if len(name) <= 63:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return name[: 63 - 9] + "_" + digest


def _columns(fields: Iterable[str]) -> str:
    return ", ".join("(body #>> '{%s}')" % f.replace(",", "") for f in fields)


def _index_name(idx: Index) -> str:
    kind = "ux" if idx.unique else "ix"
    return _ident("%s_%s_%s" % (kind, _table(idx.collection), "_".join(_slug(f) for f in idx.fields)))


def _create_table(name: str) -> str:
    table = _table(name)
    return f"""-- {name}
CREATE TABLE IF NOT EXISTS {table} (
    doc_id     text PRIMARY KEY,
    body       jsonb NOT NULL,
    pub_id     text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_{table}_pub_id ON {table} (pub_id);
CREATE INDEX IF NOT EXISTS ix_{table}_body ON {table} USING gin (body jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_{table}_updated_at ON {table} (updated_at);
"""


def _create_unique_index_sql(idx: Index) -> str:
    name = _index_name(idx)
    table = _table(idx.collection)
    cols = _columns(idx.fields)
    unique = "UNIQUE " if idx.unique else ""
    where = f"\n    WHERE {idx.where}" if idx.where else ""
    return (
        f"-- {table}.{'+'.join(idx.fields)}"
        f"\nDO $crm$\nBEGIN\n"
        f"    CREATE {unique}INDEX IF NOT EXISTS {name} ON {table} ({cols}){where};\n"
        f"EXCEPTION WHEN others THEN\n"
        f"    RAISE WARNING 'index {name} not created: %', SQLERRM;\n"
        f"END\n$crm$;"
    )


def _create_index_sql(idx: Index) -> str:
    name = _index_name(idx)
    table = _table(idx.collection)
    cols = _columns(idx.fields)
    where = f" WHERE {idx.where}" if idx.where else ""
    return (
        f"-- {table}.{'+'.join(idx.fields)}\n"
        f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols}){where};"
    )


def _dedupe(indexes: Iterable[Index]) -> List[Index]:
    """First declaration of a given index name wins; a repeat is a no-op in SQL."""
    seen = set()
    out: List[Index] = []
    for idx in indexes:
        name = _index_name(idx)
        if name in seen:
            continue
        seen.add(name)
        out.append(idx)
    return out


def _effective_indexes() -> List[Index]:
    """Public-id uniqueness plus the query indexes, with duplicates resolved."""
    pub_id = [Index(n, ["id"], unique=True, where=_U("id")) for n in UNIQUE_PUB_ID]
    return _dedupe(pub_id + INDEXES)


def index_statements() -> List[str]:
    """Every index DDL, used by pgbootstrap to verify the schema landed."""
    return [
        _create_unique_index_sql(i) if i.unique else _create_index_sql(i)
        for i in _effective_indexes()
    ]


def build_schema() -> str:
    """Render the complete, idempotent schema.

    Safe to run repeatedly: every statement is ``IF NOT EXISTS`` or a
    ``CREATE OR REPLACE``, and no statement drops or renames anything.
    """
    out: List[str] = [
        "-- ===========================================================================",
        "-- Hitech AVL CRM -- Supabase PostgreSQL schema",
        "--",
        "-- GENERATED FILE -- do not edit by hand.",
        "-- Source of truth: backend/pgschema.py",
        "-- Regenerate with:  python backend/pgschema.py > backend/supabase_schema.sql",
        "--",
        "-- Apply with any of:",
        "--   psql \"$DATABASE_URL\" -v ON_ERROR_STOP=1 -f backend/supabase_schema.sql",
        "--   Supabase dashboard -> SQL Editor -> paste this file -> Run",
        "--   python -m backend.pgbootstrap --schema",
        "--",
        "-- One table per application collection. The document is stored verbatim in",
        "-- `body` (jsonb) because the FastAPI backend is written against the Motor API",
        "-- and adds fields from Python migrations, not from DDL. `pub_id` mirrors the",
        "-- document's public `id` so the hottest query in the API -- fetch by id -- is an",
        "-- indexed equality instead of a JSONB walk.",
        "--",
        "-- This script is idempotent and additive. It never drops or renames anything, and",
        "-- a unique index that legacy duplicate data would reject is reported as a WARNING",
        "-- rather than aborting the run.",
        "-- ===========================================================================",
        "",
        'CREATE EXTENSION IF NOT EXISTS "pgcrypto";',
        "",
        "-- ---------------------------------------------------------------------",
        "-- Tables",
        "-- ---------------------------------------------------------------------",
        "",
    ]

    for name in COLLECTIONS:
        out.append(_create_table(name))
        out.append("")

    # pub_id uniqueness, expressed through the shared declaration above so there
    # is one code path for "unique if not null".
    out.append("-- ---------------------------------------------------------------------")
    out.append("-- Public-id uniqueness and query indexes")
    out.append("--")
    out.append("-- Public-id: these collections are fetched and updated by their public `id`, so a")
    out.append("-- duplicate id silently edits the wrong record. Partial, so a row with no public")
    out.append("-- id (possible when importing the backup) does not collide with another such row.")
    out.append("--")
    out.append("-- Query: gin(body jsonb_path_ops) cannot answer `body #>> '{field}' = $1`, which")
    out.append("-- is how the shim compiles every equality, range and sort. Without these btree")
    out.append("-- indexes every list endpoint is a sequential scan. Derived from the")
    out.append("-- create_index calls in server.py's startup hook plus the filter and sort keys")
    out.append("-- of every endpoint.")
    out.append("-- ---------------------------------------------------------------------")
    out.append("")
    for idx in _effective_indexes():
        out.append(_create_unique_index_sql(idx) if idx.unique else _create_index_sql(idx))
        out.append("")

    out.append("-- ---------------------------------------------------------------------")
    out.append("-- Supabase access control")
    out.append("--")
    out.append("-- Supabase's default privileges grant anon/authenticated full access to new")
    out.append("-- tables in `public`. These tables hold bcrypt password hashes, customer PII and")
    out.append("-- revenue, so that grant is removed explicitly -- for the tables that exist now and")
    out.append("-- for anything created later. The backend connects over asyncpg as `postgres` and")
    out.append("-- authenticates with its own JWT, so it is unaffected.")
    out.append("-- ---------------------------------------------------------------------")
    out.append("")
    tables = ", ".join(_table(n) for n in COLLECTIONS)
    out.append("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %s;" % ", ".join(REVOKE_FROM_ANON))
    out.append("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %s;" % ", ".join(REVOKE_FROM_ANON))
    out.append("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %s;"
               % ", ".join(REVOKE_FROM_ANON))
    out.append("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %s;"
               % ", ".join(REVOKE_FROM_ANON))
    out.append("")
    out.append("-- Row level security stays OFF on purpose. The backend authenticates every")
    out.append("-- request itself (get_current_user in server.py) and connects as `postgres`,")
    out.append("-- which bypasses RLS, so enabling it would add no protection while making every")
    out.append("-- query look as though it were filtered when it is not.")
    out.append("")
    out.append("GRANT USAGE ON SCHEMA public TO %s;" % ", ".join(REVOKE_FROM_ANON))
    out.append("")
    out.append("-- Collected for reference: %d tables in schema public matching c_*." % len(tables))
    out.append("")
    out.append("-- ===========================================================================")
    out.append("-- Done. Verify with:")
    out.append("--   SELECT count(*) FROM information_schema.tables")
    out.append("--    WHERE table_schema = 'public' AND table_name LIKE 'c\\_%';")
    out.append("--   SELECT count(*) FROM information_schema.indexes")
    out.append("--    WHERE table_schema = 'public';")
    out.append("-- ===========================================================================")
    return "\n".join(out) + "\n"


def table_names() -> List[str]:
    return [_table(c) for c in COLLECTIONS]


def index_statements() -> List[str]:
    """Every index DDL, used by pgbootstrap to verify the schema landed."""
    stmts = [_create_unique_index_sql(Index(n, ["id"], unique=True, where=_U("id")))
             for n in UNIQUE_PUB_ID]
    stmts.extend(_create_index_sql(i) for i in INDEXES)
    return stmts


def split_statements(sql: str) -> List[str]:
    """Split a script into statements on top-level semicolons.

    A naive ``sql.split(';')`` breaks on a dollar-quoted body (``DO $$ ... $$``),
    so this tracks single quotes, double quotes, dollar quotes, ``--`` comments
    and ``/* */`` blocks.
    """
    out: List[str] = []
    buf: List[str] = []
    i = 0
    n = len(sql)
    dollar_tag = ""
    while i < n:
        ch = sql[i]
        if dollar_tag:
            if sql.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = ""
                continue
            buf.append(ch)
            i += 1
            continue
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            if j == -1:
                buf.append(sql[i:n])
                i = n
                break
            # The newline must survive, or the next line is swallowed by the comment.
            buf.append(sql[i: j + 1])
            i = j + 1
            continue
        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            buf.append(sql[i:j])
            i = j
            continue
        if ch == "$":
            m = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[i:])
            if m:
                dollar_tag = m.group(0)
                buf.append(dollar_tag)
                i += len(dollar_tag)
                continue
        if ch in ("'", '"'):
            j = i + 1
            while j < n:
                if sql[j] == ch:
                    if j + 1 < n and sql[j + 1] == ch:  # doubled, escaped
                        j += 2
                        continue
                    break
                if sql[j] == "\\":
                    j += 2
                    continue
                j += 1
            buf.append(sql[i: j + 1])
            i = j + 1
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    # A trailing comment block on its own is not an executable statement.
    return [s for s in out if _has_code(s)]


def _has_code(stmt: str) -> bool:
    """True when the chunk contains anything other than comments and whitespace."""
    without_comments = re.sub(r"--[^\n]*", "", stmt)
    without_comments = re.sub(r"/\*.*?\*/", "", without_comments, flags=re.S)
    return bool(without_comments.strip())


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else None
    sql = build_schema()
    if target:
        from pathlib import Path

        Path(target).write_text(sql, encoding="utf-8")
        print(f"wrote {target} ({len(sql)} bytes, {len(split_statements(sql))} statements)")
    else:
        sys.stdout.write(sql)