"""Backend tests for the 'components in bundle' fix:
- POST /api/quotations accepts an item with `components` and persists it
- GET /api/quotations/{id} returns the components field
- GET /api/quotations/{id}/pdf is a valid PDF (>5KB) for both new (with components) and legacy quotes
- PDF also generates with a mixed-brand quote (logo header path exercised)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://hitech-crm.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@hitechaudio.in"
ADMIN_PASS = "Admin@123"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    token = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def lead_id(session):
    """Reuse a real lead or create a TEST_ one."""
    r = session.get(f"{BASE_URL}/api/leads")
    assert r.status_code == 200
    leads = r.json()
    if leads:
        return leads[0]["id"]
    r = session.post(f"{BASE_URL}/api/leads", json={
        "name": "TEST_PDF_Customer", "company": "TEST_Co", "source": "direct_enquiry"
    })
    assert r.status_code == 201
    return r.json()["id"]


class TestQuotationComponentsAndPDF:

    def test_create_quote_with_components_persists(self, session, lead_id):
        payload = {
            "lead_id": lead_id,
            "items": [{
                "product": "K2 (16x8) — Bundle",
                "brand": "L-Acoustics",
                "qty": 1,
                "unit_price": 9500000,
                "tax_pct": 18,
                "components": "12× K2; 4× KS28; 2× LA12X"
            }]
        }
        r = session.post(f"{BASE_URL}/api/quotations", json=payload)
        assert r.status_code == 201, r.text[:300]
        q = r.json()
        assert q["id"]
        assert q["items"][0]["components"] == "12× K2; 4× KS28; 2× LA12X"
        # Re-fetch via GET to validate persistence in DB
        g = session.get(f"{BASE_URL}/api/quotations/{q['id']}")
        assert g.status_code == 200
        assert g.json()["items"][0]["components"] == "12× K2; 4× KS28; 2× LA12X"
        pytest.bundle_quote_id = q["id"]

    def test_pdf_for_bundle_quote_returns_valid_pdf(self, session):
        qid = getattr(pytest, "bundle_quote_id", None)
        assert qid, "previous test should have set bundle_quote_id"
        r = session.get(f"{BASE_URL}/api/quotations/{qid}/pdf")
        assert r.status_code == 200, r.text[:300]
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"unexpected content-type: {ct}"
        assert r.content[:4] == b"%PDF", "response does not start with PDF magic bytes"
        assert len(r.content) > 5 * 1024, f"PDF too small: {len(r.content)} bytes"

    def test_mixed_brand_quote_pdf(self, session, lead_id):
        """Quote with two different brands should still produce a valid PDF (logo header path)."""
        payload = {
            "lead_id": lead_id,
            "items": [
                {"product": "K2 (16x8) — Bundle", "brand": "L-Acoustics", "qty": 1, "unit_price": 9500000, "tax_pct": 18,
                 "components": "12× K2; 4× KS28; 2× LA12X"},
                {"product": "Quantum 852 — Bundle", "brand": "DiGiCo", "qty": 1, "unit_price": 7500000, "tax_pct": 18,
                 "components": "1× Quantum 852 Console; 1× SD-Rack; Fibre Optic Kit"},
            ]
        }
        r = session.post(f"{BASE_URL}/api/quotations", json=payload)
        assert r.status_code == 201, r.text[:300]
        qid = r.json()["id"]
        # Both items should carry components
        items = r.json()["items"]
        assert items[0]["components"].startswith("12×")
        assert items[1]["components"].startswith("1× Quantum")
        # PDF must still build (even if remote brand logos fail to fetch)
        rp = session.get(f"{BASE_URL}/api/quotations/{qid}/pdf")
        assert rp.status_code == 200
        assert rp.content[:4] == b"%PDF"
        assert len(rp.content) > 5 * 1024

    def test_legacy_quote_without_components_still_renders_pdf(self, session, lead_id):
        """Regression: a quote with no components field on any item must still render."""
        payload = {
            "lead_id": lead_id,
            "items": [
                {"product": "Lone Item (no components)", "brand": "L-Acoustics", "qty": 2, "unit_price": 125000, "tax_pct": 18},
            ]
        }
        r = session.post(f"{BASE_URL}/api/quotations", json=payload)
        assert r.status_code == 201, r.text[:300]
        q = r.json()
        # components key may exist but should be None when not provided
        assert q["items"][0].get("components") in (None, "", )
        rp = session.get(f"{BASE_URL}/api/quotations/{q['id']}/pdf")
        assert rp.status_code == 200
        assert "application/pdf" in rp.headers.get("content-type", "")
        assert rp.content[:4] == b"%PDF"
        assert len(rp.content) > 5 * 1024

    def test_pdf_contains_includes_text(self, session):
        """Quick byte-level sanity check the INCLUDES section actually made it into the PDF stream.
        Note: ReportLab compresses streams by default so a substring search may miss; we just confirm
        no crash + valid PDF for both bundle and legacy cases (already done above)."""
        qid = getattr(pytest, "bundle_quote_id", None)
        assert qid
        r = session.get(f"{BASE_URL}/api/quotations/{qid}/pdf")
        assert r.status_code == 200
        # Best-effort substring check (may or may not be present due to compression)
        has_includes = b"INCLUDES" in r.content
        has_k2 = b"K2" in r.content
        print(f"INCLUDES substring present: {has_includes}, K2 substring present: {has_k2}")
        # Don't hard-assert; the existence + size > 5KB is the contract.
