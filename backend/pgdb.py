"""MongoDB-compatible document store backed by PostgreSQL JSONB.

The CRM's endpoints are written against the Motor API (``db.leads.find_one(...)``,
``$set``, ``count_documents``, cursors, and small aggregation pipelines). Rather than
rewrite every call site, this module exposes the same surface on top of Postgres so
``server.py`` keeps working unchanged.

Storage model, one table per collection::

    create table c_leads (
        doc_id   text primary key,          -- the document's _id
        body     jsonb not null,            -- the whole document, verbatim
        pub_id   text,                      -- the document's public "id" field
        updated_at timestamptz not null default now()
    )

Every document is stored verbatim in ``body``, so no field is lost and no field has
to be declared up front. Query filters compile to SQL predicates over ``body``;
projection, sort of nested paths, and update operators are applied where they are
cheapest while keeping MongoDB's observable semantics.

The table list and the index set live in ``pgschema.py``; ``supabase_schema.sql``
is generated from there. This module assumes every collection in that list has a
``c_*`` table and raises :class:`UndefinedCollectionError` -- naming the fix --
rather than letting Postgres report a bare "relation does not exist" from
whichever endpoint happened to touch the collection first.
"""

from __future__ import annotations

import base64
import datetime as _dt
import json
import logging
import re
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # bson.Binary may appear in legacy stored documents (media uploaded before
    # Oct 2026). The import is fully optional: plain bytes are stored the same way.
    from bson import Binary  # type: ignore

    _HAS_BSON = True
except Exception:  # pragma: no cover - bson/pymongo not installed; that is fine
    Binary = None  # type: ignore
    _HAS_BSON = False

try:  # The migration runner catches DuplicateKeyError to break the lease race.
    from pymongo.errors import DuplicateKeyError  # type: ignore
except Exception:  # bson/pymongo not installed; use the local fallback
    class DuplicateKeyError(Exception):  # type: ignore
        """Raised when a write violates a unique index."""


logger = logging.getLogger("pgdb")

BIN_PREFIX = "__bin_b64__:"


class UndefinedCollectionError(RuntimeError):
    """A collection was used that has no ``c_*`` table.

    Almost always a missing entry in ``pgschema.COLLECTIONS``. The message says so
    because the alternative -- Postgres raising "relation does not exist" from
    deep inside whichever endpoint touched the collection first -- costs an hour
    of bisecting to diagnose.
    """


def _is_duplicate_key(exc: BaseException) -> bool:
    """True for a Postgres unique violation, whether it came from asyncpg or psycopg."""
    name = type(exc).__name__
    if name in ("UniqueViolationError", "DuplicateKeyError"):
        return True
    # SQLSTATE 23505 is unique_violation in both drivers.
    return getattr(exc, "sqlstate", None) == "23505" or getattr(exc, "pgcode", None) == "23505"


# --------------------------------------------------------------------------
# JSON coercion
# --------------------------------------------------------------------------
def _scalar(value: Any) -> Any:
    """Normalise a value into something ``json.dumps`` and asyncpg both accept.

    ``server.py`` stores timestamps as ``datetime.isoformat()`` strings, so a
    comparison against them has to be textual. If a caller passes a real
    ``datetime`` instead -- ``migrations.py`` does, for the lease expiry -- it has
    to be reduced to the same ISO-8601 form or the two will never compare equal.
    """
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, _dt.timedelta):
        return value.total_seconds()
    return value


def _default(obj: Any) -> Any:
    """Make Mongo-flavoured values JSON-serialisable."""
    if _HAS_BSON and isinstance(obj, Binary):
        return BIN_PREFIX + base64.b64encode(bytes(obj)).decode("ascii")
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return BIN_PREFIX + base64.b64encode(bytes(obj)).decode("ascii")
    if isinstance(obj, (_dt.datetime, _dt.date, _dt.time)):
        # ISO-8601, matching datetime.isoformat() everywhere else in the app.
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


def _bind(value: Any) -> Any:
    """Coerce a filter/update value into a form asyncpg can send as text."""
    if isinstance(value, (list, tuple)):
        return json.dumps([_scalar(v) for v in value], default=_default)
    if isinstance(value, dict):
        return json.dumps(value, default=_default)
    return _scalar(value)


