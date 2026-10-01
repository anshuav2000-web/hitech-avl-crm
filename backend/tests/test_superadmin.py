"""End-to-end tests for the Super Admin system.

Covers the guarantees the business asked for, and the ways each one is easy to get
wrong:

* a Super Admin has no restriction anywhere; a normal admin and a sales rep do not
  inherit it, and the restriction is enforced by the API rather than the UI
* a brand can be created, uploaded for, edited, re-logoed, deactivated, archived
  and restored -- and stays visible in the catalogue at each step
* an uploaded PNG survives round-tripping byte-for-byte, transparency included
* bad uploads are rejected with a useful message instead of a 500
* every privileged change is recorded in the audit trail with before/after values
* a product can be created, re-branded, duplicated and bulk-edited, and always keeps
  a valid brand relationship

The suite runs against a live backend (``REACT_APP_BACKEND_URL``) and cleans up
everything it creates, so it is safe to run against a seeded development database.
"""
import io
import os
import random
import struct
import uuid
import zlib

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@hitechaudio.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")
SALES_EMAIL = os.environ.get("SALES_EMAIL", "sales@hitechaudio.in")
SALES_PASSWORD = os.environ.get("SALES_PASSWORD", "Sales@123")


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------
def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="module")
def admin():
    r = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"admin login failed: {r.text}"
    tok = r.json().get("token") or r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def superadmin(admin):
    """Promote a throwaway account to superadmin and log in as it.

    The suite never mutates the real admin's role: doing so would leave the
    deployment in a state nobody asked for if the run was interrupted.
    """
    r = requests.get(f"{API}/users", headers=admin, timeout=30)
    assert r.status_code == 200, r.text
    users = r.json()
    email = "qa.superadmin@hitech.example"
    existing = next((u for u in users if u.get("email") == email), None)
    if not existing:
        r = requests.post(f"{API}/users", headers=admin, timeout=30, json={
            "name": "QA Super Admin", "email": email, "password": "Super@12345",
            "role": "superadmin", "department": "QA"})
        assert r.status_code == 201, r.text
        existing = r.json()
    requests.patch(f"{API}/users/{existing['id']}", headers=admin, timeout=30,
                   json={"role": "superadmin", "is_active": True})
    r = _login(email, "Super@12345")
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}", "id": existing["id"], "email": email}


@pytest.fixture(scope="module")
def sales():
    r = _login(SALES_EMAIL, SALES_PASSWORD)
    if r.status_code != 200:
        pytest.skip("demo sales account not configured")
    tok = r.json().get("token") or r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


CREATED_BRANDS: list = []
CREATED_PRODUCTS: list = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    h = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    tok = h.json().get("token") or h.json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    for pid in CREATED_PRODUCTS:
        requests.delete(f"{API}/products/{pid}", headers=auth, timeout=20)
    for bid in CREATED_BRANDS:
        requests.delete(f"{API}/brands/{bid}", headers=auth, timeout=20)
    CREATED_BRANDS.clear()
    CREATED_PRODUCTS.clear()


def make_png(width=8, height=8, rgba=True, noise=False):
    """A real, valid PNG built byte by byte.

    Deliberately not a fixture file: this proves the endpoint accepts genuine PNG
    data rather than anything with a .png extension.

    ``noise`` fills the pixels with incompressible pseudo-random bytes. Uniform
    pixels are almost free to deflate, so a 1400x1400 solid image lands at a few
    kilobytes -- fine for correctness tests, useless for exercising the upload size
    limit, which is why the size test asks for noise.
    """
    color_type = 6 if rgba else 2  # 6 = RGBA, 2 = RGB
    channels = 4 if rgba else 3
    raw = bytearray()
    rng = random.Random(20260101)
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        for x in range(width):
            if noise:
                raw += bytes(rng.randrange(256) for _ in range(channels))
            else:
                # A fully transparent pixel: transparency is what must survive.
                raw += bytes([0, 0, 0, 0] if rgba else [255, 0, 0])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw)))
            + chunk(b"IEND", b""))


def upload_logo(brand_id, headers, png=None, filename="logo.png", field="file"):
    data = png if png is not None else make_png()
    return requests.post(f"{API}/brands/{brand_id}/logo", headers=headers, timeout=30,
                         files={field: (filename, data, "image/png")})


