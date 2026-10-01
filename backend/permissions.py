"""Role and permission registry.

Authorisation used to be scattered ``role == "admin"`` string comparisons, one per
endpoint. That cannot express "a Super Admin has no restriction anywhere" without
either editing every endpoint or trusting the UI, so this module is the single
place that answers three questions:

* what modules exist (``MODULES``),
* what a given role may do (``role_permissions``),
* whether a concrete user holds a permission (``has_permission``).

Design rules:

1. **Super Admin is decided by role name, not by permissions.** A Super Admin can
   always edit the role table, so a permission check driven by the role table
   would let them lock themselves out. ``is_super_admin`` therefore short-circuits
   every check, and that is what makes "no normal admin restriction applies"
   true by construction rather than by remembering to add an exception.
2. **Deny by default.** A role that is not in this registry and has no ``roles``
   document gets no permissions. An unknown role is never treated as permissive.
3. **Legacy roles keep working.** The pre-existing role documents in Mongo carry
   coarse permission names ("all", "crm", "settings", "team", ...) that were only
   ever consulted by ``require_admin``. Those are still honoured here, and "all"
   still means full access, so no existing user loses access on upgrade.

The module holds data and pure helpers only -- it never imports ``server``, so
there is no import cycle and it can be unit tested on its own.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

# The permission level requested for the Super Admin role.
FULL_ACCESS = "all"

SUPER_ADMIN_ROLE_NAME = "superadmin"

# Kept identical to the previous ``ADMIN_ROLE_NAMES`` in server.py. Moved here so
# there is one definition; server.py imports it rather than redefining it.
ADMIN_ROLE_NAMES = {"admin", "superadmin", "management"}

# Roles that may administer the system without being the Super Admin. They keep
# exactly the access they had before this module existed.
ADMIN_PERMISSION_ALIASES = {"settings", "all", FULL_ACCESS}

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------
# ``actions`` is the set of verbs a module supports. ``manage`` always implies
# ``view``: a caller who can change a record can certainly list it.
MODULES: Dict[str, Dict[str, Any]] = {
    "users":      {"label": "Users",            "actions": ("view", "manage")},
    "admins":     {"label": "Admins",           "actions": ("view", "manage")},
    "brands":     {"label": "Brands",           "actions": ("view", "manage")},
    "products":   {"label": "Products",         "actions": ("view", "manage")},
    "categories": {"label": "Categories",       "actions": ("view", "manage")},
    "inventory":  {"label": "Inventory",        "actions": ("view", "manage")},
    "customers":  {"label": "Customers",        "actions": ("view", "manage")},
    "orders":     {"label": "Orders",           "actions": ("view", "manage")},
    "quotations": {"label": "Quotations",       "actions": ("view", "manage")},
    "invoices":   {"label": "Invoices",         "actions": ("view", "manage")},
    "reports":    {"label": "Reports",          "actions": ("view", "manage")},
    "settings":   {"label": "Settings",         "actions": ("view", "manage")},
    "media":      {"label": "Media / Logos",    "actions": ("view", "manage")},
    "system":     {"label": "System Management", "actions": ("view", "manage")},
}

MODULE_KEYS: List[str] = list(MODULES)


def permission_name(module: str, action: str = "manage") -> str:
    return f"{module}.{action}"


def all_permission_names() -> List[str]:
    return [permission_name(key, action)
            for key, spec in MODULES.items()
            for action in spec["actions"]]


# ---------------------------------------------------------------------------
# Built-in defaults, used when the ``roles`` collection has no document for a role
# (a role created before this registry existed, or a role removed by hand).
# ---------------------------------------------------------------------------
DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    SUPER_ADMIN_ROLE_NAME: {"all", "*"},
    "admin": {"all", "*"},
    "management": {"all", "*"},
    "sales": {
        "customers.view", "quotations.view", "quotations.manage",
        "products.view", "categories.view", "leads.view", "leads.manage",
    },
    "marketing": {"customers.view", "reports.view"},
    "accounts": {"invoices.view", "invoices.manage", "orders.view", "reports.view"},
    "logistics": {"inventory.view", "inventory.manage", "products.view"},
    "service": {"inventory.view", "customers.view"},
    "projects": {"projects.view", "projects.manage", "quotations.view"},
    "design": {"projects.view"},
    "staff": {"customers.view"},
    "warehouse": {"inventory.view", "inventory.manage", "products.view", "products.manage"},
}


def _grant_implies(granted: str, module: str, action: str) -> bool:
    """Does a single granted permission satisfy the requested one?

    Coarse legacy names ("products", "crm", "team", ...) are resolved to *view*
    only. They predate this registry and used to be checked by ``require_admin``
    alone, so nothing ever distinguished reading a module from editing it. Reading
    that old name as "manage everything in this module" would hand the sales role
    product creation the moment these checks went live, which is exactly the
    privilege escalation the registry exists to prevent.
    """
    g = (granted or "").strip()
    if g in (FULL_ACCESS, "*"):
        return True
    if g == permission_name(module, action):
        return True
    # "manage" implies "view" so a role granted only editing still reads.
    if action == "view" and g == permission_name(module, "manage"):
        return True
    # A coarse legacy grant ("brands") covers reading that module.
    if g == module:
        return action == "view"
    # Legacy coarse aliases mapped onto modules they were standing in for, also
    # read-only. See the docstring for why these are not treated as "manage".
    legacy_read_only = {
        "crm": ("leads", "customers", "products", "categories"),
        "catalog": ("products", "categories"),
        "team": ("users", "admins"),
        "accounting": ("invoices", "orders"),
    }
    if module in legacy_read_only.get(g, ()):
        return action == "view"
    return False


def has_permission(granted: Iterable[str], module: str, action: str = "manage") -> bool:
    """Whether ``granted`` satisfies ``module.action``."""
    if module not in MODULES:
        # An unknown module is never quietly allowed.
        return False
    return any(_grant_implies(g, module, action) for g in (granted or ()))


def role_grants(role_doc: Optional[dict]) -> Set[str]:
    """Permission names on a ``roles`` document, normalised to strings."""
    if not role_doc:
        return set()
    return {str(p) for p in (role_doc.get("permissions") or []) if p}


async def role_permissions(db, role: Optional[str]) -> Set[str]:
    """Effective permissions for a role name.

    The ``roles`` collection wins when it has a document, because that is what an
    administrator edits. Built-in defaults fill any gap so a missing document
    degrades to the role's historical access rather than to nothing.
    """
    name = (role or "").strip()
    if not name:
        return set()
    if name.lower() == SUPER_ADMIN_ROLE_NAME:
        return {FULL_ACCESS, "*"}
    doc = await db.roles.find_one({"name": name}, {"_id": 0, "permissions": 1})
    grants = role_grants(doc) | DEFAULT_ROLE_PERMISSIONS.get(name.lower(), set())
    return grants


async def user_permissions(db, user: dict) -> Set[str]:
    return await role_permissions(db, (user or {}).get("role"))


def is_super_admin(user: Optional[dict]) -> bool:
    return ((user or {}).get("role") or "").strip().lower() == SUPER_ADMIN_ROLE_NAME


def is_admin_user(user: Optional[dict]) -> bool:
    """Admin-equivalent: Super Admin, admin, or management.

    Distinct from :func:`is_super_admin` on purpose. Super Admin has no
    restrictions; an ordinary admin still passes the permission checks below and
    is only guaranteed the legacy access. Conflating the two is how ordinary
    admins quietly acquire Super Admin powers.
    """
    return ((user or {}).get("role") or "").strip().lower() in ADMIN_ROLE_NAMES


async def user_can(db, user: dict, module: str, action: str = "manage") -> bool:
    """The authoritative check. Super Admin is always allowed."""
    if not user:
        return False
    if is_super_admin(user):
        return True
    return has_permission(await user_permissions(db, user), module, action)


def super_admin_role_document() -> dict:
    """The canonical ``roles`` document for the Super Admin role.

    Seeded by a migration and re-applied idempotently at startup. ``permissions``
    carries both the wildcard and the expanded module list so the UI can render a
    truthful "everything" without special-casing the role name.
    """
    return {
        "id": "role-superadmin",
        "name": SUPER_ADMIN_ROLE_NAME,
        "display_name": "Super Admin",
        "description": (
            "Unrestricted control over every module: users, admins, brands, products, "
            "categories, inventory, customers, orders, quotations, invoices, reports, "
            "settings, media and system management. Bypasses all normal admin restrictions."
        ),
        "permission_level": FULL_ACCESS,
        "permissions": sorted({FULL_ACCESS, "*"} | set(all_permission_names())),
        "is_system": True,
    }