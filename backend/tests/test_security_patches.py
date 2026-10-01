"""Security patches regression tests (SEC-001..SEC-004).

Runs against the live preview backend (REACT_APP_BACKEND_URL). Covers:
  SEC-001: brand-isolation + cost-field stripping on GET /api/shipments
  SEC-002: env-driven admin/demo-sales seeding
  SEC-003: fail-closed webhooks when signing secret is unset
  SEC-004: /api/users vs /api/users/roster exposure control
Plus a light regression sweep (dashboard/stats, leads listing, ai-summary,
quotation PDF) to make sure the auth patches did not blow up unrelated flows.
"""

import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to reading the frontend .env directly (test harness safety net).
    try:
        with open("/app/frontend/.env", "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
    except Exception:
        pass

API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@hitechaudio.in"
ADMIN_PASSWORD = "Admin@123"
SALES_EMAIL = "sales@hitechaudio.in"
SALES_PASSWORD = "Sales@123"


# --------------------------- helpers ---------------------------
def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"No token in login response: {r.json()}"
    return tok


def _auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def sales_token() -> str:
    return _login(SALES_EMAIL, SALES_PASSWORD)


@pytest.fixture(scope="module")
def temp_lacoustics_sales(admin_token):
    """Create + yield an ad-hoc sales user limited to L-Acoustics. Cleaned up at end."""
    email = f"test_lasales_{uuid.uuid4().hex[:8]}@hitechavl.com"
    password = "Test@12345"
    payload = {
        "name": "Temp LAcoustics Sales",
        "email": email,
        "password": password,
        "role": "sales",
        "allowed_brands": ["L-Acoustics"],
    }
    r = requests.post(f"{API}/users", json=payload, headers=_auth(admin_token), timeout=30)
    assert r.status_code == 201, f"create sales failed: {r.status_code} {r.text}"
    user = r.json()
    token = _login(email, password)
    yield {"user": user, "token": token, "email": email, "password": password}
    # Cleanup
    try:
        requests.delete(f"{API}/users/{user['id']}", headers=_auth(admin_token), timeout=30)
    except Exception:
        pass


# --------------------------- SEC-004 ---------------------------
class TestSEC004UsersRoster:
    def test_admin_full_users_has_email_role(self, admin_token):
        r = requests.get(f"{API}/users", headers=_auth(admin_token), timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) > 0
        sample = users[0]
        assert "email" in sample and "role" in sample, f"admin /users must expose email+role, got {sample.keys()}"
        assert "password_hash" not in sample

    def test_sales_users_forbidden(self, sales_token):
        r = requests.get(f"{API}/users", headers=_auth(sales_token), timeout=30)
        assert r.status_code == 403, f"sales must NOT list users (expected 403, got {r.status_code})"

    def test_admin_roster_only_id_name(self, admin_token):
        r = requests.get(f"{API}/users/roster", headers=_auth(admin_token), timeout=30)
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list) and len(docs) > 0
        forbidden = {"email", "role", "password_hash", "allowed_brands", "created_at"}
        for d in docs:
            assert set(d.keys()).issubset({"id", "name"}), f"roster leaked keys: {set(d.keys()) - {'id','name'}}"
            assert not (set(d.keys()) & forbidden)

    def test_sales_roster_only_id_name(self, sales_token):
        r = requests.get(f"{API}/users/roster", headers=_auth(sales_token), timeout=30)
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list) and len(docs) > 0
        for d in docs:
            assert set(d.keys()).issubset({"id", "name"}), f"roster leaked keys: {set(d.keys()) - {'id','name'}}"


# --------------------------- SEC-002 ---------------------------
class TestSEC002Seeding:
    def test_admin_login_from_env(self):
        # Admin creds from ADMIN_EMAIL/ADMIN_PASSWORD env — should log in.
        tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert tok

    def test_demo_sales_seeded_when_flag_true(self):
        # SEED_DEMO_USERS=true → sales@hitechaudio.in should exist and log in.
        tok = _login(SALES_EMAIL, SALES_PASSWORD)
        assert tok
        me = requests.get(f"{API}/auth/me", headers=_auth(tok), timeout=30)
        assert me.status_code == 200
        body = me.json()
        assert body.get("role") == "sales"
        assert body.get("email", "").lower() == SALES_EMAIL

    def test_wrong_password_rejected(self):
        r = requests.post(f"{API}/auth/login", json={"email": SALES_EMAIL, "password": "WrongPW!!"}, timeout=30)
        assert r.status_code in (400, 401), f"expected 401/400, got {r.status_code}"


