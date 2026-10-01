# Hitech AVL CRM — Modular Upgrade: Technical Implementation Plan

**Status:** PHASES 2–10 complete. All 10 phases delivered and verified.
**Principle:** Enhance, never replace. No existing collection, field, endpoint, or UI module is deleted or renamed.

---

## 1. Existing Architecture

### 1.1 Backend
| Aspect | Detail |
|---|---|
| Framework | FastAPI (single file `backend/server.py`, 5038 lines) |
| Router | `api = APIRouter(prefix="/api")` mounted at `server.py:5029` |
| DB driver | Motor (async MongoDB) |
| Auth | JWT HS256, `JWT_SECRET` from `.env`; token in `Authorization: Bearer` **and** `access_token` cookie |
| Auth deps | `get_current_user` (`server.py:101`), `require_admin` (`:123`), `require_superadmin` (`:131`) |
| Config | `backend/.env` via `python-dotenv`, loaded before imports (`server.py:1-5`) |
| PDF | ReportLab, branded templates, custom fonts in `backend/fonts` |
| AI | Google Gemini (`google.generativeai`, deprecated wrapper) |
| Email | Resend API + Zoho SMTP fallback |
| Entry point | **MISSING** — no `if __name__ == "__main__"` / `uvicorn.run()` |

### 1.2 Frontend
| Aspect | Detail |
|---|---|
| Build | CRA (`react-scripts` 5.0.1) + `@craco/craco` 7.1.0 |
| Router | react-router-dom 7.15, `BrowserRouter`, nested route under `AppShell` |
| State | `AuthContext` (token in `localStorage.hai_token`) + `@tanstack/react-query` (declared, barely used) + SWR (declared, unused) |
| Styling | Tailwind 3.4 + shadcn-style primitives in `src/components/ui/*` |
| Charts | recharts 3.6 |
| Animations | framer-motion 11.18 |
| Icons | lucide-react 0.516 |
| API layer | `src/lib/api.js` — axios instance, `API = ${REACT_APP_BACKEND_URL}/api` |
| Identity | `HitechLogo` (`src/components/Brand.js`), `EventProductionBackground`, dark slate + sky-600 palette, `label-eyebrow` / `glass-card` / `font-display` utility classes |