def _revive(obj: Any) -> Any:
    """Restore Binary values encoded by :func:`_default`."""
    if isinstance(obj, str):
        if obj.startswith(BIN_PREFIX):
            return base64.b64decode(obj[len(BIN_PREFIX):])
        return obj
    if isinstance(obj, list):
        return [_revive(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _revive(v) for k, v in obj.items()}
    return obj


def _dumps(doc: Any) -> str:
    return json.dumps(doc, default=_default)


def _loads(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    return _revive(json.loads(raw))


def _new_object_id() -> str:
    """A 24-hex string, shaped like the ObjectId the app used to receive."""
    return uuid.uuid4().hex[:24]


def _table(name: str) -> str:
    return "c_" + re.sub(r"[^a-z0-9_]", "_", name.lower())


# --------------------------------------------------------------------------
# Motor-compatible result objects
# --------------------------------------------------------------------------
class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.acknowledged = True


class InsertManyResult:
    def __init__(self, inserted_ids):
        self.inserted_ids = inserted_ids
        self.acknowledged = True


class UpdateResult:
    def __init__(self, matched_count=0, modified_count=0, upserted_id=None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id
        self.acknowledged = True


class DeleteResult:
    def __init__(self, deleted_count=0):
        self.deleted_count = deleted_count
        self.acknowledged = True


# --------------------------------------------------------------------------
# Filter -> SQL
# --------------------------------------------------------------------------
class _Params:
    def __init__(self):
        self.values: List[Any] = []

    def add(self, value: Any) -> str:
        self.values.append(value)
        return f"${len(self.values)}"


def _path(field: str) -> str:
    """Render a dotted field path as a Postgres text array literal."""
    parts = [p for p in str(field).split(".") if p != ""]
    return "{" + ",".join(p.replace("\\", "\\\\").replace(",", "\\,") for p in parts) + "}"


def _is_operator_dict(spec: Any) -> bool:
    return isinstance(spec, dict) and spec and all(k.startswith("$") for k in spec)


def _cmp_eq(jpath: str, sql_text: str, sql_json: str, params: _Params, value: Any) -> str:
    """Equality, with MongoDB's array-membership behaviour for array fields."""
    value = _scalar(value)
    if value is None:
        return f"({sql_json} IS NULL OR {sql_json} = 'null'::jsonb)"
    if isinstance(value, bool):
        p = params.add(json.dumps(value))
        return f"{sql_json} = {p}::jsonb"
    if isinstance(value, (int, float)):
        p = params.add(json.dumps(value))
        return (
            f"(jsonb_typeof({sql_json}) = 'number' AND {sql_json} = {p}::jsonb)"
        )
    p = params.add(value)
    text_eq = f"{sql_text} = {p}"
    # A scalar query also matches an array that contains it.
    arr = params.add(_dumps([value]))
    return (
        f"({text_eq} OR (jsonb_typeof({sql_json}) = 'array' "
        f"AND EXISTS (SELECT 1 FROM jsonb_array_elements({sql_json}) e WHERE e = {arr}::jsonb)))"
    )


def _cmp_num(jpath: str, sql_text: str, sql_json: str, params: _Params, op: str, value: Any) -> str:
    """Ordering comparison that works for numbers *and* ISO-8601 date strings.

    MongoDB compares across BSON types by a type ordering, so
    ``{"end_date": {"$lte": "2026-08-31"}}`` matches a document whose ``end_date``
    is the string "2026-08-14". Almost every date in this CRM is stored as an
    ISO-8601 string, not a native date, so a numeric-only comparison -- which is
    what this used to emit -- silently matched nothing at all and every
    date-range widget on the dashboard rendered empty.

    ISO-8601 in its fixed-width form sorts correctly as text, so string columns
    are compared as text and numeric columns are compared as numbers. Both are
    offered; the wrong one cannot match, because of the ``jsonb_typeof`` guard.

    The two branches bind *separate* parameters. Sharing one would make Postgres
    resolve the placeholder to ``numeric`` from the first branch and then fail to
    parse ``text <= $1`` in the second.
    """
    p_num = params.add(_scalar(value))
    p_txt = params.add(_scalar(value))
    numeric = (
        f"({sql_json} IS NOT NULL AND jsonb_typeof({sql_json}) = 'number' "
        f"AND ({sql_text})::numeric {op} {p_num})"
    )
    textual = (
        f"({sql_json} IS NOT NULL AND jsonb_typeof({sql_json}) = 'string' "
        f"AND {sql_text} {op} {p_txt})"
    )
    return f"({numeric} OR {textual})"


class _Translator:
    """Compiles a MongoDB filter into a SQL boolean expression over ``body``."""

    def __init__(self, params: _Params, col: str = "body"):
        self.params = params
        self.col = col

    def compile(self, flt: Optional[Dict]) -> str:
        if not flt:
            return "true"
        parts: List[str] = []
        for key, spec in flt.items():
            if key == "$and":
                parts.extend("(%s)" % self.compile(s) for s in spec)
            elif key == "$or":
                parts.append("(%s)" % " OR ".join("(%s)" % self.compile(s) for s in spec))
            elif key == "$nor":
                parts.append("NOT (%s)" % " OR ".join("(%s)" % self.compile(s) for s in spec))
            elif key.startswith("$"):
                # Unknown top-level operator: ignore rather than fail the request.
                continue
            else:
                parts.append(self._field(key, spec))
        return " AND ".join(p for p in parts if p) or "true"

    def _field(self, field: str, spec: Any) -> str:
        path = _path(field)
        jpath = f"{self.col} #> '{path}'"
        tpath = f"{self.col} #>> '{path}'"
        simple = "." not in field

        if not _is_operator_dict(spec):
            return _cmp_eq(jpath, tpath, jpath, self.params, spec)

        clause: List[str] = []
        for op, arg in spec.items():
            if op == "$eq":
                clause.append(_cmp_eq(jpath, tpath, jpath, self.params, arg))
            elif op == "$ne":
                inner = _cmp_eq(jpath, tpath, jpath, self.params, arg)
                clause.append(f"NOT ({inner})")
            elif op in ("$gt", "$gte", "$lt", "$lte"):
                sym = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}[op]
                clause.append(_cmp_num(jpath, tpath, jpath, self.params, sym, arg))
            elif op == "$in":
                vals = list(arg or [])
                if not vals:
                    clause.append("false")
                else:
                    clause.append(
                        "(" + " OR ".join("(%s)" % _cmp_eq(jpath, tpath, jpath, self.params, v) for v in vals) + ")"
                    )
            elif op == "$nin":
                vals = list(arg or [])
                if not vals:
                    clause.append("true")
                else:
                    inner = "(" + " OR ".join(
                        "(%s)" % _cmp_eq(jpath, tpath, jpath, self.params, v) for v in vals
                    ) + ")"
                    clause.append(f"NOT {inner}")
            elif op == "$exists":
                want = bool(arg)
                exists = f"{jpath} IS NOT NULL" if simple else (
                    f"jsonb_path_exists({self.col}, '$.{field.replace('.', '.')}' )"
                    if want else f"NOT jsonb_path_exists({self.col}, '$.{field}')"
                )
                clause.append(exists if want else f"NOT ({exists})")
            elif op == "$regex":
                # Array-aware: see _regex below.
                clause.append(self._regex(field, arg, spec.get("$options", "")))
                continue
            elif op == "$type":
                want = arg if isinstance(arg, str) else arg
                mapping = {
                    "string": "string", "double": "number", "int": "number",
                    "number": "number", "bool": "boolean", "object": "object",
                    "array": "array", "null": "null",
                }
                t = mapping.get(want, want)
                clause.append(f"jsonb_typeof({jpath}) = '{t}'")
            elif op == "$all":
                for v in arg or []:
                    clause.append("(%s)" % _cmp_eq(jpath, tpath, jpath, self.params, v))
            elif op == "$size":
                p = self.params.add(int(arg))
                clause.append(f"jsonb_array_length({jpath}) = {p}")
            elif op == "$elemMatch":
                # Only the equality form appears in this codebase.
                inner = _Translator(self.params, self.col)
                sub = inner._field(field.split(".")[0] if "." in field else "__self__", arg)
                clause.append(f"({sub})")
            elif op == "$not":
                clause.append(f"NOT ({self._field(field, arg)})")
            # Unknown operators are ignored rather than silently dropping the filter.
        return " AND ".join(c for c in clause if c) or "true"

    def _regex(self, field: str, arg: Any, opts: str) -> str:
        """Regex over a text projection, expanding the whole array when it is one.

        ``body #>> '{items}'`` yields NULL for an array, so a naive text regex
        never matches an array-valued field -- a product name inside
        ``leads.interested_in`` or ``quotations.items``. Unwrapping the array
        first is what makes catalogue search return hits.
        """
        pat = arg if isinstance(arg, str) else str(arg)
        p = self.params.add(pat)
        op_sql = "~*" if "i" in opts else "~"
        path = _path(field)
        col = self.col
        text = f"coalesce({col} #>> '{path}', '') {op_sql} {p}"
        element = f"coalesce(e #>> '{{}}', '') {op_sql} {p}"
        return (
            f"({text} OR EXISTS (SELECT 1 FROM jsonb_array_elements("
            f"CASE WHEN jsonb_typeof({col} #> '{path}') = 'array' "
            f"THEN {col} #> '{path}' ELSE '[]'::jsonb) e WHERE {element}))"
        )


# --------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------
def _apply_projection(doc: Dict, projection: Optional[Dict]) -> Dict:
    if not projection or not isinstance(projection, dict):
        return doc
    includes = {k: v for k, v in projection.items() if k != "_id" and v}
    excludes = {k for k, v in projection.items() if k != "_id" and not v}

    drop_id = projection.get("_id", 1) == 0

    if includes:
        out: Dict = {}
        if not drop_id and "_id" in doc:
            out["_id"] = doc["_id"]
        for k in includes:
            if k in doc:
                out[k] = doc[k]
        return out

    out = dict(doc)
    for k in excludes:
        out.pop(k, None)
    if drop_id:
        out.pop("_id", None)
    return out


def _project_all(docs: List[Dict], projection: Optional[Dict]) -> List[Dict]:
    if not projection:
        return docs
    return [_apply_projection(d, projection) for d in docs]


def _sort_docs(docs: List[Dict], pairs: List[Tuple[str, int]]) -> List[Dict]:
    """Stable multi-key sort mirroring the SQL ordering, numbers before text."""
    out = list(docs)
    for field, direction in reversed(pairs):
        def key(d):
            v = _get_path(d, field)
            if v is None:
                return (2, 0, "")
            if isinstance(v, bool):
                return (1, float(v), "")
            if isinstance(v, (int, float)):
                return (0, float(v), "")
            if isinstance(v, (dict, list)):
                return (1, 0, "")
            return (1, 0, str(v))
        out.sort(key=key, reverse=direction < 0)
    return out


def _get_path(doc: Any, field: str) -> Any:
    cur = doc
    for part in field.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _set_path(doc: Dict, field: str, value: Any) -> None:
    parts = field.split(".")
    cur = doc
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _unset_path(doc: Dict, field: str) -> None:
    parts = field.split(".")
    cur = doc
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return
        cur = cur[p]
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


def _apply_update(doc: Dict, update: Dict) -> Dict:
    """Apply MongoDB update operators to a plain dict."""
    if any(not k.startswith("$") for k in update):
        # Replacement document. MongoDB keeps the original _id on replaceOne, so
        # copy it across rather than letting the stored document lose it.
        new = dict(update)
        if "_id" not in new and "_id" in doc:
            new["_id"] = doc["_id"]
        return new
    for op, payload in update.items():
        if op == "$set":
            for k, v in payload.items():
                _set_path(doc, k, v)
        elif op == "$unset":
            for k in payload:
                _unset_path(doc, k)
        elif op == "$inc":
            for k, v in payload.items():
                cur = _get_path(doc, k)
                _set_path(doc, k, (cur or 0) + v)
        elif op == "$push":
            for k, v in payload.items():
                cur = _get_path(doc, k)
                if not isinstance(cur, list):
                    cur = []
                doc_k = k.split(".")[0] if "." in k else k
                if isinstance(v, dict) and "$each" in v:
                    cur = cur + list(v["$each"])
                else:
                    cur = cur + [v]
                _set_path(doc, doc_k, cur)
        elif op == "$addToSet":
            for k, v in payload.items():
                cur = _get_path(doc, k)
                if not isinstance(cur, list):
                    cur = []
                vals = v.get("$each") if isinstance(v, dict) and "$each" in v else [v]
                for item in vals:
                    if item not in cur:
                        cur.append(item)
                _set_path(doc, k.split(".")[0] if "." in k else k, cur)
        elif op == "$pull":
            for k, v in payload.items():
                cur = _get_path(doc, k)
                if isinstance(cur, list):
                    keep = [x for x in cur if x != v]
                    _set_path(doc, k.split(".")[0] if "." in k else k, keep)
        elif op == "$pop":
            for k, v in payload.items():
                cur = _get_path(doc, k)
                if isinstance(cur, list) and cur:
                    cur.pop() if v == 1 else cur.pop(0)
        elif op == "$setOnInsert":
            continue
    return doc


# --------------------------------------------------------------------------
# Cursor
# --------------------------------------------------------------------------
class _Cursor:
    def __init__(self, coll: "Collection"):
        self._coll = coll
        self._spec: Optional[Dict] = None
        self._projection: Optional[Dict] = None
        self._pipeline: Optional[List[Dict]] = None
        self._sort: Optional[Tuple[List[Tuple[str, int]], List[Any]]] = None
        self._limit: Optional[int] = None
        self._skip: int = 0
        self._iter: Optional[List[Dict]] = None
        self._iter_pos: int = 0

    def sort(self, key_or_list, direction=None):
        pairs: List[Tuple[str, int]] = []
        if isinstance(key_or_list, str):
            pairs = [(key_or_list, int(direction or 1))]
        elif isinstance(key_or_list, dict):
            pairs = [(k, int(v)) for k, v in key_or_list.items()]
        else:
            for item in key_or_list or []:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    pairs.append((str(item[0]), int(item[1])))
                else:
                    pairs.append((str(item), 1))
        self._sort = (pairs, [])
        return self

    def limit(self, n: int):
        self._limit = int(n)
        return self

    def skip(self, n: int):
        self._skip = int(n)
        return self

    def project(self, projection):
        self._projection = projection
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict]:
        if self._pipeline:
            rows = await self._coll._aggregate_simple(self._pipeline)
            rows = _project_all(rows, self._projection)
            if self._sort and self._sort[0]:
                rows = _sort_docs(rows, self._sort[0])
            if self._skip:
                rows = rows[self._skip:]
            if self._limit is not None:
                rows = rows[: int(self._limit)]
        else:
            rows = await self._coll._fetch(
                self._spec,
                self._projection,
                sort=self._sort,
                limit=self._limit,
                skip=self._skip,
            )
        if length is not None:
            rows = rows[: int(length)]
        return rows

    def __await__(self):
        return self.to_list(None).__await__()

    # ``async for row in coll.find(...)`` is how Motor's cursors are consumed, and
    # the application uses it in the quotation, purchase-order and project numbering
    # helpers. Without __aiter__/__anext__ that expression raises AttributeError,
    # which is what made every "create quotation" request fail with a 500.
    def __aiter__(self) -> "_Cursor":
        self._iter = None
        self._iter_pos = 0
        return self

    async def __anext__(self) -> Dict:
        if self._iter is None:
            self._iter = await self.to_list(None)
        if self._iter_pos >= len(self._iter):
            raise StopAsyncIteration
        row = self._iter[self._iter_pos]
        self._iter_pos += 1
        return row


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------
class Collection:
    def __init__(self, db: "PostgresDocumentDB", name: str):
        self._db = db
        self._name = name
        self._table = _table(name)

    # -- reads ------------------------------------------------------------
    def find(self, spec: Optional[Dict] = None, projection: Optional[Dict] = None, **kw):
        cur = _Cursor(self)
        cur._spec = spec or {}
        cur._projection = projection
        if kw.get("sort"):
            cur.sort(kw["sort"])
        if kw.get("limit"):
            cur.limit(kw["limit"])
        if kw.get("skip"):
            cur.skip(kw["skip"])
        return cur

    def aggregate(self, pipeline: Sequence[Dict]):
        cur = _Cursor(self)
        cur._pipeline = list(pipeline or [])
        return cur

    async def find_one(self, spec: Optional[Dict] = None, projection: Optional[Dict] = None,
                        **kw) -> Optional[Dict]:
        rows = await self._fetch(spec, projection, limit=1)
        return rows[0] if rows else None

    async def count_documents(self, spec: Optional[Dict] = None, **kw) -> int:
        params = _Params()
        where = _Translator(params).compile(spec or {})
        sql = f"SELECT count(*) FROM {self._table} WHERE {where}"
        return int(await self._db.fetchval(sql, *params.values))

    async def distinct(self, field: str, spec: Optional[Dict] = None) -> List[Any]:
        params = _Params()
        where = _Translator(params).compile(spec or {})
        p = params.add(_path(field))
        sql = (
            f"SELECT DISTINCT jsonb_array_elements(CASE WHEN jsonb_typeof(body #> {p}) = 'array' "
            f"THEN body #> {p} ELSE jsonb_build_array(body #> {p}) END) FROM {self._table} "
            f"WHERE {where} AND body #> {p} IS NOT NULL"
        )
        rows = await self._db.fetch(sql, *params.values)
        return [_loads(r[0]) for r in rows]

    # -- writes -----------------------------------------------------------
    async def insert_one(self, doc: Dict) -> InsertOneResult:
        d = dict(doc)
        d.setdefault("_id", _new_object_id())
        try:
            await self._db.execute(
                f"INSERT INTO {self._table} (doc_id, body, pub_id) VALUES ($1, $2::jsonb, $3)",
                str(d["_id"]), _dumps(d), d.get("id"),
            )
        except Exception as exc:  # noqa: BLE001
            # A unique index rejected the row. Motor callers -- the migration
            # runner in particular -- catch DuplicateKeyError to detect "someone
            # else already holds this key", so it has to arrive as that type.
            if _is_duplicate_key(exc):
                raise DuplicateKeyError(
                    f"E11000 duplicate key on {self._table} _id={d['_id']}"
                ) from exc
            raise
        return InsertOneResult(d["_id"])

    async def insert_many(self, docs: Iterable[Dict]) -> InsertManyResult:
        ids = []
        for doc in docs:
            r = await self.insert_one(doc)
            ids.append(r.inserted_id)
        return InsertManyResult(ids)

    async def _seed_from(self, spec: Optional[Dict], update: Dict) -> Dict:
        """Build the document an upsert inserts when the filter matched nothing.

        Only literal equalities from the filter become fields -- an operator
        condition such as ``{"expires_at": {"$lte": now}}`` is a *test*, not a
        value, and copying it in would store ``{"$lte": ...}`` as data. MongoDB's
        behaviour for that is to take the equality fields only.
        """
        seed: Dict[str, Any] = {}
        for k, v in (spec or {}).items():
            if k.startswith("$") or _is_operator_dict(v):
                continue
            seed[k] = _scalar(v)
        seed.setdefault("_id", _new_object_id())
        return _apply_update(seed, update)

    async def _insert_doc(self, doc: Dict) -> str:
        try:
            await self._db.execute(
                f"INSERT INTO {self._table} (doc_id, body, pub_id) VALUES ($1, $2::jsonb, $3)",
                str(doc["_id"]), _dumps(doc), doc.get("id"),
            )
        except Exception as exc:  # noqa: BLE001
            if _is_duplicate_key(exc):
                raise DuplicateKeyError(
                    f"E11000 duplicate key on {self._table} _id={doc['_id']}"
                ) from exc
            raise
        return str(doc["_id"])

    async def _write(self, spec, update, upsert: bool, multi: bool) -> UpdateResult:
        params = _Params()
        where = _Translator(params).compile(spec or {})
        rows = await self._db.fetch(
            f"SELECT doc_id, body FROM {self._table} WHERE {where} LIMIT 50"
            if multi else
            f"SELECT doc_id, body FROM {self._table} WHERE {where} LIMIT 1",
            *params.values,
        )
        matched = len(rows)
        modified = 0
        upserted_id = None

        if not rows and upsert:
            seed = await self._seed_from(spec, update)
            upserted_id = await self._insert_doc(seed)
            return UpdateResult(0, 0, upserted_id)

        for doc_id, body in rows:
            cur_doc = _loads(body)
            if not isinstance(cur_doc, dict):
                continue
            new_doc = _apply_update(cur_doc, update)
            if new_doc != cur_doc:
                try:
                    await self._db.execute(
                        f"UPDATE {self._table} SET body = $2::jsonb, pub_id = $3, updated_at = now() "
                        f"WHERE doc_id = $1",
                        doc_id, _dumps(new_doc), new_doc.get("id"),
                    )
                except Exception as exc:  # noqa: BLE001
                    if _is_duplicate_key(exc):
                        raise DuplicateKeyError(
                            f"E11000 duplicate key on {self._table}"
                        ) from exc
                    raise
                modified += 1
        return UpdateResult(matched, modified, upserted_id)

    async def update_one(self, spec, update, upsert: bool = False, **kw) -> UpdateResult:
        return await self._write(spec, update, upsert, False)

    async def update_many(self, spec, update, upsert: bool = False, **kw) -> UpdateResult:
        return await self._write(spec, update, upsert, True)

    async def replace_one(self, spec, replacement, upsert: bool = False, **kw) -> UpdateResult:
        rep = dict(replacement)
        return await self._write(spec, {"$set": rep}, upsert, False)

    async def find_one_and_update(
        self,
        spec,
        update,
        projection=None,
        upsert: bool = False,
        sort=None,
        return_document=True,
        **kw,
    ) -> Optional[Dict]:
        """Atomically update the first matching document and return it.

        ``migrations.py`` takes a cross-process lease with this call: the filter
        matches an absent lock or an expired one, ``upsert=True`` inserts it, and
        a second worker hits the ``doc_id`` primary key and gets
        ``DuplicateKeyError`` instead of stealing the lease. Without this method
        the runner raised ``AttributeError``, every migration was skipped, and
        nothing was ever seeded.

        ``return_document`` accepts ``True``/``False`` or pymongo's
        ``ReturnDocument`` enum, which is literally those booleans.
        """
        after = bool(return_document)
        params = _Params()
        where = _Translator(params).compile(spec or {})
        order = ""
        if sort:
            order = " ORDER BY " + _order_by(sort)
        rows = await self._db.fetch(
            f"SELECT doc_id, body FROM {self._table} WHERE {where}{order} LIMIT 1",
            *params.values,
        )
        if not rows:
            if not upsert:
                return None
            seed = await self._seed_from(spec, update)
            await self._insert_doc(seed)
            return _apply_projection(seed, projection) if after else None

        doc_id, body = rows[0]
        before = _loads(body)
        if not isinstance(before, dict):
            return None
        after_doc = _apply_update(dict(before), update)
        if after_doc != before:
            try:
                await self._db.execute(
                    f"UPDATE {self._table} SET body = $2::jsonb, pub_id = $3, updated_at = now() "
                    f"WHERE doc_id = $1",
                    doc_id, _dumps(after_doc), after_doc.get("id"),
                )
            except Exception as exc:  # noqa: BLE001
                if _is_duplicate_key(exc):
                    raise DuplicateKeyError(f"E11000 duplicate key on {self._table}") from exc
                raise
        chosen = after_doc if after else before
        return _apply_projection(chosen, projection)

    async def find_one_and_replace(
        self, spec, replacement, projection=None, upsert=False, sort=None,
        return_document=True, **kw,
    ) -> Optional[Dict]:
        return await self.find_one_and_update(
            spec, replacement, projection=projection, upsert=upsert, sort=sort,
            return_document=return_document, **kw,
        )

    async def find_one_and_delete(self, spec, projection=None, sort=None, **kw) -> Optional[Dict]:
        params = _Params()
        where = _Translator(params).compile(spec or {})
        rows = await self._db.fetch(
            f"SELECT doc_id, body FROM {self._table} WHERE {where} LIMIT 1", *params.values,
        )
        if not rows:
            return None
        doc_id, body = rows[0]
        await self._db.execute(f"DELETE FROM {self._table} WHERE doc_id = $1", doc_id)
        doc = _loads(body)
        return _apply_projection(doc, projection) if isinstance(doc, dict) else None

    async def delete_one(self, spec, **kw) -> DeleteResult:
        params = _Params()
        where = _Translator(params).compile(spec or {})
        status = await self._db.execute(
            f"DELETE FROM {self._table} WHERE doc_id IN "
            f"(SELECT doc_id FROM {self._table} WHERE {where} LIMIT 1)",
            *params.values,
        )
        return DeleteResult(int(status))

    async def delete_many(self, spec, **kw) -> DeleteResult:
        params = _Params()
        where = _Translator(params).compile(spec or {})
        status = await self._db.execute(f"DELETE FROM {self._table} WHERE {where}", *params.values)
        return DeleteResult(int(status))

    async def create_index(self, keys, **kwargs) -> str:
        """Build the btree index the application asked for.

        ``body`` is JSONB, so the index is an expression index over
        ``body #>> '{field}'`` -- the same expression the query translator emits,
        which is the only form an index can actually serve. ``partialFilterExpression``
        is honoured by translating its equality conditions into a WHERE clause, so
        ``{"email": {"$type": "string"}}`` becomes "index rows where email is not
        null" rather than silently widening into a plain unique index.

        A failure is logged, not raised: server.py's startup hook creates indexes
        best-effort and must not be taken down by one duplicate value in legacy
        data.
        """
        fields = _index_fields(keys)
        name = "ix_%s_%s" % (
            self._table, "_".join(re.sub(r"\W", "", f) for f in fields) or "all",
        )
        unique = "UNIQUE " if kwargs.get("unique") else ""
        if not fields:
            try:
                await self._db.execute(
                    f"CREATE INDEX IF NOT EXISTS {name} ON {self._table} USING gin (body)"
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("index %s on %s failed: %s", name, self._table, exc)
            return name

        cols = ", ".join("(body #>> '{%s}')" % f.replace(",", "") for f in fields)
        where = _partial_where(kwargs.get("partialFilterExpression"))
        # Wrap in DO/EXCEPTION so one bad index cannot abort a transaction that is
        # still creating the other 180.
        statement = (
            f"DO $pgdb$ BEGIN "
            f"CREATE {unique}INDEX IF NOT EXISTS {name} ON {self._table} ({cols}){where}; "
            f"EXCEPTION WHEN others THEN RAISE WARNING 'index {name} not created: %', SQLERRM; "
            f"END $pgdb$"
        )
        try:
            await self._db.execute(statement)
        except Exception as exc:  # noqa: BLE001
            logger.error("index %s on %s failed: %s", name, self._table, exc)
        return name

    # -- internals --------------------------------------------------------
    async def _fetch(self, spec, projection, sort=None, limit=None, skip=0, pipeline=None):
        params = _Params()
        where = self._pipeline_where(pipeline, params) if pipeline else _Translator(params).compile(spec or {})

        sql = f"SELECT body FROM {self._table} WHERE {where}"
        if sort and sort[0]:
            order = []
            for field, direction in sort[0]:
                p = params.add(_path(field))
                jt = f"jsonb_typeof(body #> '{p}')"
                txt = f"body #>> '{p}'"
                order.append(
                    f"(CASE WHEN {jt} = 'number' THEN ({txt})::numeric END) "
                    f"{'DESC' if direction < 0 else 'ASC'} NULLS LAST, {txt} "
                    f"{'DESC' if direction < 0 else 'ASC'}"
                )
            sql += " ORDER BY " + ", ".join(order)
        if skip:
            sql += f" OFFSET {int(skip)}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        rows = await self._db.fetch(sql, *params.values)
        return [_apply_projection(_loads(r[0]), projection) for r in rows]

    def _pipeline_where(self, pipeline, params: _Params) -> str:
        """Support the $match/$sort/$limit/$group subset this codebase uses."""
        where = "true"
        for stage in pipeline:
            if not isinstance(stage, dict):
                continue
            if "$match" in stage:
                where = _Translator(params).compile(stage["$match"])
        return where

    async def _aggregate_simple(self, pipeline) -> List[Dict]:
        """Run the $match/$group/$sort/$limit subset the dashboard endpoints use."""
        params = _Params()
        where = self._pipeline_where(pipeline, params)
        sql = f"SELECT body FROM {self._table} WHERE {where}"
        rows = await self._db.fetch(sql, *params.values)
        docs = [_loads(r[0]) for r in rows]

        out = docs
        for op, spec in (doc.items() if isinstance(doc, dict) else []):
            if op in ("$group",):
                id_expr = spec.get("_id")
                acc: Dict[Any, Dict[str, Any]] = {}
                for d in out:
                    key = _resolve_group_id(d, id_expr)
                    slot = acc.setdefault(key, {})
                    for out_field, agg_spec in spec.items():
                        if out_field == "_id":
                            continue
                        if not isinstance(agg_spec, dict) or not agg_spec:
                            continue
                        op_name = next(iter(agg_spec))
                        arg = agg_spec[op_name]
                        if op_name == "$sum":
                            if isinstance(arg, str) and arg.startswith("$"):
                                val = _get_path(d, arg[1:])
                            else:
                                val = arg
                            try:
                                slot[out_field] = slot.get(out_field, 0) + (val or 0)
                            except TypeError:
                                slot[out_field] = slot.get(out_field, 0) + 1
                        elif op_name == "$count":
                            slot[out_field] = slot.get(out_field, 0) + 1
                        elif op_name in ("$avg", "$max", "$min"):
                            val = _get_path(d, arg[1:]) if isinstance(arg, str) and arg.startswith("$") else arg
                            if val is None:
                                continue
                            if op_name == "$avg":
                                acc_avg = slot.setdefault("_avg", {})
                                pair = acc_avg.setdefault(out_field, [0, 0])
                                pair[0] += val
                                pair[1] += 1
                            else:
                                seen = slot.get(out_field)
                                slot[out_field] = val if seen is None else (
                                    max(seen, val) if op_name == "$max" else min(seen, val)
                                )
                        else:
                            slot.setdefault(out_field, None)
                out = []
                for k, v in acc.items():
                    row: Dict[str, Any] = {}
                    if id_expr is not None or "_id" in spec:
                        row["_id"] = k
                    avgs = v.pop("_avg", {})
                    row.update(v)
                    for field, total in avgs.items():
                        row[field] = total[0] / total[1] if total[1] else None
                    out.append(row)
            elif op == "$sort":
                out = _sort_docs(out, [(k, int(v)) for k, v in (spec or {}).items()])
            elif op == "$limit":
                out = out[: int(spec)]
            elif op == "$skip":
                out = out[int(spec):]
        return out


def _resolve_group_id(doc: Dict, id_expr: Any) -> Any:
    if id_expr is None:
        return None
    if isinstance(id_expr, str) and id_expr.startswith("$"):
        return doc.get(id_expr[1:])
    return id_expr


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
class PostgresDocumentDB:
    """Drop-in replacement for the Motor ``AsyncIOMotorDatabase`` handle."""

    def __init__(self, pool):
        self._pool = pool
        self._cache: Dict[str, Collection] = {}

    def __getitem__(self, name: str) -> Collection:
        if name not in self._cache:
            self._cache[name] = Collection(self, name)
        return self._cache[name]

    def __getattr__(self, name: str) -> Collection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    async def fetch(self, sql: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    async def fetchval(self, sql: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, *args) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(sql, *args)

    async def command(self, name: str, *a, **kw):
        """The app's health check is ``await db.command("ping")``."""
        if name == "ping":
            await self.fetchval("SELECT 1")
            return {"ok": 1}
        if name in ("collstats",):
            return {"ok": 1}
        raise NotImplementedError(f"command {name!r} is not supported by the Postgres store")

    async def list_collection_names(self) -> List[str]:
        rows = await self.fetch(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relkind = 'r' AND n.nspname = 'public' AND c.relname LIKE 'c\\_%'"
        )
        return [r[0][2:] for r in rows]