"""Regression test for the brand catalogue, generated email and health endpoint.

Covers the guarantees the business asked for:
  * the catalogue is exactly the 21 approved brands, from the database
  * archived brands and their products never appear in the active listings
  * every dropdown-visible brand carries an official website
  * a contact saved without an email gets a valid, unique, generated one
  * a real email is never overwritten
  * /health reports the database without leaking configuration
  * stored credentials are never returned to the browser
"""
import os
import re
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL, ADMIN_PASSWORD = "admin@hitechaudio.in", "Admin@123"

APPROVED = [
    "RCF", "L-Acoustics", "DiGiCo", "TT+ Audio", "Sound Devices", "Klang Technologies",
    "Radial Engineering", "Fourier Audio", "Audio Press Box", "MA Lighting", "MADRIX", "ETC",
    "Zactrack", "Luminex", "Klotz", "K&M", "Sennheiser", "Cotodama", "DPA Microphones",
    "JH Audio", "Wisycom",
]

CREATED: list = []


def _auth() -> dict:
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json().get('access_token') or r.json()['token']}"}


@pytest.fixture(scope="module")
def admin() -> dict:
    return _auth()


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    h = _auth()
    for coll, cid in CREATED:
        requests.delete(f"{API}/{coll}/{cid}", headers=h, timeout=15)
    CREATED.clear()


# ---------------------------------------------------------------------------
# Brand catalogue
# ---------------------------------------------------------------------------
class TestApprovedBrandList:
    def test_exactly_the_21_approved_brands(self, admin):
        brands = requests.get(f"{API}/brands", headers=admin, timeout=30).json()
        names = sorted(b["name"] for b in brands)
        assert len(brands) == 21, f"expected 21 brands, got {len(brands)}: {names}"
        assert names == sorted(APPROVED), (
            f"catalogue does not match the approved master list.\n"
            f"  missing: {sorted(set(APPROVED) - set(names))}\n"
            f"  extra  : {sorted(set(names) - set(APPROVED))}")

    def test_every_brand_has_an_official_website(self, admin):
        brands = requests.get(f"{API}/brands", headers=admin, timeout=30).json()
        missing = [b["name"] for b in brands if not (b.get("official_website") or "").startswith("http")]
        assert not missing, f"brands without an official website: {missing}"

    def test_every_brand_has_a_unique_slug(self, admin):
        brands = requests.get(f"{API}/brands", headers=admin, timeout=30).json()
        slugs = [b["slug"] for b in brands]
        assert all(slugs), "a brand has no slug"
        assert len(set(slugs)) == len(slugs), f"duplicate slugs: {slugs}"

    def test_brand_detail_reports_product_count(self, admin):
        brands = requests.get(f"{API}/brands", headers=admin, timeout=30).json()
        r = requests.get(f"{API}/brands/{brands[0]['id']}", headers=admin, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == brands[0]["name"]
        assert isinstance(body["product_count"], int)

    def test_unknown_brand_detail_is_404(self, admin):
        r = requests.get(f"{API}/brands/{uuid.uuid4()}", headers=admin, timeout=30)
        assert r.status_code == 404

    def test_brands_require_authentication(self):
        assert requests.get(f"{API}/brands", timeout=30).status_code == 401

    def test_sales_rep_only_sees_allowed_brands(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "sales@hitechaudio.in", "password": "Sales@123"}, timeout=30)
        if r.status_code != 200:
            pytest.skip("demo sales account not configured")
        h = {"Authorization": f"Bearer {r.json().get('access_token') or r.json()['token']}"}
        brands = requests.get(f"{API}/brands", headers=h, timeout=30).json()
        for b in brands:
            assert "locked" in b, "brand listing must expose the per-rep lock flag"
            if b["locked"]:
                prods = requests.get(f"{API}/products", params={"brand": b["name"]},
                                     headers=h, timeout=30).json()
                assert prods == [], f"locked brand {b['name']} still returned products"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
class TestProductCatalogue:
    def test_no_product_belongs_to_an_unapproved_brand(self, admin):
        prods = requests.get(f"{API}/products", headers=admin, timeout=60).json()
        offenders = sorted({p["brand"] for p in prods} - set(APPROVED))
        assert not offenders, f"products of unapproved brands are active: {offenders}"

    def test_no_archived_product_is_listed(self, admin):
        prods = requests.get(f"{API}/products", headers=admin, timeout=60).json()
        bad = [p["name"] for p in prods if p.get("status") == "archived"]
        assert not bad, f"archived products leaked into the listing: {bad[:5]}"

    def test_product_search_finds_a_known_model(self, admin):
        prods = requests.get(f"{API}/products", headers=admin, timeout=60).json()
        assert prods, "catalogue is empty; search cannot be exercised"
        model = next((p.get("model_number") for p in prods if p.get("model_number")), None)
        if not model:
            pytest.skip("no product carries a model number yet")
        hits = requests.get(f"{API}/products", params={"search": model},
                            headers=admin, timeout=30).json()
        assert hits, f"search for a real model number ({model}) returned nothing"

    def test_regex_metacharacters_do_not_break_product_search(self, admin):
        for bad in ["(", "[", ".*", "\\", "a{999999}", "+", "?"]:
            r = requests.get(f"{API}/products", params={"search": bad},
                             headers=admin, timeout=30)
            assert r.status_code == 200, f"{bad!r} -> {r.status_code}"

    def test_product_detail_resolves_brand_and_category(self, admin):
        prods = requests.get(f"{API}/products", headers=admin, timeout=60).json()
        with_links = [p for p in prods if p.get("brand_id")]
        if not with_links:
            pytest.skip("no linked products yet")
        r = requests.get(f"{API}/products/{with_links[0]['id']}", headers=admin, timeout=30)
        assert r.status_code == 200
        assert r.json()["brand_doc"]["name"] == with_links[0]["brand"]

    def test_product_cannot_be_created_for_an_unapproved_brand(self, admin):
        r = requests.post(f"{API}/products", headers=admin, timeout=30, json={
            "brand": "Definitely Not A Real Brand", "name": "Test Widget"})
        assert r.status_code == 400, r.text
        assert "approved brand" in (r.json().get("detail") or "").lower()

    def test_duplicate_sku_is_rejected(self, admin):
        prods = requests.get(f"{API}/products", headers=admin, timeout=60).json()
        with_sku = [p for p in prods if p.get("sku")]
        if not with_sku:
            pytest.skip("no product carries a SKU yet")
        r = requests.post(f"{API}/products", headers=admin, timeout=30, json={
            "brand": with_sku[0]["brand"], "name": "Duplicate SKU Attempt",
            "sku": with_sku[0]["sku"]})
        assert r.status_code == 400, r.text

    def test_categories_endpoint_lists_the_taxonomy(self, admin):
        cats = requests.get(f"{API}/categories", headers=admin, timeout=30).json()
        assert cats, "no product categories"
        for c in cats:
            assert c["name"] and c["slug"]
            assert isinstance(c["product_count"], int)


