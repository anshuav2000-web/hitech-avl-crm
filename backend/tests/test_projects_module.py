"""Phases 7 and 8: projects module, project detail, contacts, integrations, and B12.

B12 was the original audit's "dead code" finding: ``LeadStageUpdate`` and
``LeadSourceCreate`` existed as Pydantic models with no route ever using them. These
tests pin the endpoints that now consume them, plus the two real defects found while
building the project module:

1. ``TaskCreate`` had no ``project_id``, so a task could never link to a project.
2. ``create_project`` never issued a ``project_no``; ``m005`` only backfilled rows
   that already existed, so every newly created project came out unnumbered.
"""

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL, ADMIN_PASSWORD = "admin@hitechaudio.in", "Admin@123"

CREATED_PROJECTS: list = []
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


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    for pid in CREATED_PROJECTS:
        requests.delete(f"{API}/projects/{pid}", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    for lid in CREATED_LEADS:
        requests.delete(f"{API}/leads/{lid}", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    CREATED_PROJECTS.clear()
    CREATED_LEADS.clear()


@pytest.fixture(scope="module")
def project_stages(admin: requests.Session) -> list:
    return [s["id"] for s in admin.get(f"{API}/config/project_stages").json()["items"]]


@pytest.fixture
def project(admin: requests.Session) -> dict:
    r = admin.post(f"{API}/projects", json={
        "name": "P7 Test Festival AV", "client": "Sunrise Events",
        "budget": 500000, "start_date": "2026-10-01",
    })
    assert r.status_code in (200, 201), r.text
    proj = r.json()
    CREATED_PROJECTS.append(proj["id"])
    return proj


@pytest.fixture
def lead(admin: requests.Session) -> dict:
    r = admin.post(f"{API}/leads", json={"name": "P7 Test Lead", "company": "Sunrise", "source": "direct_enquiry"})
    assert r.status_code in (200, 201), r.text
    doc = r.json()
    CREATED_LEADS.append(doc["id"])
    return doc


# --------------------------- B12 ---------------------------
class TestB12DeadCodeWired:
    def test_structured_stage_move_endpoint_exists(self, admin, lead):
        """LeadStageUpdate finally has a route."""
        r = admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "contacted", "notes": "Called once"})
        assert r.status_code == 200, r.text
        assert r.json()["stage"] == "contacted"

    def test_stage_move_writes_structured_history_with_note(self, admin, lead):
        """Self-contained: does not assume the previous test's stage."""
        before = admin.get(f"{API}/leads/{lead['id']}").json()["stage"]
        admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "qualified", "notes": "Budget confirmed"})
        history = admin.get(f"{API}/leads/{lead['id']}/stage-history").json()["history"]
        entry = history[-1]
        assert entry["to_stage"] == "qualified"
        assert entry["from_stage"] == before
        assert entry["note"] == "Budget confirmed"
        assert entry["changed_at"]

    def test_stage_move_validates_against_live_config(self, admin, lead):
        r = admin.post(f"{API}/leads/{lead['id']}/stage", json={"stage": "not_a_real_stage"})
        assert r.status_code == 400, r.text

    def test_stage_is_required(self, admin, lead):
        assert admin.post(f"{API}/leads/{lead['id']}/stage", json={}).status_code == 422

    def test_lead_source_endpoint_creates_a_real_config_item(self, admin):
        """LeadSourceCreate finally has a route, and it lands in the config set.

        Uses a unique-per-run name and always cleans up, so a failure here cannot
        poison the next run with a leftover config item.
        """
        name = f"P7 Expo Referral {uuid.uuid4().hex[:8]}"
        r = admin.post(f"{API}/lead-sources", json={"name": name, "category": "event"})
        try:
            assert r.status_code == 201, r.text
            key = r.json()["id"]
            items = admin.get(f"{API}/config/lead_sources").json()["items"]
            assert any(i["id"] == key for i in items)
            assert next(i for i in items if i["id"] == key)["group"] == "event"
        finally:
            admin.delete(f"{API}/config/lead_sources/{key}")


# --------------------------- Phase 7 ---------------------------
class TestProjectCreation:
    def test_new_project_gets_a_project_number(self, project):
        """Regression: create_project never issued project_no."""
        assert project.get("project_no"), project
        assert str(project["project_no"]).startswith("HAI-PRJ-")

    def test_project_numbers_are_unique(self, admin, project):
        second = admin.post(f"{API}/projects", json={"name": "P7 Second"}).json()
        CREATED_PROJECTS.append(second["id"])
        assert second["project_no"] != project["project_no"]

    def test_project_starts_with_stage_history(self, project):
        assert project.get("stage_history") == []


class TestProjectDetail:
    def test_detail_loads_with_related_counts(self, admin, project):
        r = admin.get(f"{API}/projects/{project['id']}")
        assert r.status_code == 200, r.text
        assert set(r.json()["counts"]) == {"quotations", "purchase_orders", "tasks", "contacts", "documents"}

    def test_missing_project_is_404(self, admin):
        assert admin.get(f"{API}/projects/does-not-exist").status_code == 404

    def test_related_is_one_call(self, admin, project):
        admin.post(f"{API}/tasks", json={"title": "Rig PA", "project_id": project["id"], "status": "pending"})
        r = admin.get(f"{API}/projects/{project['id']}/related")
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body) >= {"quotations", "purchase_orders", "tasks", "contacts", "documents"}
        assert len(body["tasks"]) == 1

    def test_activity_timeline(self, admin, project):
        admin.patch(f"{API}/projects/{project['id']}/stage", json={"stage_id": "planning"})
        acts = admin.get(f"{API}/projects/{project['id']}/activity").json()
        assert any(a["type"] == "stage_change" for a in acts)


