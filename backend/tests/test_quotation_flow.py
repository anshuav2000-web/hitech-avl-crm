"""Phase 5 quotation flow: configured stages, numbering, duplicate, share, approval.

These lock in the defects found during Phase 5:

1. ``create_quotation`` used to hard-code the lead stage ``"quoted"``, which is not
   one of the configured pipeline stages -- quoting a lead made it vanish from the
   Kanban board.
2. Quote numbering was ``1000 + count + 1``, which collided with an existing number
   once a quotation was deleted.
3. A share token was minted but nothing ever exposed it to the customer, and the
   public projection had no addressee because quotations never snapshotted the
   client party.

Run with the API up and REACT_APP_BACKEND_URL set, e.g.
    $env:REACT_APP_BACKEND_URL="http://localhost:8000"; python -m pytest tests -q
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL, ADMIN_PASSWORD = "admin@hitechaudio.in", "Admin@123"
SALES_EMAIL, SALES_PASSWORD = "sales@hitechaudio.in", "Sales@123"

SESSION = requests.Session()
CREATED_QUOTES: list = []
CREATED_LEADS: list = []


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json()["token"]


def _h(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin() -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_login(ADMIN_EMAIL, ADMIN_PASSWORD)}"
    return s


@pytest.fixture(scope="module")
def sales() -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_login(SALES_EMAIL, SALES_PASSWORD)}"
    return s


@pytest.fixture(scope="module")
def stages(admin: requests.Session) -> set:
    """Every stage the live configuration actually defines."""
    return {s["id"] for s in admin.get(f"{API}/config/lead_stages").json()["items"]}


def _new_lead(admin: requests.Session, name: str, unowned: bool = False) -> str:
    r = admin.post(f"{API}/leads", json={"name": name, "source": "direct_enquiry"})
    assert r.status_code in (200, 201), r.text
    lead = r.json()
    CREATED_LEADS.append(lead["id"])
    if unowned:
        # _auto_assign() hands new leads to the least-loaded sales rep, so an
        # isolation test has to explicitly detach the lead.
        assert admin.patch(f"{API}/leads/{lead['id']}", json={"assigned_to": None}).status_code == 200
    return lead["id"]


def _new_quote(admin: requests.Session, lead_id: str, qty: int = 2) -> dict:
    r = admin.post(f"{API}/quotations", json={
        "lead_id": lead_id,
        "items": [{"product": "K2 Line Array", "brand": "L-Acoustics",
                   "qty": qty, "unit_price": 250000, "tax_pct": 18}],
    })
    assert r.status_code in (200, 201), r.text
    q = r.json()
    CREATED_QUOTES.append(q["id"])
    return q


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    """Never leave probe rows behind in the dev database."""
    yield
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    for qid in CREATED_QUOTES:
        SESSION.delete(f"{API}/quotations/{qid}", headers=_h(tok), timeout=15)
    for lid in CREATED_LEADS:
        SESSION.delete(f"{API}/leads/{lid}", headers=_h(tok), timeout=15)
    CREATED_QUOTES.clear()
    CREATED_LEADS.clear()


class TestConfiguredStage:
    def test_quoting_does_not_use_a_phantom_stage(self, admin, stages):
        lead_id = _new_lead(admin, "P5 Configured Stage")
        _new_quote(admin, lead_id)
        stage = admin.get(f"{API}/leads/{lead_id}").json()["stage"]
        assert stage in stages, f"lead moved to unconfigured stage {stage!r}"

    def test_lead_stays_on_the_board(self, admin, stages):
        lead_id = _new_lead(admin, "P5 Stays Visible")
        _new_quote(admin, lead_id)
        stage = admin.get(f"{API}/leads/{lead_id}").json()["stage"]
        assert stage == "convert_to_quotation"


class TestQuoteNumbering:
    def test_numbering_survives_deletions(self, admin):
        lead_id = _new_lead(admin, "P5 Numbering")
        first = _new_quote(admin, lead_id)
        assert admin.delete(f"{API}/quotations/{first['id']}").status_code in (200, 204)
        CREATED_QUOTES.remove(first["id"])

        second = _new_quote(admin, lead_id)
        numbers = [q["quote_no"] for q in admin.get(f"{API}/quotations").json()]
        assert len(numbers) == len(set(numbers)), "quote_no collided after a delete"

    def test_duplicate_gets_a_fresh_number(self, admin):
        lead_id = _new_lead(admin, "P5 Dup Number")
        src = _new_quote(admin, lead_id)
        r = admin.post(f"{API}/quotations/{src['id']}/duplicate")
        assert r.status_code in (200, 201), r.text
        dup = r.json()
        CREATED_QUOTES.append(dup["id"])
        assert dup["quote_no"] != src["quote_no"]


class TestDuplicate:
    def test_duplicate_is_an_independent_draft(self, admin):
        lead_id = _new_lead(admin, "P5 Dup Shape")
        src = _new_quote(admin, lead_id)
        dup = admin.post(f"{API}/quotations/{src['id']}/duplicate").json()
        CREATED_QUOTES.append(dup["id"])

        assert dup["id"] != src["id"]
        assert dup["status"] == "draft"
        assert dup["duplicated_from"] == src["quote_no"]
        assert len(dup["items"]) == len(src["items"])

    def test_duplicate_does_not_inherit_share_token(self, admin):
        lead_id = _new_lead(admin, "P5 Dup Token")
        src = _new_quote(admin, lead_id)
        admin.post(f"{API}/quotations/{src['id']}/share", json={"channel": "link"})
        dup = admin.post(f"{API}/quotations/{src['id']}/duplicate").json()
        CREATED_QUOTES.append(dup["id"])
        assert not dup.get("share_token")

    def test_addressee_snapshot_is_carried_over(self, admin):
        lead_id = _new_lead(admin, "P5 Snap Carry")
        src = _new_quote(admin, lead_id)
        dup = admin.post(f"{API}/quotations/{src['id']}/duplicate").json()
        CREATED_QUOTES.append(dup["id"])
        assert dup.get("client_name") == src.get("client_name")


class TestShare:
    def test_link_share_returns_a_usable_token(self, admin):
        lead_id = _new_lead(admin, "P5 Share Link")
        q = _new_quote(admin, lead_id)
        r = admin.post(f"{API}/quotations/{q['id']}/share", json={"channel": "link"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["share_token"]
        assert f"/public/quotation/{data['share_token']}" in data["public_url"]

    def test_whatsapp_share_builds_a_wa_me_link(self, admin):
        lead_id = _new_lead(admin, "P5 Share WhatsApp")
        q = _new_quote(admin, lead_id)
        data = admin.post(f"{API}/quotations/{q['id']}/share",
                          json={"channel": "whatsapp", "recipient": "+91 98765 43210"}).json()
        assert data["url"].startswith("https://wa.me/919876543210?text=")
        assert q["quote_no"] in data["url"]

    def test_whatsapp_requires_a_number(self, admin):
        lead_id = _new_lead(admin, "P5 Share NoNumber")
        q = _new_quote(admin, lead_id)
        r = admin.post(f"{API}/quotations/{q['id']}/share", json={"channel": "whatsapp"})
        assert r.status_code == 422, r.text

    def test_print_share_returns_the_pdf_path(self, admin):
        lead_id = _new_lead(admin, "P5 Share Print")
        q = _new_quote(admin, lead_id)
        data = admin.post(f"{API}/quotations/{q['id']}/share", json={"channel": "print"}).json()
        assert data["pdf_path"].endswith(f"/quotations/{q['id']}/pdf")


class TestPublicView:
    def test_public_link_is_unauthenticated(self, admin):
        lead_id = _new_lead(admin, "P5 Public Open")
        q = _new_quote(admin, lead_id)
        tok = admin.post(f"{API}/quotations/{q['id']}/share", json={"channel": "link"}).json()["share_token"]

        r = requests.get(f"{API}/public/quotation/{tok}", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quote_no"] == q["quote_no"]
        assert "items" in body and body["total"] == q["total"]

    def test_unknown_token_is_rejected(self):
        r = requests.get(f"{API}/public/quotation/deadbeef0000", timeout=30)
        assert r.status_code == 404

    def test_public_view_never_exposes_lead_contact_details(self, admin):
        lead = admin.post(f"{API}/leads", json={
            "name": "P5 Public Privacy", "company": "Sunrise Events",
            "email": "buyer@sunriseevents.in", "phone": "9876500000",
            "source": "direct_enquiry",
        }).json()
        CREATED_LEADS.append(lead["id"])
        q = _new_quote(admin, lead["id"])
        tok = admin.post(f"{API}/quotations/{q['id']}/share", json={"channel": "link"}).json()["share_token"]

        raw = requests.get(f"{API}/public/quotation/{tok}", timeout=30).text
        assert "buyer@sunriseevents.in" not in raw
        assert "9876500000" not in raw
        assert "lead_id" not in raw

    def test_quotation_snapshots_the_addressee(self, admin):
        """A quote is a contractual document: it must keep naming the right party."""
        lead = admin.post(f"{API}/leads", json={
            "name": "P5 Snapshot", "company": "Sunrise Events", "source": "direct_enquiry",
        }).json()
        CREATED_LEADS.append(lead["id"])
        q = _new_quote(admin, lead["id"])
        assert q.get("client_name") == lead["name"]
        assert q.get("company_name") == lead["company"]

    def test_shared_link_shows_the_addressee(self, admin):
        lead = admin.post(f"{API}/leads", json={
            "name": "P5 Snapshot View", "company": "Sunrise Events", "source": "direct_enquiry",
        }).json()
        CREATED_LEADS.append(lead["id"])
        q = _new_quote(admin, lead["id"])
        tok = admin.post(f"{API}/quotations/{q['id']}/share", json={"channel": "link"}).json()["share_token"]

        body = requests.get(f"{API}/public/quotation/{tok}", timeout=30).json()
        assert body["client_name"] == lead["name"]
        assert body["company_name"] == lead["company"]


class TestApproval:
    def test_full_ladder_records_who_and_why(self, admin, stages):
        lead_id = _new_lead(admin, "P5 Approval")
        q = _new_quote(admin, lead_id)
        qid = q["id"]
        assert admin.get(f"{API}/quotations/{qid}").json()["status"] == "draft"

        r = admin.post(f"{API}/quotations/{qid}/approval", json={"action": "submit"}).json()
        assert r["status"] == "under_review"

        r = admin.post(f"{API}/quotations/{qid}/approval",
                       json={"action": "approve", "note": "Approved by MD"}).json()
        assert r["status"] == "accepted"
        assert r.get("approved_by_name")
        assert r.get("approval_note") == "Approved by MD"

        assert admin.post(f"{API}/quotations/{qid}/approval", json={"action": "reopen"}).json()["status"] == "draft"
        r = admin.post(f"{API}/quotations/{qid}/approval",
                       json={"action": "reject", "note": "Too expensive"}).json()
        assert r["status"] == "rejected"

    def test_approval_advances_the_lead_to_the_won_stage(self, admin, stages):
        lead_id = _new_lead(admin, "P5 Approval Stage")
        q = _new_quote(admin, lead_id)
        admin.post(f"{API}/quotations/{q['id']}/approval", json={"action": "submit"})
        admin.post(f"{API}/quotations/{q['id']}/approval", json={"action": "approve"})

        stage = admin.get(f"{API}/leads/{lead_id}").json()["stage"]
        assert stage in stages
        assert stage == "quotation_confirmed"

        history = admin.get(f"{API}/leads/{lead_id}/stage-history").json()["history"]
        assert history[-1]["to_stage"] == "quotation_confirmed"


class TestQuotationIsolation:
    """A sales rep must not touch a quotation that is not theirs."""

    def test_unowned_quotation_is_off_limits(self, admin, sales):
        lead_id = _new_lead(admin, "P5 Unowned", unowned=True)
        q = _new_quote(admin, lead_id)
        qid = q["id"]

        assert sales.post(f"{API}/quotations/{qid}/duplicate").status_code == 403
        assert sales.post(f"{API}/quotations/{qid}/approval", json={"action": "approve"}).status_code == 403
        assert sales.post(f"{API}/quotations/{qid}/share", json={"channel": "link"}).status_code == 403

    def test_admin_is_never_blocked(self, admin):
        lead_id = _new_lead(admin, "P5 Admin Pass", unowned=True)
        q = _new_quote(admin, lead_id)
        assert admin.post(f"{API}/quotations/{q['id']}/duplicate").status_code in (200, 201)