# ---------------------------------------------------------------------------
# Generated email
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


class TestGeneratedEmail:
    @pytest.mark.parametrize("name,expected_local", [
        ("Shahnawaz Siddiqui", "shahnawaz.siddiqui"),
        ("Rahul Kumar Singh", "rahul.kumar.singh"),
        ("Anne-Marie O'Brien", "anne-marie.obrien"),
        ("  Dr.  R K  Sharma  Jr. ", "dr.r.k.sharma.jr"),
    ])
    def test_name_becomes_a_valid_address(self, admin, name, expected_local):
        r = requests.post(f"{API}/contacts", headers=admin, timeout=30, json={"name": name})
        assert r.status_code in (200, 201), r.text
        doc = r.json()
        CREATED.append(("contacts", doc["id"]))
        local = doc["email"].split("@")[0]
        assert local == expected_local, f"{name!r} -> {doc['email']}"
        assert EMAIL_RE.match(doc["email"]), f"invalid address: {doc['email']}"
        assert doc.get("email_generated") is True

    def test_generated_addresses_are_unique(self, admin):
        emails = []
        for _ in range(3):
            r = requests.post(f"{API}/contacts", headers=admin, timeout=30,
                              json={"name": "Repeated Person Name"})
            assert r.status_code in (200, 201), r.text
            doc = r.json()
            CREATED.append(("contacts", doc["id"]))
            emails.append(doc["email"])
        assert len(set(emails)) == 3, f"duplicate addresses generated: {emails}"

    def test_a_real_email_is_never_replaced(self, admin):
        supplied = f"real.person+{uuid.uuid4().hex[:6]}@vendor.example"
        r = requests.post(f"{API}/contacts", headers=admin, timeout=30,
                          json={"name": "Real Person", "email": supplied})
        doc = r.json()
        CREATED.append(("contacts", doc["id"]))
        assert doc["email"] == supplied
        assert doc.get("email_generated") is None

    def test_customers_get_a_generated_address_too(self, admin):
        r = requests.post(f"{API}/customers", headers=admin, timeout=30,
                          json={"name": "Generated Customer Person"})
        assert r.status_code in (200, 201), r.text
        doc = r.json()
        CREATED.append(("customers", doc["id"]))
        assert EMAIL_RE.match(doc["email"]), doc["email"]
        assert doc.get("email_generated") is True


# ---------------------------------------------------------------------------
# Health + secret hygiene
# ---------------------------------------------------------------------------
class TestHealthAndSecrets:
    def test_health_reports_database_status(self):
        r = requests.get(f"{BASE_URL}/health", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ok"
        assert body["database"] == "connected"

    def test_health_needs_no_credentials(self):
        # A platform health check has no CRM token; this must still work.
        assert requests.get(f"{BASE_URL}/health", timeout=15).status_code == 200

    def test_health_does_not_leak_configuration(self):
        raw = requests.get(f"{BASE_URL}/health", timeout=15).text
        for secret in ("mongodb://", "JWT_SECRET", "password", "DB_NAME"):
            assert secret not in raw, f"/health leaked {secret!r}"

    def test_stored_email_credentials_are_masked(self, admin):
        body = requests.get(f"{API}/resend/settings", headers=admin, timeout=30).json()
        for field in ("smtp_password", "resend_api_key"):
            assert body.get(field, "") in ("", "********"), \
                f"{field} was returned in plaintext"
            assert f"{field}_set" in body, f"{field}_set flag missing"

    def test_saving_other_fields_preserves_the_stored_password(self, admin):
        before = requests.get(f"{API}/resend/settings", headers=admin, timeout=30).json().get("smtp_password_set")
        r = requests.post(f"{API}/resend/settings", headers=admin, timeout=30,
                          json={"sender_name": "Regression Test"})
        assert r.status_code == 200, r.text
        after = requests.get(f"{API}/resend/settings", headers=admin, timeout=30).json().get("smtp_password_set")
        assert before == after, "an unrelated save cleared the stored SMTP password status"
        requests.post(f"{API}/resend/settings", headers=admin, timeout=30,
                      json={"sender_name": "Hi-Tech Audio & Image LLP"})

    def test_protected_endpoints_reject_anonymous_callers(self):
        for path in ("/api/products", "/api/customers", "/api/contacts",
                     "/api/leads", "/api/inventory", "/api/quotations",
                     "/api/search", "/api/dashboard/stats"):
            r = requests.get(f"{BASE_URL}{path}", timeout=15)
            assert r.status_code == 401, f"{path} returned {r.status_code} without a token"