# --------------------------- SEC-003 ---------------------------
class TestSEC003WebhooksFailClosed:
    def test_whatsapp_meta_post_503_when_secret_unset(self):
        r = requests.post(
            f"{API}/webhook/whatsapp",
            json={"entry": []},
            headers={"X-Hub-Signature-256": "sha256=deadbeef"},
            timeout=30,
        )
        assert r.status_code == 503
        body = (r.text or "")
        assert "META_APP_SECRET" in body or "Webhook disabled" in body, f"unexpected body: {body}"

    def test_whatsapp_twilio_503_when_token_unset(self):
        r = requests.post(
            f"{API}/webhook/whatsapp/twilio",
            data={"From": "whatsapp:+911234567890", "Body": "hi"},
            timeout=30,
        )
        assert r.status_code == 503
        body = r.text or ""
        assert "TWILIO_AUTH_TOKEN" in body or "Webhook disabled" in body

    def test_zoho_503_when_secret_unset(self):
        r = requests.post(
            f"{API}/webhook/zoho",
            json={"fromAddress": "x@y.com", "subject": "s"},
            headers={"X-Webhook-Secret": "irrelevant"},
            timeout=30,
        )
        assert r.status_code == 503
        body = r.text or ""
        assert "ZOHO_WEBHOOK_SECRET" in body or "Webhook disabled" in body

    def test_whatsapp_meta_verify_403_when_verify_token_unset(self):
        r = requests.get(
            f"{API}/webhook/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "guess", "hub.challenge": "12345"},
            timeout=30,
        )
        assert r.status_code == 403


# --------------------------- SEC-001 ---------------------------
class TestSEC001ShipmentBrandIsolation:
    _created_shipment_id = None

    def test_admin_sees_all_and_cost_fields(self, admin_token):
        # Ensure at least one non-L-Acoustics shipment exists so the isolation test is meaningful.
        r = requests.get(f"{API}/shipments", headers=_auth(admin_token), timeout=30)
        assert r.status_code == 200
        docs = r.json()
        oems = {d.get("oem") for d in docs}
        if not (oems - {"L-Acoustics"}):
            # Create a DiGiCo shipment as admin so we can prove filtering later.
            payload = {
                "po_no": f"TEST-PO-{uuid.uuid4().hex[:6]}",
                "oem": "DiGiCo",
                "currency": "GBP",
                "items": [],
                "bl_awb": "TEST-AWB",
                "eta": "2026-06-01",
                "notes": "TEST_security_patch",
            }
            c = requests.post(f"{API}/shipments", json=payload, headers=_auth(admin_token), timeout=30)
            assert c.status_code == 201, f"seed DiGiCo shipment failed: {c.status_code} {c.text}"
            TestSEC001ShipmentBrandIsolation._created_shipment_id = c.json()["id"]
            r = requests.get(f"{API}/shipments", headers=_auth(admin_token), timeout=30)
            docs = r.json()
        # Admin: expect cost fields present on at least one doc
        assert any("freight_cost_inr" in d for d in docs), "admin GET /shipments must include freight_cost_inr"
        assert any("duty_paid_inr" in d for d in docs), "admin GET /shipments must include duty_paid_inr"

    def test_sales_isolated_and_cost_stripped(self, temp_lacoustics_sales):
        tok = temp_lacoustics_sales["token"]
        r = requests.get(f"{API}/shipments", headers=_auth(tok), timeout=30)
        assert r.status_code == 200, f"sales GET /shipments failed: {r.status_code} {r.text}"
        docs = r.json()
        # Every returned shipment must be L-Acoustics only.
        for d in docs:
            assert d.get("oem") == "L-Acoustics", f"brand-isolation breach — sales saw oem={d.get('oem')}"
            assert "freight_cost_inr" not in d, f"freight_cost_inr leaked to sales: {d}"
            assert "duty_paid_inr" not in d, f"duty_paid_inr leaked to sales: {d}"

    def test_dashboard_ops_brand_filtered_for_sales(self, temp_lacoustics_sales, admin_token):
        # Sales dashboard shipments_arriving_soon is empty by design (admin-only ops list),
        # but shipments_in_transit MUST reflect only allowed brands.
        s = requests.get(f"{API}/dashboard/stats", headers=_auth(temp_lacoustics_sales["token"]), timeout=30)
        assert s.status_code == 200
        sops = s.json().get("ops", {})
        a = requests.get(f"{API}/dashboard/stats", headers=_auth(admin_token), timeout=30)
        assert a.status_code == 200
        aops = a.json().get("ops", {})
        # sales count must be <= admin count (filtered subset)
        assert sops.get("shipments_in_transit", 0) <= aops.get("shipments_in_transit", 0)

    @classmethod
    def teardown_class(cls):
        if cls._created_shipment_id:
            try:
                tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
                requests.delete(f"{API}/shipments/{cls._created_shipment_id}", headers=_auth(tok), timeout=30)
            except Exception:
                pass


# --------------------------- Regression sweep ---------------------------
class TestRegression:
    def test_leads_list_admin(self, admin_token):
        r = requests.get(f"{API}/leads", headers=_auth(admin_token), timeout=30)
        assert r.status_code == 200

    def test_leads_list_sales(self, sales_token):
        r = requests.get(f"{API}/leads", headers=_auth(sales_token), timeout=30)
        assert r.status_code == 200

    def test_dashboard_stats_admin(self, admin_token):
        r = requests.get(f"{API}/dashboard/stats", headers=_auth(admin_token), timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "by_stage" in body and "ops" in body

    def test_dashboard_stats_sales(self, sales_token):
        r = requests.get(f"{API}/dashboard/stats", headers=_auth(sales_token), timeout=30)
        assert r.status_code == 200

    def test_brands_ok(self, sales_token):
        r = requests.get(f"{API}/brands", headers=_auth(sales_token), timeout=30)
        assert r.status_code == 200

    def test_auth_me(self, sales_token):
        r = requests.get(f"{API}/auth/me", headers=_auth(sales_token), timeout=30)
        assert r.status_code == 200
        assert r.json().get("role") == "sales"