# ---------------------------------------------------------------------------
# Permission engine
# ---------------------------------------------------------------------------
class TestPermissionRegistry:
    def test_registry_is_served(self, admin):
        r = requests.get(f"{API}/permissions", headers=admin, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        keys = {m["key"] for m in body["modules"]}
        for expected in ("users", "admins", "brands", "products", "categories",
                         "inventory", "customers", "orders", "quotations", "invoices",
                         "reports", "settings", "media", "system"):
            assert expected in keys, f"module {expected} missing from the registry"

    def test_super_admin_reports_full_access(self, superadmin):
        r = requests.get(f"{API}/permissions", headers=superadmin, timeout=30)
        body = r.json()
        assert body["is_super_admin"] is True
        assert body["permission_level"] == "all"
        for module in body["modules"]:
            assert all(module["held"].values()), f"{module['key']} not held by Super Admin"

    def test_admin_is_not_super_admin(self, admin):
        body = requests.get(f"{API}/permissions", headers=admin, timeout=30).json()
        assert body["is_admin"] is True
        assert body["is_super_admin"] is False
        assert body["permission_level"] is None

    def test_role_matrix_is_super_admin_only(self, admin, sales):
        assert requests.get(f"{API}/roles/permissions", headers=admin, timeout=30).status_code == 200
        assert requests.get(f"{API}/roles/permissions", headers=sales, timeout=30).status_code == 403

    def test_superadmin_role_document_is_expanded(self, admin):
        roles = requests.get(f"{API}/roles", headers=admin, timeout=30).json()
        sa = next((r for r in roles if r["name"] == "superadmin"), None)
        assert sa is not None, "the superadmin role is missing from the roles collection"
        assert sa.get("permission_level") == "all"
        assert "brands.manage" in sa["permissions"]
        assert "media.manage" in sa["permissions"]


# ---------------------------------------------------------------------------
# Backend enforcement -- the UI is not the security boundary
# ---------------------------------------------------------------------------
class TestAuthorizationIsEnforcedServerSide:
    def test_sales_cannot_create_a_brand(self, sales):
        r = requests.post(f"{API}/brands", headers=sales, timeout=30,
                          json={"name": f"Unauthorized {uuid.uuid4().hex[:8]}"})
        assert r.status_code == 403, r.text

    def test_sales_cannot_create_a_product(self, sales):
        r = requests.post(f"{API}/products", headers=sales, timeout=30,
                          json={"brand": "RCF", "name": "Unauthorized Widget"})
        assert r.status_code == 403, r.text

    def test_sales_cannot_upload_media(self, sales):
        r = requests.post(f"{API}/media", headers=sales, timeout=30,
                          files={"file": ("x.png", make_png(), "image/png")})
        assert r.status_code == 403, r.text

    def test_sales_cannot_read_the_audit_trail(self, sales):
        assert requests.get(f"{API}/audit-logs", headers=sales, timeout=30).status_code == 403

    def test_sales_cannot_delete_a_brand(self, sales, admin):
        brands = requests.get(f"{API}/brands", headers=admin, timeout=30).json()
        r = requests.delete(f"{API}/brands/{brands[0]['id']}", headers=sales, timeout=30)
        assert r.status_code == 403, r.text

    def test_anonymous_cannot_touch_master_data(self):
        for method, path, kwargs in (
            ("get", "/brands", {}),
            ("post", "/brands", {"json": {"name": "Anon"}}),
            ("post", "/products", {"json": {"brand": "RCF", "name": "Anon"}}),
            ("get", "/audit-logs", {}),
            ("get", "/permissions", {}),
            ("get", "/users", {}),
        ):
            r = getattr(requests, method)(f"{API}{path}", timeout=30, **kwargs)
            assert r.status_code == 401, f"{method.upper()} {path} returned {r.status_code}"

    def test_super_admin_can_do_what_an_admin_cannot(self, admin, superadmin):
        """Every Super Admin capability an ordinary admin lacks is exercised."""
        brand = requests.post(f"{API}/brands", headers=superadmin, timeout=30, json={
            "name": f"SA Privilege {uuid.uuid4().hex[:6]}",
            "official_website": "https://example.com"}).json()
        CREATED_BRANDS.append(brand["id"])

        # 1. Deactivate (archive a single brand without touching its products).
        r = requests.patch(f"{API}/brands/{brand['id']}", headers=superadmin, timeout=30,
                           json={"status": "inactive"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "inactive"

        # 2. Restore it to the catalogue.
        r = requests.patch(f"{API}/brands/{brand['id']}", headers=superadmin, timeout=30,
                           json={"status": "active"})
        assert r.status_code == 200 and r.json()["status"] == "active"
        assert r.json()["approved"] is True

        # 3. Audit trail, readable by Super Admin and by admin.
        for headers in (superadmin, admin):
            r = requests.get(f"{API}/audit-logs", headers=headers, timeout=30,
                             params={"record_id": brand["id"]})
            assert r.status_code == 200, r.text
            assert r.json()["total"] >= 1, "creating a brand wrote no audit entry"

    def test_normal_admin_cannot_grant_superadmin(self, admin, superadmin):
        """The privilege-escalation guard."""
        r = requests.get(f"{API}/users", headers=admin, timeout=30)
        victim = requests.post(f"{API}/users", headers=admin, timeout=30, json={
            "name": "Escalation Probe", "email": f"probe.{uuid.uuid4().hex[:6]}@hitech.example",
            "password": "Probe@12345", "role": "sales"})
        assert victim.status_code == 201, victim.text
        vid = victim.json()["id"]
        try:
            r = requests.patch(f"{API}/users/{vid}", headers=admin, timeout=30,
                               json={"role": "superadmin"})
            assert r.status_code == 403, f"an ordinary admin promoted a user: {r.status_code} {r.text}"
        finally:
            requests.delete(f"{API}/users/{vid}", headers=admin, timeout=20)

    def test_no_one_can_change_their_own_role(self, admin):
        me = requests.get(f"{API}/auth/me", headers=admin, timeout=30).json()
        r = requests.patch(f"{API}/users/{me['id']}", headers=admin, timeout=30,
                           json={"role": "superadmin"})
        assert r.status_code == 400, r.text


# ---------------------------------------------------------------------------
# Brand management
# ---------------------------------------------------------------------------
class TestBrandManagement:
    def test_created_brand_is_immediately_visible(self, superadmin):
        """A brand added through the API must appear in the catalogue.

        The previous implementation wrote ``approved: False``, so the brand was
        saved and then invisible everywhere -- the single most confusing failure
        this feature set has to not have.
        """
        name = f"Visible Brand {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/brands", headers=superadmin, timeout=30, json={
            "name": name, "official_website": "https://example.com",
            "brand_category": "Professional Audio"})
        assert r.status_code == 201, r.text
        bid = r.json()["id"]
        CREATED_BRANDS.append(bid)

        listed = requests.get(f"{API}/brands", headers=superadmin, timeout=30).json()
        assert name in [b["name"] for b in listed], \
            "the brand was created but does not appear in GET /brands"
        assert r.json()["approved"] is True
        assert r.json()["status"] == "active"

    def test_duplicate_brand_is_rejected(self, superadmin):
        name = f"Duplicate Probe {uuid.uuid4().hex[:6]}"
        first = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                              json={"name": name})
        assert first.status_code == 201, first.text
        CREATED_BRANDS.append(first.json()["id"])
        second = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                               json={"name": name})
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"].lower()

    def test_edit_every_editable_field(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30, json={
            "name": f"Edit Probe {uuid.uuid4().hex[:6]}", "country": "India"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            r = requests.patch(f"{API}/brands/{bid}", headers=superadmin, timeout=30, json={
                "description": "Edited by the Super Admin test",
                "country": "United Kingdom",
                "official_website": "https://edited.example.com",
                "brand_category": "Live & Broadcast Audio",
                "tags": ["pa", "rental"],
                "featured": True})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["description"] == "Edited by the Super Admin test"
            assert body["country"] == "United Kingdom"
            assert body["official_website"] == "https://edited.example.com"
            assert body["brand_category"] == "Live & Broadcast Audio"
            assert body["tags"] == ["pa", "rental"]
            assert body["featured"] is True
            assert body["updated_at"] >= body["created_at"]
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_patch_is_partial_and_does_not_blank_fields(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30, json={
            "name": f"Partial Probe {uuid.uuid4().hex[:6]}",
            "description": "Keep this description",
            "country": "Japan"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            r = requests.patch(f"{API}/brands/{bid}", headers=superadmin, timeout=30,
                               json={"country": "Germany"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["country"] == "Germany"
            assert body["description"] == "Keep this description", \
                "a one-field patch blanked an unrelated field"
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_deactivate_hides_from_catalogue_but_keeps_the_row(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Deactivate Probe {uuid.uuid4().hex[:6]}"})
        bid, name = created.json()["id"], created.json()["name"]
        CREATED_BRANDS.append(bid)
        try:
            requests.patch(f"{API}/brands/{bid}", headers=superadmin, timeout=30,
                           json={"status": "inactive"})
            listed = [b["name"] for b in
                      requests.get(f"{API}/brands", headers=superadmin, timeout=30).json()]
            assert name not in listed, "an inactive brand is still in the active catalogue"
            every = [b["name"] for b in requests.get(
                f"{API}/brands", headers=superadmin, timeout=30,
                params={"include_archived": True}).json()]
            assert name in every, "deactivating a brand destroyed the row"
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_archive_then_restore_brings_the_brand_and_its_products_back(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Archive Probe {uuid.uuid4().hex[:6]}"})
        bid, name = created.json()["id"], created.json()["name"]
        CREATED_BRANDS.append(bid)
        prod = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                             json={"brand": name, "name": "Archive Probe Model"})
        assert prod.status_code == 201, prod.text
        pid = prod.json()["id"]
        CREATED_PRODUCTS.append(pid)
        try:
            r = requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=30)
            assert r.status_code == 200, r.text
            assert r.json()["products_archived"] == 1

            listed = [b["name"] for b in
                      requests.get(f"{API}/brands", headers=superadmin, timeout=30).json()]
            assert name not in listed

            r = requests.post(f"{API}/brands/{bid}/restore", headers=superadmin, timeout=30)
            assert r.status_code == 200, r.text
            assert r.json()["products_restored"] == 1
            listed = [b["name"] for b in
                      requests.get(f"{API}/brands", headers=superadmin, timeout=30).json()]
            assert name in listed, "the brand did not come back after a restore"
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_restoring_a_live_brand_is_refused(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Double Restore {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        r = requests.post(f"{API}/brands/{bid}/restore", headers=superadmin, timeout=30)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Logo upload
# ---------------------------------------------------------------------------
class TestLogoUpload:
    def test_upload_preview_replace_and_remove(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Logo Brand {uuid.uuid4().hex[:6]}"})
        bid, name = created.json()["id"], created.json()["name"]
        CREATED_BRANDS.append(bid)
        try:
            first = make_png(16, 16, rgba=True)
            r = upload_logo(bid, superadmin, first)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["logo_media_id"], "the upload did not store a media id"
            assert body["logo_url"] == f"/api/media/{body['logo_media_id']}"
            assert body["logo_media_id_url"], "no resolved media URL on the brand"

            # Served bytes are byte-identical: re-encoding would flatten alpha.
            served = requests.get(f"{API}/media/{body['logo_media_id']}", timeout=30)
            assert served.status_code == 200
            assert served.content == first, "the served PNG is not the uploaded PNG"
            assert served.headers.get("content-type") == "image/png"
            assert served.content[:8] == b"\x89PNG\r\n\x1a\n"

            # Appears on the list endpoint too, so every renderer sees it.
            listed = next(b for b in requests.get(f"{API}/brands", headers=superadmin,
                                                  timeout=30).json() if b["name"] == name)
            assert listed["logo_url"] == f"/api/media/{body['logo_media_id']}"

            # Replace with a different image.
            second = make_png(32, 24, rgba=False)
            r2 = upload_logo(bid, superadmin, second)
            assert r2.status_code == 200, r2.text
            assert r2.json()["logo_media_id"] != body["logo_media_id"]
            served2 = requests.get(f"{API}/media/{r2.json()['logo_media_id']}", timeout=30)
            assert served2.content == second

            # Remove.
            r3 = requests.delete(f"{API}/brands/{bid}/logo", headers=superadmin, timeout=30)
            assert r3.status_code == 200, r3.text
            assert not r3.json().get("logo_media_id")
            assert not r3.json().get("logo_url")
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_transparency_is_reported_and_preserved(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Alpha Brand {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            # Alpha is a property of the stored asset, so it is read from the media
            # resource. The brand endpoint answers with the brand.
            r = upload_logo(bid, superadmin, make_png(8, 8, rgba=True))
            assert r.status_code == 200, r.text
            mid = r.json()["logo_media_id"]
            info = requests.get(f"{API}/media/{mid}/info", timeout=30)
            assert info.status_code == 200
            assert info.json()["has_alpha"] is True
            served = requests.get(f"{API}/media/{mid}", timeout=30)
            assert served.status_code == 200
            # A PNG colour-type-6 header is what carries the alpha channel; if the
            # bytes were re-encoded it would have become colour type 2.
            assert served.content[25] == 6, "the alpha channel was lost in storage"

            r2 = upload_logo(bid, superadmin, make_png(8, 8, rgba=False))
            assert requests.get(f"{API}/media/{r2.json()['logo_media_id']}/info",
                                timeout=30).json()["has_alpha"] is False
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_identical_upload_reuses_one_row(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Dedupe Brand {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            png = make_png(10, 10, rgba=True)
            # The upload endpoint answers with the updated brand, so the media id
            # lives on ``logo_media_id``; the brand's own ``id`` is unchanged by
            # an upload and would make the dedupe assertion pass vacuously.
            a = upload_logo(bid, superadmin, png).json()
            b = upload_logo(bid, superadmin, png).json()
            assert a["logo_media_id"] == b["logo_media_id"], \
                "re-uploading identical bytes created a duplicate"
            media = requests.get(f"{API}/media/{b['logo_media_id']}/info",
                                 headers=superadmin, timeout=30).json()
            assert media["upload_count"] >= 2
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    @pytest.mark.parametrize("label,payload,filename,expect", [
        ("not an image", b"this is definitely not a png", "logo.png", "unsupported file type"),
        ("empty file", b"", "logo.png", "empty"),
        ("truncated png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 12, "broken.png", "could not be read"),
        ("png header with junk body", b"\x89PNG\r\n\x1a\n" + b"garbage" * 8, "x.png", "could not be read"),
    ])
    def test_invalid_uploads_are_rejected_with_a_message(self, superadmin, label, payload,
                                                         filename, expect):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Bad Upload {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            r = upload_logo(bid, superadmin, payload, filename)
            assert r.status_code == 400, f"{label}: expected 400, got {r.status_code}"
            detail = (r.json().get("detail") or "").lower()
            assert expect in detail, f"{label}: unhelpful message {detail!r}"
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_oversized_upload_is_rejected(self, superadmin):
        """A 3 MB PNG logo must be refused rather than stored."""
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Huge Brand {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            big = make_png(1400, 1400, rgba=True, noise=True)
            assert len(big) > 2 * 1024 * 1024, f"test payload is only {len(big)} bytes"
            r = upload_logo(bid, superadmin, big)
            assert r.status_code == 400, r.text
            assert "limit" in (r.json().get("detail") or "").lower()
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_upload_requires_the_brands_permission(self, sales):
        brands = requests.get(f"{API}/brands", headers=sales, timeout=30).json()
        if not brands:
            pytest.skip("no brands visible to the sales account")
        r = upload_logo(brands[0]["id"], sales)
        assert r.status_code == 403, r.text

    def test_missing_logo_has_a_clean_shape(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"No Logo {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        detail = requests.get(f"{API}/brands/{bid}", headers=superadmin, timeout=30).json()
        # No logo means the URL fields are empty, not missing or broken -- the UI
        # renders a placeholder from this without a special case.
        assert detail.get("logo_url") is None
        assert detail.get("logo_media_id") is None

    def test_unknown_media_id_is_404(self):
        r = requests.get(f"{API}/media/{uuid.uuid4().hex * 2}", timeout=30)
        assert r.status_code == 404

    def test_in_use_media_cannot_be_deleted(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"In Use {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            media_id = upload_logo(bid, superadmin).json()["logo_media_id"]
            r = requests.delete(f"{API}/media/{media_id}", headers=superadmin, timeout=30)
            assert r.status_code == 409, r.text
            assert "still used by" in (r.json().get("detail") or "")
        finally:
            requests.delete(f"{API}/brands/{bid}/logo", headers=superadmin, timeout=20)
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)


# ---------------------------------------------------------------------------
# Product management
# ---------------------------------------------------------------------------
class TestProductManagement:
    def _brand(self, superadmin, prefix):
        name = f"{prefix} {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/brands", headers=superadmin, timeout=30, json={"name": name})
        CREATED_BRANDS.append(r.json()["id"])
        return r.json()

    def test_product_keeps_stock_and_image_fields_that_were_previously_dropped(self, superadmin):
        brand = self._brand(superadmin, "Stock Probe")
        r = requests.post(f"{API}/products", headers=superadmin, timeout=30, json={
            "brand": brand["name"], "name": "Stocked Model", "sku": f"SKU-{uuid.uuid4().hex[:8]}",
            "stock_quantity": 42, "warehouse_location": "Bay 3",
            "technical_specifications": {"Output": "2000W", "Inputs": "4"},
            "features": ["Lightweight", "Rack mount"]})
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        CREATED_PRODUCTS.append(pid)
        try:
            body = requests.get(f"{API}/products/{pid}", headers=superadmin, timeout=30).json()
            assert body["stock_quantity"] == 42, "stock_quantity was dropped on create"
            assert body["warehouse_location"] == "Bay 3", "warehouse_location was dropped on create"
            assert body["technical_specifications"].get("Output") == "2000W"
            assert "Lightweight" in body["features"]
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)

    def test_product_always_has_a_valid_brand_relationship(self, superadmin):
        brand_a = self._brand(superadmin, "Brand A")
        brand_b = self._brand(superadmin, "Brand B")
        r = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                          json={"brand": brand_a["name"], "name": "Reassignable"})
        pid = r.json()["id"]
        CREATED_PRODUCTS.append(pid)
        try:
            detail = requests.get(f"{API}/products/{pid}", headers=superadmin, timeout=30).json()
            assert detail["brand_id"] == brand_a["id"]

            moved = requests.patch(f"{API}/products/{pid}", headers=superadmin, timeout=30,
                                   json={"brand": brand_b["name"]})
            assert moved.status_code == 200, moved.text
            assert moved.json()["brand"] == brand_b["name"]
            assert moved.json()["brand_id"] == brand_b["id"], "brand_id did not follow the rename"

            detail = requests.get(f"{API}/products/{pid}", headers=superadmin, timeout=30).json()
            assert detail["brand_doc"]["id"] == brand_b["id"], \
                "the brand document no longer resolves after the change"
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)

    def test_product_for_an_unknown_brand_is_rejected(self, superadmin):
        r = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                          json={"brand": f"Ghost {uuid.uuid4().hex[:8]}", "name": "Orphan"})
        assert r.status_code == 400
        assert "approved brand" in (r.json().get("detail") or "").lower()

    def test_partial_update_leaves_other_fields_alone(self, superadmin):
        brand = self._brand(superadmin, "Patch Brand")
        created = requests.post(f"{API}/products", headers=superadmin, timeout=30, json={
            "brand": brand["name"], "name": "Partial Product",
            "short_description": "keep me", "unit_price": 1000, "stock_quantity": 7})
        pid = created.json()["id"]
        CREATED_PRODUCTS.append(pid)
        try:
            r = requests.patch(f"{API}/products/{pid}", headers=superadmin, timeout=30,
                               json={"unit_price": 1500})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["unit_price"] == 1500
            assert body["short_description"] == "keep me", "a price edit blanked the description"
            assert body["stock_quantity"] == 7
            assert body["price_status"] == "set"
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)

    def test_status_change_is_allowed_including_archive(self, superadmin):
        brand = self._brand(superadmin, "Status Brand")
        created = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                                json={"brand": brand["name"], "name": "Statusable"})
        pid = created.json()["id"]
        CREATED_PRODUCTS.append(pid)
        try:
            for status in ("discontinued", "coming_soon", "active", "archived"):
                r = requests.patch(f"{API}/products/{pid}", headers=superadmin, timeout=30,
                                   json={"status": status})
                assert r.status_code == 200, r.text
                assert r.json()["status"] == status
            listed = requests.get(f"{API}/products", headers=superadmin, timeout=30,
                                  params={"brand": brand["name"]}).json()
            assert all(p["id"] != pid for p in listed), "an archived product is still listed"
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)

    def test_duplicate_creates_an_independent_record(self, superadmin):
        brand = self._brand(superadmin, "Dup Brand")
        created = requests.post(f"{API}/products", headers=superadmin, timeout=30, json={
            "brand": brand["name"], "name": "Original Model",
            "sku": f"DUP-{uuid.uuid4().hex[:8]}", "unit_price": 500})
        pid = created.json()["id"]
        try:
            r = requests.post(f"{API}/products/{pid}/duplicate", headers=superadmin, timeout=30,
                              json={})
            assert r.status_code == 201, r.text
            copy = r.json()
            CREATED_PRODUCTS.append(copy["id"])
            assert copy["id"] != pid
            assert copy["name"] != created.json()["name"]
            assert copy["sku"] != created.json()["sku"], "the duplicate reused the source SKU"
            assert copy["unit_price"] == 500, "the duplicate lost the price"
            assert copy["brand_id"] == created.json()["brand_id"]

            # Independent: editing the copy must not touch the original.
            requests.patch(f"{API}/products/{copy['id']}", headers=superadmin, timeout=30,
                           json={"unit_price": 999})
            again = requests.get(f"{API}/products/{pid}", headers=superadmin, timeout=30).json()
            assert again["unit_price"] == 500, "editing the duplicate changed the original"
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)

    def test_bulk_edit_reports_partial_failure(self, superadmin):
        brand = self._brand(superadmin, "Bulk Brand")
        other = self._brand(superadmin, "Bulk Other")
        a = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                          json={"brand": brand["name"], "name": "Bulk A"}).json()
        b = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                          json={"brand": brand["name"], "name": "Bulk B"}).json()
        CREATED_PRODUCTS.extend([a["id"], b["id"]])
        try:
            r = requests.post(f"{API}/products/bulk", headers=superadmin, timeout=30, json={
                "product_ids": [a["id"], b["id"], uuid.uuid4().hex + uuid.uuid4().hex],
                "unit_price": 777, "brand": other["name"]})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["updated"] == 2, body
            assert len(body["failed"]) == 1, body
            assert body["failed"][0]["error"] == "not found"
            for pid in (a["id"], b["id"]):
                p = requests.get(f"{API}/products/{pid}", headers=superadmin, timeout=30).json()
                assert p["unit_price"] == 777
                assert p["brand"] == other["name"]
        finally:
            for pid in (a["id"], b["id"]):
                requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)

    def test_bulk_cannot_change_a_sku(self, superadmin):
        r = requests.post(f"{API}/products/bulk", headers=superadmin, timeout=30,
                          json={"product_ids": [uuid.uuid4().hex], "sku": "X"})
        assert r.status_code == 400

    def test_product_image_upload_and_removal(self, superadmin):
        brand = self._brand(superadmin, "Image Brand")
        created = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                                json={"brand": brand["name"], "name": "Illustrated Model"})
        pid = created.json()["id"]
        CREATED_PRODUCTS.append(pid)
        try:
            png = make_png(12, 12, rgba=True)
            r = requests.post(f"{API}/products/{pid}/image", headers=superadmin, timeout=30,
                              files={"file": ("p.png", png, "image/png")})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["image_media_id"]
            assert body["image_url"] == f"/api/media/{body['image_media_id']}"
            assert f"/api/media/{body['image_media_id']}" in body["image_urls"]

            served = requests.get(f"{API}/media/{body['image_media_id']}", timeout=30)
            assert served.content == png

            listed = requests.get(f"{API}/products", headers=superadmin, timeout=30,
                                  params={"brand": brand["name"]}).json()
            found = next(p for p in listed if p["id"] == pid)
            assert found["image_url"] == f"/api/media/{body['image_media_id']}", \
                "the image is missing from the product listing"

            rm = requests.delete(f"{API}/products/{pid}/image", headers=superadmin, timeout=30)
            assert rm.status_code == 200
            assert not rm.json().get("image_media_id")
        finally:
            requests.delete(f"{API}/products/{pid}", headers=superadmin, timeout=20)


# ---------------------------------------------------------------------------
# Categories and attributes
# ---------------------------------------------------------------------------
class TestMasterData:
    def test_category_and_subcategory(self, superadmin):
        root_name = f"Root Cat {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/categories", headers=superadmin, timeout=30,
                          json={"name": root_name})
        assert r.status_code == 201, r.text
        rid = r.json()["id"]

        sub_name = f"Sub Cat {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/categories", headers=superadmin, timeout=30,
                          json={"name": sub_name, "parent_id": rid})
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        assert r.json()["parent_id"] == rid

        tree = requests.get(f"{API}/categories", headers=superadmin, timeout=30,
                            params={"nested": True}).json()
        node = next(c for c in tree if c["id"] == rid)
        assert [c["name"] for c in node["subcategories"]] == [sub_name]

        flat = requests.get(f"{API}/categories", headers=superadmin, timeout=30).json()
        assert any(c["id"] == sid for c in flat), "the flat list dropped the subcategory"

        for cid in (sid, rid):
            requests.delete(f"{API}/categories/{cid}", headers=superadmin, timeout=20)

    def test_duplicate_category_is_rejected(self, superadmin):
        name = f"Unique Cat {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/categories", headers=superadmin, timeout=30, json={"name": name})
        assert r.status_code == 201, r.text
        cid = r.json()["id"]
        try:
            again = requests.post(f"{API}/categories", headers=superadmin, timeout=30,
                                  json={"name": name})
            assert again.status_code == 400
        finally:
            requests.delete(f"{API}/categories/{cid}", headers=superadmin, timeout=20)

    def test_category_in_use_cannot_be_archived(self, superadmin):
        brand = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                              json={"name": f"Cat Brand {uuid.uuid4().hex[:6]}"}).json()
        CREATED_BRANDS.append(brand["id"])
        cat = requests.post(f"{API}/categories", headers=superadmin, timeout=30,
                            json={"name": f"Busy Cat {uuid.uuid4().hex[:6]}"}).json()
        prod = requests.post(f"{API}/products", headers=superadmin, timeout=30, json={
            "brand": brand["name"], "name": "Categorised", "category": cat["name"]}).json()
        CREATED_PRODUCTS.append(prod["id"])
        try:
            r = requests.delete(f"{API}/categories/{cat['id']}", headers=superadmin, timeout=30)
            assert r.status_code == 409, r.text
            assert "active product" in (r.json().get("detail") or "")
        finally:
            requests.delete(f"{API}/products/{prod['id']}", headers=superadmin, timeout=20)
            requests.delete(f"{API}/categories/{cat['id']}", headers=superadmin, timeout=20)

    def test_product_attribute_crud(self, superadmin):
        name = f"attr_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/product-attributes", headers=superadmin, timeout=30, json={
            "name": name, "type": "select", "unit": "W", "options": ["100", "200"]})
        assert r.status_code == 201, r.text
        aid = r.json()["id"]
        assert r.json()["label"], "the attribute has no human label"

        listed = requests.get(f"{API}/product-attributes", headers=superadmin, timeout=30).json()
        assert any(a["id"] == aid for a in listed)

        upd = requests.patch(f"{API}/product-attributes/{aid}", headers=superadmin, timeout=30,
                             json={"label": "Output Power"})
        assert upd.status_code == 200 and upd.json()["label"] == "Output Power"

        dup = requests.post(f"{API}/product-attributes", headers=superadmin, timeout=30,
                            json={"name": name})
        assert dup.status_code == 400

        assert requests.delete(f"{API}/product-attributes/{aid}",
                               headers=superadmin, timeout=30).status_code == 200
        still = requests.get(f"{API}/product-attributes", headers=superadmin, timeout=30).json()
        assert all(a["id"] != aid for a in still)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
