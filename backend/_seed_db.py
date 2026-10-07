"""Shared PostgreSQL connection helper for seed/one-off scripts.

Usage::

    from _seed_db import connect_db
    pool, db = await connect_db()
    # ... use db as a PostgresDocumentDB ...
    await pool.close()

DATABASE_URL must be set in the environment (or in backend/.env).
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


def _load_env() -> None:
    """Load backend/.env if it exists (idempotent)."""
    try:
        from dotenv import load_dotenv  # type: ignore
        env = Path(__file__).parent / ".env"
        if env.exists():
            load_dotenv(env)
        # Also try the plain cwd .env so scripts run from different dirs work.
        load_dotenv()
    except ImportError:
        pass


def _normalize_url(url: str) -> str:
    """Percent-encode '@' and other reserved chars that may appear in passwords."""
    if "@" in url.split("://", 1)[-1]:
        head, _, tail = url.partition("://")
        creds, _, hostpart = tail.rpartition("@")
        if ":" in creds:
            u, _, p = creds.partition(":")
            url = f"{head}://{quote(u, safe='')}:{quote(p, safe='')}@{hostpart}"
    return url


async def connect_db(min_size: int = 1, max_size: int = 3):
    """Return ``(pool, db)`` for the configured PostgreSQL database.

    Raises ``SystemExit`` if DATABASE_URL is not set.
    """
    import asyncpg  # type: ignore
    from pgdb import PostgresDocumentDB  # type: ignore

    _load_env()
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        raise SystemExit(
            "DATABASE_URL is not set.\n"
            "  Add it to backend/.env or export it before running this script."
        )
    url = _normalize_url(raw_url)
    pool = await asyncpg.create_pool(url, min_size=min_size, max_size=max_size, command_timeout=30)
    db = PostgresDocumentDB(pool)
    return pool, db
