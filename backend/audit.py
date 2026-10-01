"""Audit trail for privileged changes.

Every write that a Super Admin or an administrator performs on master data --
brands, products, logos, users, roles, categories -- records who did it, what
they changed, and what the record looked like before and after.

Two properties matter more than the feature itself:

* **It never breaks the request.** A failed audit write must not roll back a
  successful business operation. Failures are logged and swallowed; an audit gap
  is bad, a lost brand edit is worse.
* **It stores a diff, not a snapshot dump.** Storing the whole previous document
  would make the collection grow quadratically with edit history and bury the
  answer to "what actually changed" in noise. Only fields whose value really
  differs are recorded, with the old and new values rendered as short strings so
  the audit viewer never has to re-fetch the record to be readable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

log = logging.getLogger("crm.audit")

# Actions, so the vocabulary is greppable and the UI can offer filters.
CREATE = "create"
UPDATE = "update"
DELETE = "delete"
ARCHIVE = "archive"
RESTORE = "restore"
UPLOAD = "upload"
REPLACE = "replace"
REMOVE = "remove"
DUPLICATE = "duplicate"
STATUS_CHANGE = "status_change"
LOGIN = "login"

# Modules.
BRANDS = "brands"
PRODUCTS = "products"
USERS = "users"
ROLES = "roles"
CATEGORIES = "categories"
MEDIA = "media"
SYSTEM = "system"

# Fields rendered as text rather than JSON in the audit viewer, and truncated so
# one fat field cannot dominate the entry.
_TEXTY = {
    "description", "long_description", "short_description", "technical_specifications",
    "specifications", "features", "tags", "product_images", "gallery", "data",
    "permissions", "allowed_brands", "downloads",
}
_MAX_TEXT = 240


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def render(value: Any) -> Any:
    """A short, human-readable form of a value for the audit trail."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        v = value.strip()
        return v[:_MAX_TEXT] + ("…" if len(v) > _MAX_TEXT else "")
    if isinstance(value, (list, tuple)):
        items = [render(v) for v in list(value)[:12]]
        text = ", ".join("" if i is None else str(i) for i in items)
        more = "" if len(value) <= 12 else f" +{len(value) - 12} more"
        return (text + more)[:_MAX_TEXT]
    if isinstance(value, dict):
        keys = list(value)[:12]
        text = ", ".join(f"{k}={render(value[k])}" for k in keys)
        more = "" if len(value) <= 12 else f" +{len(value) - 12} more"
        return (text + more)[:_MAX_TEXT]
    return str(value)[:_MAX_TEXT]


def diff(before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]],
         fields: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """Field-level changes between two documents.

    ``fields`` restricts the comparison, which keeps an audit entry focused on
    what the operation was actually about instead of every incidental key.
    """
    before = before or {}
    after = after or {}
    names = list(fields) if fields is not None else sorted(set(before) | set(after))
    out: List[Dict[str, Any]] = []
    for name in names:
        old = before.get(name)
        new = after.get(name)
        if old == new:
            continue
        out.append({
            "field": name,
            "before": render(old),
            "after": render(new),
            # A field the previous record did not have at all is reported as
            # "added", which reads correctly in the viewer, whereas a literal
            # null before is indistinguishable from an explicit null.
            "kind": "added" if name not in before else ("removed" if name not in after else "changed"),
        })
    return out


def summarise(changes: List[Dict[str, Any]]) -> str:
    """One line describing what changed, e.g. ``Brand: Old Brand -> DiGiCo``."""
    if not changes:
        return ""
    parts = []
    for c in changes[:3]:
        label = c["field"].replace("_", " ").capitalize()
        parts.append(f"{label}: {c['before']} -> {c['after']}")
    if len(changes) > 3:
        parts.append(f"+{len(changes) - 3} more")
    return "; ".join(parts)


async def record(db, *, actor: Optional[dict], action: str, module: str,
                 record_type: Optional[str] = None, record_id: Optional[str] = None,
                 record_label: Optional[str] = None,
                 changes: Optional[List[Dict[str, Any]]] = None,
                 summary: Optional[str] = None,
                 meta: Optional[dict] = None) -> Optional[dict]:
    """Append one audit entry. Never raises."""
    try:
        changes = changes or []
        entry = {
            "id": __import__("uuid").uuid4().hex,
            "action": action,
            "module": module,
            "record_type": record_type or module.rstrip("s"),
            "record_id": record_id,
            "record_label": record_label,
            "actor_id": (actor or {}).get("id"),
            "actor_name": (actor or {}).get("name") or (actor or {}).get("email") or "system",
            "actor_role": (actor or {}).get("role") or "system",
            "changes": changes,
            "summary": summary if summary is not None else summarise(changes),
            "created_at": _now(),
        }
        if meta:
            entry["meta"] = meta
        await db.audit_logs.insert_one(dict(entry))
        return entry
    except Exception:  # noqa: BLE001 - an audit gap must not fail the operation
        log.exception("audit write failed for %s/%s", module, action)
        return None


async def record_change(db, *, actor, action: str, module: str, record_type: str,
                        record_id: str, record_label: Optional[str],
                        before: Optional[dict], after: Optional[dict],
                        fields: Optional[Iterable[str]] = None,
                        meta: Optional[dict] = None) -> Optional[dict]:
    """Convenience wrapper: diff two documents and record the result."""
    changes = diff(before, after, fields)
    if action == UPDATE and not changes:
        # Nothing actually changed. Recording a no-op edit makes the trail
        # useless for answering "who touched this and what did they do".
        return None
    return await record(
        db, actor=actor, action=action, module=module, record_type=record_type,
        record_id=record_id, record_label=record_label, changes=changes, meta=meta,
    )