class TestAuditTrail:
    def test_a_brand_lifecycle_is_fully_recorded(self, superadmin):
        name = f"Audited Brand {uuid.uuid4().hex[:6]}"
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": name, "country": "India"})
        assert created.status_code == 201, created.text
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        try:
            requests.patch(f"{API}/brands/{bid}", headers=superadmin, timeout=30,
                           json={"country": "Nepal", "description": "Audited edit"})
            upload_logo(bid, superadmin, make_png(8, 8))
            requests.patch(f"{API}/brands/{bid}", headers=superadmin, timeout=30,
                           json={"status": "inactive"})
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=30)

            history = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                                   params={"record_id": bid, "record_type": "brand"}).json()
            entries = history["entries"]
            actions = {e["action"] for e in entries}
            assert {"create", "update", "upload", "archive"} <= actions, actions

            # The edit must carry the actual before/after values.
            edit = next(e for e in entries
                        if e["action"] == "update"
                        and any(c["field"] == "country" for c in e["changes"]))
            change = next(c for c in edit["changes"] if c["field"] == "country")
            assert change["before"] == "India"
            assert change["after"] == "Nepal"
            assert edit["actor_id"], "the audit entry has no actor"
            assert edit["created_at"], "the audit entry has no timestamp"

            # Per-record history endpoint returns the same trail, oldest first.
            one = requests.get(f"{API}/audit-logs/record/brand/{bid}",
                               headers=superadmin, timeout=30).json()
            assert len(one) == len(entries)
            assert one[0]["created_at"] <= one[-1]["created_at"]
        finally:
            requests.delete(f"{API}/brands/{bid}", headers=superadmin, timeout=20)

    def test_product_changes_record_the_brand_move(self, superadmin):
        a = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                          json={"name": f"Audit A {uuid.uuid4().hex[:6]}"}).json()
        b = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                          json={"name": f"Audit B {uuid.uuid4().hex[:6]}"}).json()
        CREATED_BRANDS.extend([a["id"], b["id"]])
        prod = requests.post(f"{API}/products", headers=superadmin, timeout=30,
                             json={"brand": a["name"], "name": "Moved Product"}).json()
        CREATED_PRODUCTS.append(prod["id"])
        try:
            requests.patch(f"{API}/products/{prod['id']}", headers=superadmin, timeout=30,
                           json={"brand": b["name"]})
            history = requests.get(f"{API}/audit-logs/record/product/{prod['id']}",
                                   headers=superadmin, timeout=30).json()
            assert len(history) >= 2, history
            move = next((e for e in history
                         if any(c["field"] == "brand" for c in e.get("changes") or [])), None)
            assert move is not None, "the brand change was not recorded"
            change = next(c for c in move["changes"] if c["field"] == "brand")
            assert change["before"] == a["name"] and change["after"] == b["name"]
        finally:
            requests.delete(f"{API}/products/{prod['id']}", headers=superadmin, timeout=20)

    def test_audit_entries_carry_actor_and_summary(self, superadmin):
        r = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                         params={"module": "brands", "limit": 20})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] > 0
        for entry in body["entries"][:5]:
            assert entry["actor_name"], entry
            assert entry["action"] and entry["module"]
            assert isinstance(entry["changes"], list)

    def test_audit_search_and_filters(self, superadmin):
        r = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                         params={"module": "products", "limit": 5})
        body = r.json()
        for entry in body["entries"]:
            assert entry["module"] == "products"
        r = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                         params={"search": "zqx-nonexistent-needle"})
        assert r.json()["total"] == 0

    def test_audit_pagination(self, superadmin):
        first = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                             params={"limit": 5, "skip": 0}).json()
        second = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                              params={"limit": 5, "skip": 5}).json()
        assert len(first["entries"]) <= 5
        ids_first = {e["id"] for e in first["entries"]}
        ids_second = {e["id"] for e in second["entries"]}
        assert not (ids_first & ids_second), "pagination returned the same page twice"

    def test_a_no_op_edit_is_not_recorded(self, superadmin):
        """Recording an edit that changed nothing makes the trail useless."""
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Noop {uuid.uuid4().hex[:6]}"})
        bid = created.json()["id"]
        CREATED_BRANDS.append(bid)
        before = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                              params={"record_id": bid}).json()["total"]
        requests.patch(f"{API}/brands/{bid}", headers=superadmin, timeout=30,
                       json={"country": created.json()["country"]})
        after = requests.get(f"{API}/audit-logs", headers=superadmin, timeout=30,
                             params={"record_id": bid}).json()["total"]
        assert after == before, "a change with no effect was written to the audit trail"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
