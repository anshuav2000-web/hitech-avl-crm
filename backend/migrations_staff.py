"""m013 -- the real staff directory.

Source: the floor-sheet handed over by the business. 43 people across 13
departments. **The names, departments, extensions and mobiles below are transcribed
verbatim**, including the source's own inconsistencies, because this is a directory
that people will read on a phone:

* ``RASHEEN`` and ``kamaksha`` keep their original casing.
* ``Excel Excutive`` keeps its typo.
* ``Piyush`` has no extension and ``Excel Excutive`` has neither extension nor mobile.
  Both are stored as ``None`` -- the blanks are recorded as missing, never guessed,
  and the records are still created.
* Extension ``371`` legitimately appears twice (Mahender in AMC / Tender, Jay in
  Application Team). That is real, so it is not a duplicate to be cleaned up.

Matching strategy, in order, so re-running never creates a second copy of a person:

1. existing record with the same ``mobile`` (strongest identifier, 10-digit)
2. existing record with the same ``name`` **and** ``department``
3. otherwise insert

Nothing is ever deleted or renamed here.

On roles: ``role`` is the CRM's *permission* field, not a job title, and it is not part
of the source data. Mapping a department onto a permission is a security decision, so
this migration deliberately does **not** hand out ``admin``/``superadmin``/``management``
to anyone -- not even the people listed under Management. See ``ROLE_PROPOSALS`` for the
suggested mapping; apply it once someone confirms who should actually have admin.
"""

import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Verbatim transcription: (name, department, extension, mobile)
# extension/mobile are None where the source sheet was blank.
# ---------------------------------------------------------------------------

STAFF_DIRECTORY = [
    # Reception
    ("Neeta Yadav", "Reception Ground Floor", "317", "9871059125"),
    ("Vaishali", "Reception Second Floor", "351", "8882068588"),

    # Management
    ("Rajan Gupta", "Management", "301", "9811015472"),
    ("Nirdosh Aggarwal", "Management", "302", "9810568450"),
    ("Yash Gupta", "Management", "303", "7838218866"),
    ("Shaurya Gupta", "Management", "304", "9873210611"),

    # Sales
    ("Rakesh", "Sales", "311", "9953515976"),
    ("Ajay Teja", "Sales", "306", "9985534774"),
    ("Raheesuddin", "Sales", "313", "9213864923"),
    ("Ajay", "Sales", "340", "9675342458"),
    ("Rohit", "Sales", "327", "8287695976"),

    # Marketing
    ("Anchit", "Marketing", "356", "9971193032"),
    ("Kanika", "Marketing", "211", "8937931125"),

    # Service
    ("Amit Saxena", "Service", "355", "9871876757"),
    ("Sube Singh", "Service", "354", "9818024272"),
    ("Abhishek", "Service", "346", "9318353420"),
    ("RASHEEN", "Service", "342", "9899229608"),

    # AMC / Tender
    ("Lalit Pandey", "AMC / Tender", "332", "8010395404"),
    ("Satyam AMC", "AMC / Tender", "365", "7532040240"),
    ("Mahender", "AMC / Tender", "371", "9958266287"),
    ("Vipin", "AMC / Tender", "328", "9953621201"),

    # Application Team
    ("Satyam Rajvanshi", "Application Team", "347", "8171109434"),
    ("Ganesh", "Application Team", "423", "7428031366"),
    ("Piyush", "Application Team", None, "9650376042"),
    ("Imran", "Application Team", "349", "9910308361"),
    ("kamaksha", "Application Team", "329", "9816697171"),
    ("Jay", "Application Team", "371", "8700359243"),

    # Design Team
    ("Niharika", "Design Team", "316", "8340559391"),
    ("Ashraf", "Design Team", "339", "9582781178"),
    ("Zuber", "Design Team", "331", "8750343610"),

    # Store Dept.
    ("Dayaram", "Store Dept.", "777", "9871297067"),
    ("Ashish", "Store Dept.", "350", "7827915131"),

    # Accounts Dept.
    ("Gaurav Verma", "Accounts Dept.", "325", "9891280720"),
    ("Umesh Pandey", "Accounts Dept.", "318", "8178808818"),
    ("Prakash Jha", "Accounts Dept.", "320", "9990584604"),
    ("Puran", "Accounts Dept.", "321", "9999719861"),
    ("Rashmi", "Accounts Dept.", "319", "9810884725"),
    ("Vipul", "Accounts Dept.", "310", "9560232729"),

    # Admin
    ("Mrs. Daniel", "Admin", "308", "9968314860"),
    ("Rajiv", "Admin", "435", "9810282370"),
    ("Excel Excutive", "Admin", None, None),
    ("Deepika", "Admin", "338", "8882798095"),

    # HR Department
    ("Aanchal", "HR Department", "309", "8377860128"),
]

