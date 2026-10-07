"""Offline checks for pgdb.py: filter compilation, projections, update operators.

These need no database. They pin the translation rules that the endpoints depend
on, so a regression shows up here rather than as a 500 in production.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pgdb import (  # noqa: E402
    _apply_projection,
    _apply_update,
    _Translator,
    _Params,
)

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}\n     got:  {got!r}\n     want: {want!r}")


def sql_for(flt):
    p = _Params()
    out = _Translator(p).compile(flt)
    return out, p.values


def has(sql, fragment):
    return fragment in sql


# ---------------------------------------------------------------- equality
s, v = sql_for({"email": "a@b.com"})
check("equality compiles a text compare", has(s, "#>> '{email}' = $1"), True)
check("equality binds the scalar first", v[0], "a@b.com")
# A scalar query also matches an array holding it, so a second param is bound.
check("equality binds the array form too", v[1], '["a@b.com"]')

s, v = sql_for({"stage": {"$in": ["new", "assigned"]}})
check("$in expands to OR", has(s, " OR "), True)
check("$in binds one param per candidate", [x for x in v if x == "new"], ["new"])
check("$in binds both candidates", [x for x in v if x == "assigned"], ["assigned"])

s, _ = sql_for({"stage": {"$nin": ["lost_lead"]}})
check("$nin negates", has(s, "NOT ("), True)

s, _ = sql_for({"total": {"$gt": 100}})
check("$gt guards jsonb_typeof", has(s, "jsonb_typeof"), True)
check("$gt uses numeric", has(s, "::numeric >"), True)

s, _ = sql_for({"name": {"$regex": "acme", "$options": "i"}})
check("$regex case-insensitive", has(s, "~*"), True)

s, _ = sql_for({"name": {"$regex": "acme"}})
check("$regex without options is case-sensitive", has(s, " ~ $"), True)

s, _ = sql_for({"interested_in": {"$exists": True}})
check("$exists true uses IS NOT NULL", has(s, "IS NOT NULL"), True)

s, _ = sql_for({"interested_in": {"$exists": False}})
check("$exists false negates", has(s, "NOT ("), True)

# --------------------------------------------------------------- combinators
s, _ = sql_for({"$or": [{"slug": "x"}, {"name": "y"}]})
check("$or joins with OR", has(s, " OR "), True)

s, _ = sql_for({"$and": [{"a": 1}, {"b": 2}]})
check("$and joins with AND", has(s, " AND "), True)

s, _ = sql_for({"assigned_to": {"$ne": None}})
check("$ne against null", has(s, "NOT ("), True)

# a real query shape from the codebase: search across several fields
s, v = sql_for(
    {"$or": [{"name": {"$regex": "acme", "$options": "i"}},
             {"brand_category": {"$regex": "acme", "$options": "i"}},
             {"country": {"$regex": "acme", "$options": "i"}}]}
)
check("search $or binds the pattern three times", v, ["acme", "acme", "acme"])

# empty filter must not restrict
check("empty filter is permissive", sql_for({})[0], "true")
check("None filter is permissive", sql_for(None)[0], "true")

# nested path
s, v = sql_for({"quotation.items.product": "K2"})
check("dotted path rendered", has(s, "'{quotation,items,product}'"), True)

# unknown operator is ignored rather than raising
s, _ = sql_for({"weird": {"$nope": 1}})
check("unknown operator ignored", s, "true")

# ---------------------------------------------------------------- projection
doc = {"_id": "a1", "id": "u1", "name": "Admin", "password_hash": "x", "stage": "new"}
check("exclude _id only", _apply_projection(doc, {"_id": 0}),
      {"id": "u1", "name": "Admin", "password_hash": "x", "stage": "new"})
check("include list", _apply_projection(doc, {"_id": 0, "id": 1}),
      {"id": "u1"})
check("include several", _apply_projection(doc, {"_id": 0, "id": 1, "name": 1}),
      {"id": "u1", "name": "Admin"})
check("exclude a field", _apply_projection(doc, {"_id": 0, "password_hash": 0}),
      {"id": "u1", "name": "Admin", "stage": "new"})
check("no projection returns all", _apply_projection(doc, None), doc)
check("include keeps _id by default",
      _apply_projection(doc, {"name": 1}), {"_id": "a1", "name": "Admin"})

# ------------------------------------------------------------------- updates
d = {"_id": "1", "stage": "new", "count": 0, "tags": ["a"], "notes": None}
_apply_update(d, {"$set": {"stage": "qualified"}})
check("$set", d["stage"], "qualified")

_apply_update(d, {"$inc": {"count": 1}})
check("$inc", d["count"], 1)

_apply_update(d, {"$unset": {"notes": ""}})
check("$unset", "notes" in d, False)

_apply_update(d, {"$push": {"tags": "b"}})
check("$push", d["tags"], ["a", "b"])

_apply_update(d, {"$addToSet": {"tags": "b"}})
check("$addToSet does not duplicate", d["tags"], ["a", "b"])

_apply_update(d, {"$addToSet": {"tags": "c"}})
check("$addToSet adds new", d["tags"], ["a", "b", "c"])

_apply_update(d, {"$pull": {"tags": "a"}})
check("$pull", d["tags"], ["b", "c"])

d2 = {"_id": "2", "a": {"b": 1}}
_apply_update(d2, {"$set": {"a.c": 2}})
check("nested $set", d2["a"], {"b": 1, "c": 2})

d3 = {"_id": "3", "x": 1}
# A replacement returns a new document and carries the original _id across, the
# way MongoDB's replaceOne does. It does not mutate in place.
replaced = _apply_update(d3, {"x": 2})
check("replacement document", replaced, {"_id": "3", "x": 2})
check("replacement keeps _id", replaced.get("_id"), "3")

# ------------------------------------------------------------------ reporting
if failures:
    print(f"FAILED ({len(failures)}):\n")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)
print("all pgdb translation checks passed")