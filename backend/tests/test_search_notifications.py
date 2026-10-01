"""Phase 9: global search, notifications, activity timeline.

Fixes the audit's remaining defects:

* **B6** - the sales branch of ``/api/search`` ignored ``q`` for quotations and
  returned every quotation the rep owned, so any keystroke dumped their whole book
  into the results panel.
* **B10** - the header overlay filtered a hard-coded page list and never called
  ``/api/search`` at all, so global search could not find a single record.
* **B11** - the notification bell was a hard-coded red dot wired to nothing.

Also pins two regressions found while fixing these: unescaped ``$regex`` input, and
whole-document projections that leaked internal lead notes into search results.
"""

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL, ADMIN_PASSWORD = "admin@hitechaudio.in", "Admin@123"
SALES_EMAIL, SALES_PASSWORD = "sales@hitechaudio.in", "Sales@123"
# Every seeded account (demo and real) shares this password, so a test can log in as
# whichever rep round-robin actually assigned a lead to.
SALES_DEMO_PASSWORD = os.environ.get("SALES_DEMO_PASSWORD", "Sales@123")

CREATED_QUOTES: list = []
CREATED_LEADS: list = []


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json()["token"]


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


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    for qid in CREATED_QUOTES:
        requests.delete(f"{API}/quotations/{qid}", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    for lid in CREATED_LEADS:
        requests.delete(f"{API}/leads/{lid}", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    CREATED_QUOTES.clear()
    CREATED_LEADS.clear()


@pytest.fixture(scope="module")
def needle() -> str:
    """A token that cannot collide with real data."""
    return f"Zq{uuid.uuid4().hex[:10]}"


@pytest.fixture
def lead(admin, needle) -> dict:
    r = admin.post(f"{API}/leads", json={
        "name": f"{needle} Client", "company": f"{needle} Pvt",
        "email": f"{needle}@example.in", "source": "direct_enquiry",
        "notes": "INTERNAL-SECRET-NOTE",
    })
    assert r.status_code in (200, 201), r.text
    doc = r.json()
    CREATED_LEADS.append(doc["id"])
    return doc


def _session_as(admin: requests.Session, user_id) -> requests.Session:
    """Log in as whichever user actually owns a record.

    Round-robin spreads new leads across every sales rep, so any test that needs
    "the rep who watches this lead" has to resolve the owner rather than assume the
    one fixed demo account.
    """
    assert user_id, "record has no assignee"
    users = admin.get(f"{API}/users").json()
    match = next((u for u in users if u["id"] == user_id), None)
    assert match, f"no user with id {user_id}"
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_login(match['email'], SALES_DEMO_PASSWORD)}"
    return s


@pytest.fixture
def quote(admin, lead, needle) -> dict:
    r = admin.post(f"{API}/quotations", json={
        "lead_id": lead["id"],
        "items": [{"product": f"{needle} Speaker", "qty": 1, "unit_price": 1000, "tax_pct": 18}],
    })
    assert r.status_code in (200, 201), r.text
    doc = r.json()
    CREATED_QUOTES.append(doc["id"])
    return doc


class TestSearchFindsThings:
    def test_admin_finds_lead_and_quotation(self, admin, lead, quote):
        r = admin.get(f"{API}/search", params={"q": lead["name"].split()[0]})
        assert r.status_code == 200, r.text
        keys = {c["key"] for c in r.json()["categories"]}
        assert "leads" in keys
        assert "quotations" in keys

    def test_results_are_categorised(self, admin, lead):
        body = admin.get(f"{API}/search", params={"q": lead["name"].split()[0]}).json()
        assert body["categories"]
        assert all(c.get("label") for c in body["categories"])
        assert body["total"] == sum(len(c["items"]) for c in body["categories"])

    def test_types_filter_narrows(self, admin, quote):
        term = quote["quote_no"]
        body = admin.get(f"{API}/search", params={"q": term, "types": "quotations"}).json()
        assert {c["key"] for c in body["categories"]} <= {"quotations"}

    def test_short_query_returns_nothing(self, admin):
        assert admin.get(f"{API}/search", params={"q": "a"}).json()["total"] == 0


class TestB6SearchLeak:
    """The original defect: the sales branch ignored q and returned every quote."""

    def test_no_match_returns_no_quotations_for_sales(self, sales):
        body = sales.get(f"{API}/search", params={"q": "zzz_no_such_record_zzz"}).json()
        assert "quotations" not in {c["key"] for c in body["categories"]}
        assert body["total"] == 0

    def test_no_match_returns_no_leads_for_sales(self, sales):
        body = sales.get(f"{API}/search", params={"q": "zzz_no_such_record_zzz"}).json()
        assert "leads" not in {c["key"] for c in body["categories"]}

    def test_every_returned_hit_actually_matches_the_term(self, sales, lead):
        term = lead["name"].split()[0]
        body = sales.get(f"{API}/search", params={"q": term}).json()
        for cat in body["categories"]:
            for item in cat["items"]:
                assert term.lower() in str(item).lower()

    def test_sales_cannot_search_up_other_reps_leads(self, admin, sales, needle):
        unowned = admin.post(f"{API}/leads", json={"name": f"{needle} Hidden",
                                                   "source": "direct_enquiry"}).json()
        CREATED_LEADS.append(unowned["id"])
        admin.patch(f"{API}/leads/{unowned['id']}", json={"assigned_to": None})

        ids = {i["id"] for c in sales.get(f"{API}/search", params={"q": f"{needle} Hidden"}).json()["categories"]
               for i in c["items"]}
        assert unowned["id"] not in ids


class TestSearchSafetyAndPrivacy:
    @pytest.mark.parametrize("bad", ["(", "[", ".*", "\\", "(((", "a{999999}", "+", "?"])
    def test_regex_metacharacters_do_not_500(self, admin, bad):
        r = admin.get(f"{API}/search", params={"q": bad})
        assert r.status_code == 200, r.text

    def test_results_never_include_internal_notes(self, sales, lead):
        raw = sales.get(f"{API}/search", params={"q": lead["name"].split()[0]}).text
        assert "INTERNAL-SECRET-NOTE" not in raw

    def test_projection_is_explicit(self, admin, lead):
        body = admin.get(f"{API}/search", params={"q": lead["name"].split()[0]}).json()
        for cat in body["categories"]:
            for item in cat["items"]:
                assert "_id" not in item


class TestNotificationsFire:
    def test_unread_count_is_an_integer(self, admin):
        body = admin.get(f"{API}/notifications/unread-count").json()
        assert isinstance(body["unread_count"], int)

    def test_stage_move_notifies_the_watching_rep(self, admin, sales, lead):
        """Assert against whoever actually owns the lead.

        Round-robin assigns new leads across every sales rep, so assuming the fixed
        demo sales account owns it breaks as soon as more reps exist. Read
        assigned_to and log in as that person.
        """
        owner = _session_as(admin, lead["assigned_to"])
        before = owner.get(f"{API}/notifications/unread-count").json()["unread_count"]
        admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "qualified", "notes": "Budget ok"})
        after = owner.get(f"{API}/notifications/unread-count").json()["unread_count"]
        assert after > before, f"{before} -> {after}"

    def test_actor_is_not_notified_about_their_own_action(self, admin, lead):
        admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "contacted"})
        assert admin.get(f"{API}/notifications/unread-count").json()["unread_count"] == 0

    def test_notification_carries_link_and_entity(self, admin, sales, lead):
        admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "interested"})
        owner = _session_as(admin, lead["assigned_to"])
        notes = owner.get(f"{API}/notifications", params={"read": False}).json()
        mine = [n for n in notes if (n.get("entity") or {}).get("id") == lead["id"]]
        assert mine, "no notification carried the lead reference"
        assert all(n.get("link") for n in mine)