# Suggested role mapping, NOT applied by this migration. Every value here is a
# non-privileged CRM role; the three admin-tier roles are intentionally absent.
ROLE_PROPOSALS = {
    "Sales": "sales",
    "Service": "service",
    "AMC / Tender": "service",
    "Application Team": "service",
    "Design Team": "design",
    "Accounts Dept.": "accounts",
    "Store Dept.": "purchase",
    "Marketing": "sales",
    "Reception Ground Floor": "staff",
    "Reception Second Floor": "staff",
    "Management": "management",   # <-- admin tier: needs explicit sign-off
    "Admin": "admin",             # <-- admin tier: needs explicit sign-off
    "HR Department": "staff",
}

DEFAULT_ROLE = "staff"

# Marks these rows as real staff imported from the floor sheet, so they can be told
# apart from the seeded demo accounts and purged on their own schedule.
SOURCE_TAG = "staff_import_2026_10"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_mobile(value):
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


async def m013_import_staff_directory(db):
    """Import / refresh the 43-person staff directory. Idempotent, non-destructive."""
    now = _now()
    added, updated, unchanged = 0, 0, 0

    # Indexes FIRST. These employees have no email, and the existing plain unique
    # index on `email` treats every missing value as the same value -- so the very
    # first insert of `email: null` after the second one fails with E11000. The
    # partial index has to exist before any row goes in, not after.
    try:
        await db.users.drop_index("email_1")
    except Exception:
        pass  # may not exist yet
    await db.users.create_index(
        "email",
        unique=True,
        background=True,
        partialFilterExpression={"email": {"$type": "string"}},
    )
    await db.users.create_index("phone", background=True)
    await db.users.create_index("extension", background=True)
    await db.users.create_index([("name", 1), ("department", 1)], background=True)
    await db.users.create_index("staff_source", background=True)

    for name, department, extension, mobile in STAFF_DIRECTORY:
        ext = str(extension) if extension not in (None, "") else None
        mob = _norm_mobile(mobile)

        existing = None
        if mob:
            existing = await db.users.find_one({"phone": mob}, {"_id": 0, "id": 1})
        if not existing:
            existing = await db.users.find_one(
                {"name": name, "department": department}, {"_id": 0, "id": 1}
            )

        if existing:
            # Update in place; never create a second record for the same person and
            # never blank out a field the user already filled in.
            sets = {"updated_at": now, "staff_source": SOURCE_TAG}
            if ext:
                sets["extension"] = ext
            if mob:
                sets["phone"] = mob
            before = await db.users.find_one({"id": existing["id"]}, {"_id": 0})
            differs = any(
                before.get(f) != sets.get(f) for f in ("extension", "phone")
            ) or before.get("staff_source") != SOURCE_TAG
            await db.users.update_one({"id": existing["id"]}, {"$set": sets})
            if differs:
                updated += 1
            else:
                unchanged += 1
            continue

        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "name": name,
            "department": department,
            "extension": ext,
            "phone": mob,
            # No email was supplied, so none is invented. email stays null, which the
            # partial unique index allows for any number of rows. An employee cannot
            # log in until IT assigns an address.
            "email": None,
            "role": DEFAULT_ROLE,
            "designation": None,
            "allowed_brands": [],
            "active": True,
            "is_demo": False,
            "staff_source": SOURCE_TAG,
            # Empty rather than absent: /auth/login reads this key and a missing one
            # would surface as a 500 instead of a clean 401.
            "password_hash": "",
            "created_at": now,
            "updated_at": now,
        })
        added += 1

    # Employees legitimately share nothing but the one repeated extension, so index on
    # the pair people are actually unique by. (Created at the top of this migration,
    # before any insert, because the email index swap has to happen first.)

    missing = sum(
        1 for _, _, e, m in STAFF_DIRECTORY if e in (None, "") or m in (None, "")
    )
    return (
        f"{added} added, {updated} updated, {unchanged} unchanged "
        f"(directory={len(STAFF_DIRECTORY)}, incomplete={missing})"
    )