class TestProjectStage:
    def test_stage_move_records_history(self, admin, project, project_stages):
        target = project_stages[1]
        r = admin.patch(f"{API}/projects/{project['id']}/stage",
                        json={"stage_id": target, "note": "Design signed off"})
        assert r.status_code == 200, r.text
        history = r.json()["stage_history"]
        assert history[-1]["to_stage"] == target
        assert history[-1]["note"] == "Design signed off"

    def test_history_keys_match_the_lead_convention(self, admin, project, project_stages):
        r = admin.patch(f"{API}/projects/{project['id']}/stage", json={"stage_id": project_stages[2]})
        entry = r.json()["stage_history"][-1]
        assert {"from_stage", "to_stage", "changed_by", "changed_at"} <= set(entry)

    def test_unknown_stage_is_rejected(self, admin, project):
        assert admin.patch(f"{API}/projects/{project['id']}/stage",
                           json={"stage_id": "bogus"}).status_code == 400


class TestProjectContacts:
    def test_add_list_remove(self, admin, project):
        c = admin.post(f"{API}/projects/{project['id']}/contacts",
                       json={"name": "Site Engineer", "contact_type": "engineer",
                             "phone": "9876500009", "is_primary": True})
        assert c.status_code == 201, c.text
        cid = c.json()["id"]

        listed = admin.get(f"{API}/projects/{project['id']}/contacts").json()
        assert any(x["id"] == cid for x in listed)

        assert admin.delete(f"{API}/projects/{project['id']}/contacts/{cid}").status_code == 200
        after = admin.get(f"{API}/projects/{project['id']}/contacts").json()
        assert not any(x["id"] == cid for x in after)


class TestProjectDocuments:
    def test_add_and_list(self, admin, project):
        d = admin.post(f"{API}/projects/{project['id']}/documents",
                       json={"name": "System Design v1", "url": "http://example.invalid/d.pdf", "kind": "design"})
        assert d.status_code == 201, d.text
        listed = admin.get(f"{API}/projects/{project['id']}/documents").json()
        assert any(x["name"] == "System Design v1" for x in listed)


class TestProjectTasksLink:
    def test_task_accepts_a_project_id(self, admin, project):
        """Regression: TaskCreate had no project_id, so the link was dropped."""
        t = admin.post(f"{API}/tasks", json={"title": "Rig PA", "project_id": project["id"],
                                             "status": "pending", "priority": "high"})
        assert t.status_code == 201, t.text
        assert t.json()["project_id"] == project["id"]
        tasks = admin.get(f"{API}/tasks?project_id={project['id']}").json()
        assert any(x["title"] == "Rig PA" for x in tasks)


# --------------------------- Phase 8 ---------------------------
class TestProjectIntegrations:
    def test_registry_is_served(self, admin, project):
        r = admin.get(f"{API}/projects/{project['id']}/integrations")
        assert r.status_code == 200, r.text
        avail = r.json()["available"]
        assert len(avail) >= 8
        assert {i["id"] for i in avail} == {"tally", "resend", "whatsapp_meta", "whatsapp_twilio",
                                            "webhooks", "meta_ads", "gemini", "amc"}

    def test_no_duplicated_integration(self, admin, project):
        avail = admin.get(f"{API}/projects/{project['id']}/integrations").json()["available"]
        assert len({i["id"] for i in avail}) == len(avail), "duplicate integration in the registry"

    def test_toggle_on_and_off(self, admin, project):
        on = admin.post(f"{API}/projects/{project['id']}/integrations/tally")
        assert on.status_code == 200 and "tally" in on.json()["integrations"]

        avail = admin.get(f"{API}/projects/{project['id']}/integrations").json()["available"]
        assert any(i["id"] == "tally" and i["in_use"] for i in avail)

        off = admin.post(f"{API}/projects/{project['id']}/integrations/tally")
        assert "tally" not in off.json()["integrations"]

    def test_unknown_integration_is_404(self, admin, project):
        assert admin.post(f"{API}/projects/{project['id']}/integrations/does_not_exist").status_code == 404


class TestProjectReports:
    def test_reports_is_not_shadowed_by_the_id_route(self, admin, project):
        """Regression guard: /projects/reports must be declared before /projects/{pid}."""
        r = admin.get(f"{API}/projects/reports")
        assert r.status_code == 200, r.text
        assert "totals" in r.json()

    def test_reports_include_the_project(self, admin, project):
        body = admin.get(f"{API}/projects/reports").json()
        assert any(x["id"] == project["id"] for x in body["projects"])
        assert body["totals"]["count"] >= 1

    def test_reports_filter_by_stage(self, admin, project):
        """The filter must narrow results, but other projects may share a stage --
        seeded projects legitimately sit in 'planning' too. Assert inclusion, not exclusivity."""
        admin.patch(f"{API}/projects/{project['id']}/stage", json={"stage_id": "planning"})
        body = admin.get(f"{API}/projects/reports?stage=planning").json()
        ids = {x["id"] for x in body["projects"]}
        assert project["id"] in ids

        other = admin.get(f"{API}/projects/reports?stage=__no_such_stage__").json()
        assert other["projects"] == []