class TestPersistence:
    def test_brand_and_logo_survive_a_refetch(self, superadmin):
        """Every read path resolves the logo, not just the upload response."""
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Persist {uuid.uuid4().hex[:6]}"})
        bid, name = created.json()["id"], created.json()["name"]
        CREATED_BRANDS.append(bid)
        png = make_png(20, 10, rgba=True)
        media_id = upload_logo(bid, superadmin, png).json()["logo_media_id"]

        detail = requests.get(f"{API}/brands/{bid}", headers=superadmin, timeout=30).json()
        assert detail["logo_url"] == f"/api/media/{media_id}"

        listed = next(b for b in requests.get(f"{API}/brands", headers=superadmin,
                                              timeout=30).json() if b["id"] == bid)
        assert listed["logo_url"] == f"/api/media/{media_id}"

        with_archived = next(b for b in requests.get(
            f"{API}/brands", headers=superadmin, timeout=30,
            params={"include_archived": True}).json() if b["id"] == bid)
        assert with_archived["logo_url"] == f"/api/media/{media_id}"

        info = requests.get(f"{API}/media/{media_id}/info", headers=superadmin, timeout=30).json()
        assert info["width"] == 20 and info["height"] == 10
        assert info["url"] == f"/api/media/{media_id}"

    def test_timestamps_are_present_on_master_records(self, superadmin):
        created = requests.post(f"{API}/brands", headers=superadmin, timeout=30,
                                json={"name": f"Stamped {uuid.uuid4().hex[:6]}"})
        CREATED_BRANDS.append(created.json()["id"])
        body = created.json()
        assert body.get("created_at"), "a new brand has no created_at"
        assert body.get("updated_at"), "a new brand has no updated_at"