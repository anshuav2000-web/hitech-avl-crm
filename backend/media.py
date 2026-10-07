"""Upload storage for brand logos and product images.

Why the bytes live in the database rather than on disk:

* the backend container has **no volume**. Anything written to its filesystem is
  destroyed by the next deploy, which would silently blank every logo the day
  after it was uploaded;
* a logo has to be reachable from a customer-facing quotation page, so it must be
  served by the same origin that serves the API and survive a redeploy;
* the payloads are small (a logo is tens of KB), so the database is a perfectly
  adequate blob store here and it keeps the asset, its metadata and the row that
  references it in one transaction-adjacent place.

Files are stored **verbatim**. Re-encoding to normalise an image would destroy
exactly the thing logos need: a transparent PNG background. The bytes that were
uploaded are the bytes that are served.

Validation is by magic bytes plus a real decode, never by the client-supplied
content type, which is attacker controlled and routinely wrong.

Bytes are persisted in PostgreSQL JSONB as base64-encoded strings via pgdb.py's
``_default`` serialiser and recovered by ``_revive``. No external binary wrapper
(bson.Binary) is needed.
"""
from __future__ import annotations

import hashlib
import io
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
# A brand logo is a small raster asset. 2 MB is generous for a transparent PNG and
# small enough that a mistaken multi-megabyte photo cannot fill the database.
MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
# Decompression-bomb guard: refuse anything larger than 40 megapixels.
MAX_PIXELS = 40_000_000

# ---------------------------------------------------------------------------
# Allowed formats
# ---------------------------------------------------------------------------
# PNG is the format the business asked for and is the default everywhere. JPEG
# and WebP are accepted because a photograph of a logo arrives that way, and the
# format is detected from the bytes, never from the filename.
_MAGIC: Tuple[Tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)
_WEBP_HEAD = b"RIFF"

_EXT_TO_CONTENT_TYPE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class MediaError(ValueError):
    """A rejected upload. The message is safe to show to an operator."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(name: Optional[str], fallback_ext: str = ".png") -> str:
    """A stored filename that cannot escape its directory or carry a second extension."""
    base = (name or "").strip().split("/")[-1].split("\\")[-1]
    base = _SAFE_NAME.sub("_", base).strip("._-")
    if not base:
        base = "upload"
    if not re.search(r"\.(png|jpe?g|webp)$", base, re.I):
        base += fallback_ext
    return base[:120]


def sniff_content_type(data: bytes) -> Optional[str]:
    """Detect the format from the leading bytes.

    ``Content-Type`` on the multipart part is supplied by the client and is not
    evidence of anything. The magic number is.
    """
    for magic, content_type in _MAGIC:
        if data.startswith(magic):
            return content_type
    if len(data) >= 12 and data[:4] == _WEBP_HEAD and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def inspect_image(data: bytes) -> dict:
    """Validate the payload and return its metadata.

    Raises :class:`MediaError` with an operator-readable reason for: not an
    image, empty, too large, or a corrupt file whose header lies.
    """
    if not data:
        raise MediaError("The file is empty.")
    content_type = sniff_content_type(data)
    if content_type is None:
        raise MediaError(
            "Unsupported file type. Upload a PNG, JPEG or WebP image "
            "(a PNG is recommended so the background stays transparent)."
        )

    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is a hard runtime dependency
        raise MediaError("Image support is unavailable on the server.")

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()  # structural check: catches truncated/lying files
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            fmt = (img.format or "").upper()
            has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
    except MediaError:
        raise
    except Exception as exc:
        raise MediaError(f"That file could not be read as an image ({exc}).")

    if width <= 0 or height <= 0:
        raise MediaError("That image has no usable dimensions.")
    if width * height > MAX_PIXELS:
        raise MediaError(
            f"That image is {width}x{height} pixels, which is too large. "
            "Use an image under 40 megapixels."
        )
    return {
        "content_type": content_type,
        "width": width,
        "height": height,
        # Transparency is only preserved if the source really has an alpha
        # channel. Reporting it lets the UI warn before a JPEG logo is saved on
        # a white tile where a transparent PNG would have looked correct.
        "has_alpha": bool(has_alpha),
        "format": fmt,
    }


def check_size(size: int, kind: str) -> None:
    limit = MAX_LOGO_BYTES if kind.endswith("logo") else MAX_IMAGE_BYTES
    if size > limit:
        mb = limit // (1024 * 1024)
        raise MediaError(f"That file is {size // 1024} KB. The limit for {kind} is {mb} MB.")


async def store(db, data: bytes, *, filename: Optional[str], kind: str,
                actor: Optional[dict] = None, extra: Optional[dict] = None) -> dict:
    """Validate and persist an upload. Idempotent on identical bytes.

    The id is the SHA-256 of the content, so uploading the same file twice -- a
    double click, a retried request, two admins replacing a logo with the same
    asset -- reuses one row instead of accumulating orphans.
    """
    check_size(len(data), kind)
    meta = inspect_image(data)
    digest = hashlib.sha256(data).hexdigest()
    media_id = digest

    existing = await db.media.find_one({"_id": media_id}, {"_id": 0, "id": 1})
    if existing:
        # Already stored. Refresh the pointer count and return the same document so
        # the caller's reference is stable.
        await db.media.update_one({"_id": media_id}, {"$inc": {"upload_count": 1},
                                                      "$set": {"last_used_at": _now()}})
        doc = await db.media.find_one({"_id": media_id}, {"_id": 0, "data": 0})
        return doc

    doc = {
        "id": media_id,
        "_id": media_id,
        "sha256": digest,
        "filename": safe_filename(filename, "." + (meta["format"].lower() or "png")),
        "content_type": meta["content_type"],
        "size": len(data),
        "width": meta["width"],
        "height": meta["height"],
        "has_alpha": meta["has_alpha"],
        "format": meta["format"],
        "kind": kind,
        "upload_count": 1,
        "uploaded_by": (actor or {}).get("id"),
        "uploaded_by_name": (actor or {}).get("name"),
        "uploaded_at": _now(),
        "last_used_at": _now(),
        "data": bytes(data),
    }
    if extra:
        doc.update(extra)
    await db.media.insert_one(dict(doc))
    out = dict(doc)
    out.pop("data", None)
    out.pop("_id", None)
    return out


async def load(db, media_id: str) -> Optional[dict]:
    return await db.media.find_one({"_id": media_id})


async def metadata(db, media_id: str) -> Optional[dict]:
    doc = await db.media.find_one({"_id": media_id}, {"_id": 0, "data": 0})
    return doc


def public_url(media_id: Optional[str]) -> Optional[str]:
    """The stable, frontend-agnostic URL for a stored asset.

    Relative on purpose: the CRM is served from several origins (public
    quotation links, an IP during setup, a custom domain later), and a hard-coded
    absolute host would break on the first change. The frontend prefixes it with
    the API base, exactly as it does for every other call.
    """
    if not media_id:
        return None
    return f"/api/media/{media_id}"


def attach(db_media_doc: Optional[dict], key: str = "logo_media_id") -> dict:
    """Add the resolved public URL next to the raw media id.

    Consumers get both: the id so they can replace or remove the asset, and the
    URL so they can render it without a second request.
    """
    out = dict(db_media_doc or {})
    if out.get(key):
        out[f"{key}_url"] = public_url(out[key])
    return out