class TestActivityTimeline:
    def test_timeline_loads_for_a_lead(self, admin, lead):
        r = admin.get(f"{API}/activity-timeline", params={"lead_id": lead["id"]})
        assert r.status_code == 200, r.text
        assert "count" in r.json()

    def test_stage_change_is_recorded_in_the_timeline(self, admin, lead):
        admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "need_analysis"})
        acts = admin.get(f"{API}/activity-timeline", params={"lead_id": lead["id"]}).json()["activity"]
        assert any(a["type"] == "stage_change" for a in acts)

    def test_one_move_writes_exactly_one_activity(self, admin, lead):
        """Regression: move_lead_stage used to write a second, duplicate 'note' entry."""
        admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "boq_creation"})
        acts = admin.get(f"{API}/activity-timeline", params={"lead_id": lead["id"]}).json()["activity"]
        moves = [a for a in acts if a.get("to_stage") == "boq_creation"]
        assert len(moves) == 1, len(moves)

    def test_timeline_is_scoped_to_the_record(self, admin, lead):
        acts = admin.get(f"{API}/activity-timeline", params={"lead_id": lead["id"]}).json()["activity"]
        assert all(a["lead_id"] == lead["id"] for a in acts if a.get("lead_id"))

    def test_sales_timeline_is_scoped_to_their_own_leads(self, admin, sales, needle):
        hidden = admin.post(f"{API}/leads", json={"name": f"{needle} Secret",
                                                  "source": "direct_enquiry"}).json()
        CREATED_LEADS.append(hidden["id"])
        admin.patch(f"{API}/leads/{hidden['id']}", json={"assigned_to": None})
        acts = sales.get(f"{API}/activity-timeline", params={"limit": 200}).json()["activity"]
        assert not any(a.get("lead_id") == hidden["id"] for a in acts)