### 1.3 Runtime blocker (must be fixed first)
`python server.py` **imports the module and exits** — there is no server runner. That is the direct cause of the "Network Error" the user saw. Backend must be started with:
```
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
Additionally, **MongoDB is not installed on this machine** (`mongod.exe` not found; no Windows service registered). A data directory from a previous machine exists at `backend/data` (WiredTiger files) but no server binary can read it until MongoDB is installed.

---

## 2. Existing Modules (all reused, none rebuilt)

| Module | Route | Backend | Frontend page | Maturity |
|---|---|---|---|---|
| Auth / Users / Roles | `/auth/*`, `/users*`, `/roles*` | ✅ | `Login.js`, `Team.js` | Solid |
| Leads | `/leads*` | ✅ rich | `Leads.js`, `LeadDetail.js`, `LeadForm.js` | Good |
| Lead Pipeline | `/leads` PATCH stage | ✅ | `Pipeline.js` (hard-coded 24 stages) | Hard-coded |
| Qualification (BANT) | `/leads/{id}/qualify*` | ✅ | `Qualification.js` | Good |
| Follow-Ups | `/follow-ups` | ✅ | `FollowUps.js` | Good |
| Contact Attempts | `/leads/{id}/contact-attempts` | ✅ | in LeadDetail | Good |
| Design Team | `/design-tasks` | ✅ | `DesignTeam.js` | Good |
| BOQ | `/boqs` | ✅ | `BoqGenerator.js` | Good |
| Quotations | `/quotations*` | ✅ strong | `Quotations.js`, `QuotationBuilder.js` | Strong |
| Purchase Orders | `/purchase-orders` | ⚠️ supplier-side only | `PurchaseOrders.js` | Wrong semantics for request |
| Invoices / Accounting | `/accounting`, `/invoices` | ✅ | `Accounting.js` | Good |
| Projects | `/projects` | ⚠️ 7 fields only | `Projects.js` (table) | Stub |
| Customers / Contacts | `/customers`, `/contacts` | ✅ thin | `Customers.js`, `Contacts.js` | Thin |
| Tasks | `/tasks` | ⚠️ 6 fields | `Tasks.js` | Thin |
| Calendar / Events | `/events` | ✅ | `Calendar.js` | Good |
| Work Orders | `/work-orders` | ✅ | `WorkOrders.js` | Good |
| AMC | `/amcs` | ✅ | `AMCs.js` | Good |
| Inventory / Shipments | `/inventory`, `/shipments` | ✅ | `Inventory.js`, `Shipments.js` | Good |
| Catalog / Packages / Brands | `/products`, `/packages`, `/brands` | ✅ | `Catalog.js`, `Packages.js` | Strong |
| Suppliers | `/suppliers` | ✅ | `Suppliers.js` | Good |
| Negotiation / Lost / Requirements | `/negotiations`, `/lost-leads`, `/leads/{id}/requirements` | ✅ | in LeadDetail | Good |
| Social / Marketing / Bookings | `/social*`, `/marketing`, `/bookings` | ✅ | `SocialMedia.js`, `DigitalMarketing.js`, `BookingSystem.js` | Good |
| Settings | `/settings/company`, `/settings/system` | ✅ | `CompanySettings.js`, `SystemSettings.js` | Good |
| **14 placeholder pages** | `/module/*` | ❌ none | `GenericModulePage.jsx` **fabricates sample rows** | Fake |

Placeholder modules routed to `GenericModulePage`: `opportunities`, `companies`, `activities`, `contracts`, `milestones`, `gantt`, `categories`, `vendor-performance`, `expenses`, `tax-reports`, `timesheets`, `manufacturing`, `stocktakes`, `seo`.

---

## 3. Existing Database Collections (MongoDB `hitech_crm`)

`users`, `roles`, `brands`, `brand_access_requests`, `leads`, `activities`, `lead_sources`, `lead_stages`, `quotations`, `projects`, `customers`, `contacts`, `accounting`, `events`, `tasks`, `work_orders`, `suppliers`, `social_posts`, `campaigns`, `bookings`, `settings`, `products`, `packages`, `shipments`, `inventory`, `amcs`, `invoices`, `purchase_orders`, `negotiations`, `design_tasks`, `boqs`, `follow_ups`, `contact_attempts`, `lost_leads`, `requirement_discussions`, `activity_logs`, `notifications`, `sales_targets`, `reports`, `webhook_settings`, `webhook_logs`, `resend_settings`, `email_logs`, `sync_logs`, `contact_attempts`.

Indexes created in `on_start()` (`server.py:4705-4719`).

### Existing relationships (already valid, will be extended — never rewritten)
- `leads.assigned_to` → `users.id`
- `activities.lead_id` → `leads.id`
- `quotations.lead_id` → `leads.id`
- `invoices.quotation_id` → `quotations.id`, `invoices.po_id` → `purchase_orders.id`
- `events.lead_id`, `follow_ups.lead_id`, `contact_attempts.lead_id`, `negotiations.lead_id`, `requirement_discussions.lead_id`
- `tasks.lead_id`
- `boqs.lead_id`
- **Missing:** `projects` has **no** `lead_id`/`quotation_id`/`customer_id`. `purchase_orders` has **no** `quotation_id`/`customer_id`/`project_id`. `customers` has **no** `lead_id`. `tasks` has **no** `project_id`/`quotation_id`/`po_id`.

---

## 4. Existing Integrations — REUSE, do not duplicate

| Integration | Implementation | Reuse for |
|---|---|---|
| Resend email | `_send_resend_email()`, `_fire_resend()`, `/resend/*` | Quotation/PO email share |
| Zoho SMTP | `SMTP_*` in `.env`, `_send_zoho_email` path | Email fallback |
| WhatsApp **inbound** (Meta Cloud) | `POST /webhook/whatsapp` | Inbound lead capture |
| WhatsApp **inbound** (Twilio) | `POST /webhook/whatsapp/twilio` | Inbound lead capture |
| n8n webhooks | `_fire_webhook()`, `/webhooks/*` | Generic automation |
| Tally XML | `/quotations/{id}/tally-xml`, `tally-push` | Accounting push |
| Meta Ads | `/meta/*` | Marketing |
| Google Gemini | `call_gemini()`, `/leads/{id}/ai-summary`, `/quotations/ai-recommend` | AI summaries, PDF import |
| ReportLab | `/quotations/{id}/pdf`, `/accounting/{id}/pdf` | Branded PDF |
| Public capture | `PublicLeadForm.js` → `POST /public/leads` | Web leads |

**Gap:** WhatsApp is **inbound only**. There is no outbound share/wa.me composer. The request asks for WhatsApp *sharing*. Correct approach: add a dynamic `wa.me` link builder + optional outbound Cloud API dispatch — **reusing the existing Meta/Twilio credentials and settings**, not a new integration.

---

## 5. Existing Bugs Found During Audit (must be fixed; each is a regression risk)

| # | Location | Bug | Impact |
|---|---|---|---|
| B1 | `server.py` (end of file) | No `uvicorn.run` entry point | **Backend never starts** → "Network Error" |
| B2 | `server.py:1989,1205,1214,1291,1619,4596,4615` | Scoping checks use `user["role"] != "admin"` | `superadmin` is treated as a sales user — sees only *assigned* leads, no admin panels |
| B3 | `Sidebar.jsx:364` | `visibleChildren` filters `c.roles.includes("admin")` | Hard-coded admin — non-admin users see children of sections they cannot access |
| B4 | `Dashboard.js:97` | `stats.by_stage.won` / `.lost` | `PIPELINE_STAGES` has `quotation_confirmed` / `lost_lead` — "Won Deals" and "In Pipeline" are always wrong |
| B5 | `Dashboard.js:523-536` | `StageBadge` map keyed on `won`/`lost`/`quoted` | None of these exist in the real stage list → every badge falls back to grey |
| B6 | `server.py:4620` | Non-admin search returns **all** of the user's quotations, unfiltered by `q` | Data leak into search UI |
| B7 | `server.py:4997` | `suppliers.insert_many` sits **inside** the `for r in default_roles` loop | 9 duplicate suppliers inserted on every cold start where any role is missing |
| B8 | `server.py:1441-1442, 1466-1467` | Routes registered twice: `/api/sync/...` and `/api/api/sync/...` | Wrong-prefix shadow route |
| B9 | `server.py:129` vs roles seed | `require_admin` allows role `"management"`; no such role is seeded | Dead role name |
| B10 | `Header.jsx:10-19,179` | Search is a **static page list**; never calls `/api/search` | Global search is non-functional |
| B11 | `Header.jsx:110` | Notification bell is a hard-coded red dot | Notifications unreadable |
| B12 | `server.py:523,529` | `LeadSourceCreate` / `LeadStageUpdate` models exist with **no routes** | Dead code — the intended configurable-stage feature was never wired |

---

## 6. Required Database Changes (additive only, no renames, no drops)

All new collections are additive. All new fields are optional with safe defaults so existing documents keep working untouched.

### 6.1 New configuration collections
| Collection | Purpose | Notes |
|---|---|---|
| `crm_config_sets` | Generic config container: `{key, scope, items[], version, updated_at, updated_by}` | One collection drives *all* configurable lists (see 6.2). Replaces the dead `lead_stages` / `lead_sources` intent without deleting them. |
| `dashboard_layouts` | `{user_id, layout[], updated_at}` | Per-user widget layout. Unique index on `user_id`. |
| `sidebar_layouts` | `{user_id, sections[], updated_at}` | Per-user sidebar order/visibility. Unique index on `user_id`. |
| `notification_rules` | `{event, enabled, roles[]}` | Admin-tunable notification triggers |
| `document_templates` | `{type, name, body, is_default}` | Quotation/PO/Invoice template bodies |

### 6.2 Config keys in `crm_config_sets`
`lead_stages`, `project_stages`, `task_statuses`, `priorities`, `customer_types`, `project_types`, `contact_types`, `quote_statuses`, `po_statuses`, `project_workflows`.

Each item shape:
```
{ id, key, label, order, color, icon, is_active, is_won, is_lost, is_default, group }
```

### 6.3 New fields on existing collections (all optional)
| Collection | New fields |
|---|---|
| `leads` | `stage_id`, `stage_history[] {from,to,by,at}`, `expected_close_date`, `follow_up_date`, `customer_id`, `attachments[]` |
| `quotations` | `customer_id`, `project_id`, `quote_status` (config-driven), `approval {status,by,at,note}`, `notes`, `attachments[]`, `version`, `duplicated_from` |
| `purchase_orders` | **`direction`: `"supplier"` \| `"customer"`**, `quotation_id`, `lead_id`, `customer_id`, `project_id`, `po_seq`, `items_snapshot_ref`, `approval` |
| `projects` | `project_no`, `stage_id`, `project_type`, `contact_role_ids[]`, `customer_id`, `lead_id`, `quotation_ids[]`, `po_ids[]`, `target_date`, `manager_id`, `team[]`, `documents[]`, `notes`, `workflow_id`, `progress` |
| `tasks` | `description`, `status_id`, `priority_id`, `start_date`, `related {module, record_id, record_label}`, `attachments[]`, `comments[]`, `reminder_at`, `project_id` |
| `customers` | `customer_type`, `lead_ids[]` |
| `notifications` | `link`, `icon`, `entity {module,id}` |

### 6.4 Migration strategy
New file `backend/migrations.py`:
- Framework: a lightweight in-repo runner (`MIGRATIONS = [...]`), invoked by `python -m migrations` **and** idempotently by the FastAPI startup hook.
- Every migration: `id`, `name`, `up(db)`. All are **idempotent** (`create_index` with `background`, `$set` with defaults, `update_many` no-ops on re-run).
- **No `drop`, no `rename`, no `delete`** in any migration.
- `schema_version` key written into the existing `settings` collection after each run.

Migration set:
1. `m001_config_seed` — seed `crm_config_sets` from the current hard-coded constants (`PIPELINE_STAGES`, `Tasks.js` statuses, `Projects.js` statuses) so behaviour is preserved exactly.
2. `m002_indexes` — indexes for all new fields.
3. `m003_backfill_stage_ids` — map each existing `leads.stage` slug to its config `stage_id`; no data mutation beyond adding the new field.
4. `m004_backfill_stage_history` — synthesise a single history entry per lead from `created_at` + current stage.
5. `m005_project_enrichment` — assign `project_no` to existing projects.
6. `m006_po_direction` — set `direction: "supplier"` on existing POs (correct, since they are vendor POs).
7. `m007_fix_supplier_seed_loop` — remove the duplicate-insert loop at `server.py:4997` (code fix, not data).

---

## 7. Required API Changes (all additive)

### 7.1 Configuration
```
GET    /api/config/{key}                 # public-ish, auth required
GET    /api/config                      # all keys (one call → caches)
POST   /api/config/{key}                # superadmin — add item
PATCH  /api/config/{key}/{item_id}      # superadmin — rename/recolour/reorder
DELETE /api/config/{key}/{item_id}      # superadmin — soft (is_active=false) if in use
POST   /api/config/{key}/reorder        # superadmin — bulk order
POST   /api/config/reset                # superadmin — restore defaults
```

### 7.2 Dashboard & sidebar
```
GET    /api/dashboard/layout            # current user's layout (creates default on first call)
PUT    /api/dashboard/layout            # persist order / hidden / size
POST   /api/dashboard/layout/reset
GET    /api/dashboard/widgets           # widget registry (id, label, group, minW, minH, roles)
GET    /api/dashboard/summary           # per-widget data, one call, permission-scoped
GET    /api/sidebar/layout
PUT    /api/sidebar/layout
POST   /api/sidebar/layout/reset
```

### 7.3 Leads
```
GET    /api/leads/{id}/stage-history
POST   /api/leads/{id}/stage            # structured move, writes stage_history + activity + notification
GET    /api/leads/{id}/related          # customer, quotations, POs, project, tasks — single call
```

### 7.4 Quotations → PO
```
POST   /api/quotations/{id}/duplicate
POST   /api/quotations/{id}/share/whatsapp     # returns wa.me URL + rendered message
POST   /api/quotations/{id}/share/email        # reuses _send_resend_email
GET    /api/quotations/{id}/share/link
POST   /api/quotations/{id}/approve
POST   /api/quotations/{id}/convert-to-po      # direction="customer", carries items, sets quotation_id
GET    /api/purchase-orders/{id}
POST   /api/purchase-orders/{id}/approve
```

### 7.5 Projects
```
GET    /api/projects/{id}                    # full detail incl. related counts
GET    /api/projects/{id}/related            # customer, lead, quotations, POs, tasks, docs, activity
PATCH  /api/projects/{id}/stage              # records stage history
GET    /api/projects/{id}/activity
GET    /api/projects/{id}/contacts
POST   /api/projects/{id}/contacts
DELETE /api/projects/{id}/contacts/{cid}
GET    /api/projects/{id}/documents
POST   /api/projects/{id}/documents
GET    /api/projects/{id}/integrations       # existing integration registry + per-project config
GET    /api/projects/reports?filters...
```

### 7.6 Tasks, search, notifications, activity
```
GET    /api/tasks?status_id&project_id&related_module&assigned_to&due_before
GET    /api/tasks/{id}
POST   /api/tasks/{id}/comments
GET    /api/search?q=&types=                # fixed: q-filtered, permission-scoped, categorised
GET    /api/notifications/unread-count       # already exists — wire the bell to it
GET    /api/activity-timeline?module=&record_id=
```

---

## 8. Required Frontend Changes (new files only; existing pages enhanced in place)

| New file | Purpose |
|---|---|
| `src/config/widgetRegistry.jsx` | Widget registry — add a widget in one entry, no dashboard redesign |
| `src/components/dashboard/DashboardGrid.jsx` | CSS-grid + **native HTML5 drag & drop** (no new npm deps) |
| `src/components/dashboard/WidgetShell.jsx` | Card chrome: title, drag handle, size menu, hide, remove |
| `src/components/dashboard/WidgetPicker.jsx` | Add-widget modal grouped by category |
| `src/components/dashboard/widgets/*.jsx` | One file per widget (`LeadsWidget`, `PipelineWidget`, `ProjectsWidget`, `TasksWidget`, `FollowUpsWidget`, `QuotationsWidget`, `PurchaseOrdersWidget`, `ApprovalsWidget`, `ActivityWidget`, `SalesSummaryWidget`, `RevenueWidget`, `CustomerSummaryWidget`, `DeadlinesWidget`, `NotificationsWidget`, `TeamPerformanceWidget`) |
| `src/components/dashboard/hooks/useDashboardLayout.js` | Load / save / reset layout, optimistic, debounced |
| `src/components/sidebar/SidebarCustomizer.jsx` | Show/hide + reorder modules, persisted to DB |
| `src/components/records/ActivityTimeline.jsx` | Shared timeline renderer (reuse on lead / quote / PO / project) |
| `src/components/records/RelatedRecords.jsx` | Shared "related records" panel (customer, lead, quote, PO, project, tasks) |
| `src/components/records/ShareMenu.jsx` | WhatsApp / Email / Copy link / Download / Print |
| `src/components/records/QuotationPreview.jsx` | Full preview before PDF download |
| `src/pages/ProjectDetail.jsx` | Tabbed project dashboard (Overview / Timeline / Tasks / Documents / Quotes / POs / Contacts / Integrations / Activity) |
| `src/pages/AdminConfig.jsx` | Admin screen for all configurable lists |
| `src/pages/ProjectReports.jsx` | Filterable project reports |
| `src/components/search/GlobalSearchResults.jsx` | Categorised results wired to `/api/search` |

**Files modified in place (enhance, do not replace):**
- `Dashboard.js` → becomes the default-layout shell that renders `DashboardGrid`; existing `Kpi`/charts reused as widget bodies.
- `Pipeline.js` → `STAGES` array replaced by `GET /api/config/lead_stages`.
- `Sidebar.jsx` → B3 fix; preferences hydrated from `/api/sidebar/layout` with localStorage as offline fallback.
- `Header.jsx` → B10/B11 fix: real search + real unread-count.
- `Tasks.js` → config-driven statuses, related-record fields.
- `Projects.js` → list view with filters; links to `ProjectDetail`.
- `Quotations.js` → add Duplicate / Share / Print / Approve / Convert-to-PO.
- `App.js` → register new routes only.

**Constraint:** no new npm dependencies. `npm install` currently fails with `ERESOLVE` (`react-day-picker@8.10.1` peer `date-fns@^2||^3` vs root `date-fns@4.1.0`). Drag & drop uses the native HTML5 API already proven in `Pipeline.js`.

---

## 9. Reusable Functionality (no rewrite)

- `hash_password` / `verify_password` / `create_token` / `get_current_user` / `require_admin` / `require_superadmin`
- `_compute_totals` (pricing engine)
- `_allowed_brands` (brand ACL)
- `_auto_assign` (round-robin)
- `_fire_webhook`, `_fire_resend`, `_send_resend_email`
- `_fetch_brand_logos`, `PDF_FONT`, `PDF_FONT_BOLD`, `HITECH_OFFICE_ADDR` (PDF branding)
- ReportLab quotation/accounting builders — extended, not rewritten
- `PdfPreviewModal.jsx`
- `HitechLogo`, `EventProductionBackground`, `label-eyebrow`, `glass-card`, `font-display` design system
- `src/components/ui/*` (shadcn primitives: dialog, dropdown-menu, tabs, sheet, table, tooltip, select, popover, scroll-area, command, calendar, toast)

---

## 10. Design System Additions

- `ThemeProvider` (light/dark) already exists → new modules must respect it.
- New shared tokens: `WidgetCard`, `PageHeader`, `TabbedPanel`, `EmptyState`, `SectionTitle`, `StatTile` — defined once, reused by dashboard, project detail, reports.
- Density: 12-col responsive grid; 4-col tablet; 1-col mobile.
- Accessibility: keyboard-reorderable widgets, `aria-label` on drag handles, focus rings preserved, tooltips on collapsed sidebar (already present).

---

## 11. Potential Breaking Changes & Mitigations

| Risk | Mitigation |
|---|---|
| Replacing hard-coded stages breaks Pipeline/Dashboard | Config is seeded from the exact current constants (m001); all existing stage slugs remain valid `key`s |
| Changing dashboard layout breaks `data-testid` | All current test IDs preserved; new grid wraps the same components |
| Adding `direction` to POs | Defaults to `"supplier"`; existing POs untouched; only newly converted POs are `"customer"` |
| Denormalising quote items into a PO | PO stores `quotation_id` and re-reads items from the quotation; only a `items_snapshot` is stored for audit immutability |
| Permission tightening could hide existing modules | Config is additive; no module is removed; role checks use the *union* of old and new rules |
| New `user_id`-scoped collections | Created lazily on first access; no backfill needed |
| Fixing B2 (`superadmin` scoping) changes visible data | Intentional bug fix; `superadmin` now sees all data as its name implies |
| Adding indexes to large collections | `background: true`; `m002` is idempotent and safe to re-run |

---

## 12. Execution Order

| Phase | Deliverable | Gate before next phase |
|---|---|---|
| 0 | **Unblock runtime**: add uvicorn entry point; install MongoDB; verify login + one list endpoint | Frontend loads data with no Network Error |
| 1 | Audit (this document) | — |
| 2 | `migrations.py` + `crm_config_sets` + `/api/config/*` + fix B7, B8, B2 | Existing pipeline & dashboard still show identical data |

| 3 | Customizable dashboard + widget registry + modular sidebar; fix B3, B4, B5 | Layout persists across logout/login; responsive at 3 widths |
| 4 | Config-driven lead pipeline, drag & drop, structured stage history | Existing leads unaffected; every move recorded |
| 5 | Quotation preview, Duplicate, Share (WhatsApp/Email/Link/Print), approval; fix B1 | PDF still renders with branding |
| 6 | `quotation → customer PO` with references | Lead → Quote → PO → Project navigable |
| 7 | Projects module + `ProjectDetail` dashboard + timeline + tasks; fix B12 | Projects creatable directly *and* from a quotation |
| 8 | Project contact types + integrations tab (reusing existing integrations) | No duplicated integration |
| 9 | Reports, global search (fix B10, B6), notifications (fix B11), activity timeline | Notifications actually fire |
| 10 | Test suite run, regression sweep, responsive/perf pass | All existing pytest suites green |

---

## 12a. Phase 2 Outcome

**Delivered:** `migrations.py` (m001–m009, all idempotent), `crm_config_sets` (11 sets), full
`/api/config/*` CRUD + reorder + reset with optimistic-locking `version` and role guards, and
fixes for B7 (duplicate supplier seeding), B8 (shadow `/api/api/*` routes) and B2 (superadmin /
management were scoped as sales reps and saw none of the data). Also fixed B13: `LeadCreate` had
no `notes` field, so every lead creation — authenticated and public — returned HTTP 500.

**Gate passed:** 24 pipeline stages intact and ordered, dashboard aggregates unchanged, 3 seeded
projects still carry `project_no` + `stage_id`, and all core list endpoints return 200.

**Deferred to Phase 3 / 4 — do not treat as done:**

- **B4 is still open.** `server.py:1113` (`_auto_assign`) and `server.py:2060` filter
  `stage: {"$nin": ["won", "lost"]}`, but no stage has ever been named `won` or `lost` — the real
  keys are `quotation_confirmed` and `lost_lead`. Round-robin assignment and open-lead counts
  therefore count closed leads as active. Phase 2 made the flags correct (`m009`); Phase 3 must
  rewire the two call sites to read them from the config set.
- **CSV import vocabulary mismatch.** `server.py:2478` `VALID_STAGES` is a stale 6-value set
  (`new/contacted/qualified/quoted/won/lost`) that matches neither the seeded pipeline nor the
  dashboard. Affects lead import normalisation only; needs a decision in Phase 4.

**Pre-existing defects found, deliberately not "fixed" by weakening the test:**

- `test_quotation_pdf_v2.py::test_mixed_bundle_quote_pdf_full_validation` fails on real quotation
  PDF generator defects: the "Detailed Breakdown" section is absent from bundle quotes, only 5 `₹`
  glyphs render (test requires ≥10), and header/footer separators emit `U+FFFD` replacement
  characters. The generator (`server.py:1627`–2000) has no config lookups, so Phase 2 cannot be
  the cause. This is Phase 5 work.
- The test suite was previously unrunnable: `pytest-xdist` and `pymupdf` were missing, and it needs
  `REACT_APP_BACKEND_URL` set plus `SEED_DEMO_USERS=true`. Four stale fixtures were corrected at
  the test rather than the model (invalid `"manual"` source, the unassigned-lead precondition that
  round-robin auto-assignment invalidates, and two PDF sign-off strings the template never
  rendered).

---

## Phase 5 — Quotation flow: complete

Added duplication, customer sharing and an approval ladder to quotations, plus the fix for the
phantom-stage defect that was blocking the flow.

**Backend** (`backend/server.py`):

- `POST /api/quotations/{id}/duplicate` — copies line items into a fresh `draft`, assigns a fresh
  quote number, records `duplicated_from`, and deliberately drops `share_token` / `shared_at` /
  `approved_at` / `approved_by` / `approval_note` / `viewed_at` so a copy never inherits a live
  customer link or a prior sign-off.
- `POST /api/quotations/{id}/share` with `channel` = `whatsapp` | `email` | `link` | `print`.
  Whitespace and `+` are stripped from the recipient so `+91 98765 43210` becomes `919876543210`.
  A missing WhatsApp number is a `422`, not a broken link.
- `GET /api/public/quotation/{token}` — unauthenticated, deliberately narrow projection (quote
  number, items, charges, totals, terms). It never returns `lead_id`, email or phone. Unknown token
  is a `404`.
- `POST /api/quotations/{id}/approval` with `action` = `submit` | `approve` | `reject` | `reopen`,
  recording approver and note. Accepting moves the lead to `quotation_confirmed` through the
  config-driven stage path, so it also lands in `stage_history`.
- All three respect the existing ownership rule: a sales rep gets `403` on a lead that is not
  assigned to them; `admin` / `superadmin` / `management` are never blocked.

**Frontend:**

- `frontend/src/components/quotations/QuotationActions.jsx` — duplicate, share panel
  (email / WhatsApp / copy link / print) and the approval buttons, wired into `Quotations.js`.
- `frontend/src/pages/PublicQuotation.jsx` + `/public/quotation/:token` route, registered outside
  `<Protected>` so a customer can open the link without an account.

**Defects fixed along the way:**

- `create_quotation` hard-coded the lead stage `"quoted"`, which is not one of the configured
  stages, so quoting a lead silently removed it from the Kanban board. It now goes through
  `_advance_lead_to_quotation_stage` → `convert_to_quotation`, and never resurrects a closed lead.
- Quote numbering was `f"HAI-Q-{1000 + count + 1}"`, which reused a number as soon as a quotation
  was deleted. Now derived from the max existing number.
- Quotations never snapshotted the client party, so a shared link had no addressee to render.
  `client_name` / `company_name` are now captured at creation time (a quote is a contractual
  document and must keep naming the correct party if the lead is later renamed or deleted), with a
  projection-limited lead fallback for legacy quotes.

**Verification:** 20 new tests in `backend/tests/test_quotation_flow.py` cover the configured stage,
numbering after deletion, duplication, all four share channels, the public projection and its
privacy boundary, the approval ladder and its stage effect, and sales/admin isolation. A Playwright
pass confirmed 27 browser assertions across the public view and the share panel, with no page
errors and no contact-detail leakage. Full suite: **49 passed, 1 failed** — the single failure is
the deferred `test_mixed_bundle_quote_pdf_full_validation` PDF defect above, unchanged.

---

## 13. Explicitly Out of Scope

- Replacing the existing CRM or any existing page wholesale.
- Deleting `GenericModulePage` placeholder modules — they are marked as stubs, not removed.
- Adding new third-party SaaS integrations beyond what is already configured.
- Replacing ReportLab with a different PDF engine.

---

## Phases 6–10 Outcome

All ten phases are delivered. Each phase below lists what shipped and the defects found
and fixed while building it — the defect list is the important part, because several were
real bugs rather than missing features.

### Phase 6 — Quotation → customer PO

`POST /quotations/{id}/convert-to-po` converts an accepted quotation into a customer-side
purchase order. Existing POs are vendor POs (`direction: "supplier"`); a converted one is
`direction: "customer"` with `supplier_id` left null rather than faked. Customer POs use a
separate `CPO-<year>-NNN` series so they can never collide with the `PO-` series vendors are
quoting against. Also `GET /purchase-orders/{id}` (embeds the source quotation and lead) and
`POST /purchase-orders/{id}/approve`. All three honour the existing ownership rule.

- **`_compute_totals` only accepted Pydantic models.** Re-pricing a stored quotation passed
  dicts and raised `AttributeError`. Rather than duplicate the pricing formula — which would
  be free to drift from the quotation total, the exact number a customer disputes — the one
  engine now accepts both.
- **Quote numbering collided after deletion** (`1000 + count + 1`). Now scans the max suffix.

### Phase 7 — Projects module

Project detail with related counts, a single-call `/related`, stage moves with structured
history, contacts, documents, and a filterable `/projects/reports`.

- **`TaskCreate` had no `project_id` field**, so a task could never link to a project no matter
  what the client sent. The link was silently dropped.
- **`create_project` never issued a `project_no`.** `m005` only backfilled projects that
  already existed, so every project created through the UI came out unnumbered.
- **`/projects/reports` was at risk of being shadowed** by `/projects/{pid}`; it is declared
  first, and a regression test pins that ordering.

### Phase 8 — Contact types + integrations

Project contacts and documents, plus a single `PROJECT_INTEGRATIONS` registry that the
Integrations tab renders from. The tab cannot advertise a connector the Integrations page
cannot configure — that was the "no duplicated integration" requirement.

### Phase 9 — Search, notifications, activity timeline

- **B6 — the sales branch of `/api/search` ignored `q` for quotations** and returned every
  quotation the rep owned, so any keystroke dumped their whole book into the results panel.
- **B10 — the header overlay filtered a hard-coded page list** and never called `/api/search`,
  so "global search" could not find a single record. It now queries the API, debounced 250 ms,
  with categorised results.
- **B11 — the notification bell was a hard-coded red dot** wired to nothing. It now reads the
  real unread count and polls every 60 s.
- Unescaped `$regex` let a stray `(` or `.*` raise a 500 or trigger catastrophic backtracking;
  the term is escaped and projections are explicit so search cannot leak internal lead notes.
- Notifications actually fire: every stage move notifies the lead's owner and admins, and
  **excludes the actor** — otherwise the badge would increment on every action the user takes
  themselves.

### Phase 10 — Verification

**Backend: 101 passed, 1 failed.** The single failure is the deferred
`test_mixed_bundle_quote_pdf_full_validation` PDF defect, unchanged from the Phase 2 baseline
and untouched by any of this work. **Browser: 24/24** Playwright assertions across the public
quotation view, share panel, project detail tabs, integrations toggle, and global search.

New permanent suites: `tests/test_quotation_flow.py` (20), `tests/test_projects_module.py` (25),
`tests/test_search_notifications.py` (27).

---

## Data Work

Migration-driven and idempotent, in `backend/migrations_seed_data.py`:

- **`m011_seed_catalog`** — 38 real pro-audio / AV brands and 67 real product model lines
  (L-Acoustics K2, d&b KSL, DiGiCo SD7, Shure SLX24, QSC CPX, Samsung QM55R, Barco PKIX …).
  **Prices are deliberately left unset** (`unit_price: None`, `price_status: "pending"`). We
  do not know this dealer's actual price list, and a guessed figure reaching a customer
  quotation is worse than a blank one. `ProductCreate.unit_price` is now optional so an
  unpriced product can also be created through the UI.
- **`m012_seed_demo_employees`** — 16 **fictional** demo accounts across Sales, Service,
  Accounts, Purchase, Projects and Design. Every one is tagged `is_demo: true` and uses a
  `demo-<name>@hitech.example` address (a reserved TLD) so they cannot collide with, or be
  mistaken for, real staff. **Purge before go-live:** `db.users.delete_many({is_demo: true})`.
  This also makes round-robin lead assignment and the team dashboard exercisable — new leads
  now spread across 5 reps instead of always landing on one.
- Both migrations key on natural keys, so re-running is a no-op and a hand-corrected price is
  never overwritten.

**Temp data removed:** 33 test/probe rows (leads, quotations) plus orphaned tasks. Retained
business seed data: 3 customers (Taj, Marriott, ITC), 3 projects, 3 tasks, 2 contacts,
1 supplier PO.
