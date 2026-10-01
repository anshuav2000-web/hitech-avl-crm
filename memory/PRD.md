# Hitech Audio & Image LLP — Sales CRM

## Original problem statement
> I run a distribution house in India where we import products from our OEMs. The company is Hitech Audio and Image LLP — all brands we import are foreign brands. I need a CRM system to take care of my leads (WhatsApp, email, website) and assign them to each of my sales people.

## Architecture
- **Backend:** FastAPI + MongoDB (motor). All routes under `/api`. JWT auth (HS256, 1-day TTL), bcrypt password hashing.
- **Frontend:** React 19 + react-router 7, Tailwind, Cabinet Grotesk + Satoshi fonts, lucide-react icons, recharts for KPIs.
- **AI:** Claude Sonnet 4.6 via `emergentintegrations` (Emergent LLM key) for lead summary / next-action coaching.
- **Auto-assignment:** round-robin by open-lead-count among sales users.

## User personas
- **Admin (owner):** full read/write across all leads, manages team, sees company-wide KPIs.
- **Sales person:** only sees leads assigned to them; updates stage, logs activity, creates quotations.

## Core requirements (static)
- Capture leads from manual entry + public web form (`/capture`, no auth).
- 6-stage pipeline: New → Contacted → Qualified → Quoted → Won / Lost.
- Activity timeline (notes, calls, emails, WhatsApp, meetings, follow-ups).
- Quotations with line items, GST, totals, auto-numbered (`HAI-Q-####`).
- Dashboard with KPIs (total / in-pipeline / won / conversion %), stage chart, source chart, recent leads.
- AI-powered next-action recommendations per lead.
- Role-based access enforced server-side.

## What's been implemented
**2026-06-29 — first finish**
- JWT auth (login, /me, logout) with seeded admin + demo sales user.
- Leads CRUD, public lead capture, lead-source filtering, search.
- Activities API + UI timeline.
- Quotations API + creation modal with multi-line items + GST math.
- Dashboard KPI endpoint + interactive bar/pie charts.
- Kanban board with drag-and-drop stage changes.
- Team management (admin only) — create / delete users.
- AI lead summary via Emergent LLM key + Claude Sonnet 4.6.
- Public web-form route at `/capture` ready to embed/share on the company website.

**2026-06-29 — Ops + Catalog + Integrations expansion**
- Per-rep brand access control (allowed_brands on User).
- Catalog & Packages (seeded L-Acoustics, RCF, DiGiCo + complex PA packages).
- Quotation Builder upgrades — typeahead picker, draft/duplicate, PDF download.
- Operations modules — Shipments, Inventory (serials), AMC renewals.
- CSV/Excel Lead Importer.
- Tally integration — TallyPrime XML export + optional HTTP push.
- WhatsApp & Zoho webhook stubs.

**2026-06-29 — Website integration polish (current task)**
- `/integrations` page restructured: 5 cleanly-numbered drop-in options (Floating widget, Direct link, Iframe, Native form, Direct API).
- All snippets auto-capture `source_url` so each lead shows which page on www.hitechavl.com it came from.
- New "Test the connection" panel (section 06) — sends a live POST to `/api/public/leads` from inside the CRM so the user can verify end-to-end before pasting the embed.
- CORS confirmed `*` so www.hitechavl.com can POST cross-origin.

**2026-06-29 — DiGiCo 2026 pricelist bundles**
- Extended `Package` model with `fixed_price_inr`, `components` (free-form sub-SKUs), and `sku`.
- New seeder `/app/backend/seed_digico_packages.py` parses `seed_data/digico_pricelist_2026.xlsx` (the user-provided Working Sheet) and creates 24 DiGiCo bundles with the Hi-Tech INR sell-price (column J), so bundle discounts are preserved (not recomputed from components).
- `Packages.js` now displays the fixed bundle price + component breakdown.
- `QuotationBuilder.js` has a new **Packages ⇄ Individual products** toggle inside the catalog browser. Clicking a bundle adds it as one quotation line at the fixed INR price; reps can then add items from other brands (L-Acoustics, RCF) below to mix package + add-ons.
- Verified: end-to-end POST `/api/quotations` with a Quantum 852 bundle → quote HAI-Q-1031 totals ₹1,93,01,142 (₹1,63,56,900 + 18 % GST).

**2026-06-30 — L-Acoustics K2/KARA II/L2 bundles**
- Seeder `/app/backend/seed_lacoustics_packages.py` parses `seed_data/lacoustics_k2_karaii_l2_packages.xlsx` (one tab per bundle: K2 16×8, KARA II 12×4, KARA II 12×8, L2 2×2×8).
- 4 packages inserted with `brand="L-Acoustics"`, `source="k2_karaii_l2_2026"`, and pre-GST `fixed_price_inr` taken from each sheet's "Total:" row (e.g. K2 16×8 = ₹4,83,79,400 → quote total ₹5,70,87,692 with 18% GST — matches workbook Grand Total).
- "OPTIONAL" components (e.g. KS28-COV) are still listed but excluded from the bundle price, matching the source file.
- Verified end-to-end: bundle picker in Quotation Builder + Packages page + API.

**2026-06-30 — Quotation PDF rebuilt in Hi-Tech house format**
- Reverse-engineered the customer-supplied sample (`L Acoustics Offer - Glasshouse, Hyderabad.pdf`) and rebuilt `/api/quotations/{id}/pdf` as a multi-page document:
  - Page 1 — Cover with header (Hi-Tech name + tagline left, brand logos right), red rule, To-block + Ref/Date/Validity/Currency meta, Subject line, opening paragraph, cover summary table, totals block, amount-in-words (Indian Lakh/Crore words via `_inr_words`).
  - Pages 2+ — Detailed Breakdown grouped by brand. Each brand has a dark banner + 8-column table; bundle lines list their components as indented `↳` sub-rows with qty (no individual prices, matches industry practice).
  - Last page — Terms & Conditions (uses `q.terms` if set, otherwise 10 default house clauses verbatim from the sample) + signatory ("Yours faithfully / For Hi-Tech Audio & Image LLP / Shaurya Gupta").
  - Header/footer drawn on every page via `BaseDocTemplate` + `onPage` canvas callback. Footer shows company name, work-office address, email, website, page number, and Ref. No.
- Installed `fonts-dejavu-core` (apt) and registered DejaVu Sans / Bold as `HTBody` / `HTBody-Bold` so ₹ (U+20B9), ↳ (U+21B3) and × (U+00D7) render correctly — previous PDFs were emitting tofu boxes.
- Date now in Indian "DD-Mon-YYYY" format (e.g. `30-Jun-2026`).
- testing_agent_v3_fork iteration_14: 10/10 backend + full admin frontend + RBAC pass; zero tofu; ₹/↳/brand banners/terms/signatory/Indian dates/amount-in-words all asserted via PyMuPDF text extraction.

**2026-07-01 — Security audit patches (SEC-001 → SEC-004)**
- **SEC-004** `/api/users` now requires admin. New `/api/users/roster` returns `{id, name}` only for any signed-in user — no email/role/allowed_brands leakage. `Leads.js` now calls the safer roster endpoint.
- **SEC-002** Admin seeding sources from `ADMIN_EMAIL` / `ADMIN_PASSWORD` env; demo sales user only seeded when `SEED_DEMO_USERS=true`. `SALES_DEMO_EMAIL` / `SALES_DEMO_PASSWORD` also env-driven. Preview .env keeps `SEED_DEMO_USERS=true` so existing sales login works.
- **SEC-003** `/api/webhook/whatsapp`, `/api/webhook/whatsapp/twilio`, `/api/webhook/zoho` now fail-closed with **HTTP 503** when their signing secret env var is empty (previously they silently skipped signature verification — open endpoint).
- **SEC-001** `/api/shipments` filters by `_allowed_brands(user)`; `freight_cost_inr` and `duty_paid_inr` stripped from responses for non-admin roles. Dashboard `/api/dashboard/stats.ops.shipments_in_transit` count and `shipments_arriving_soon` list are also brand-filtered.
- Bundled DejaVu Sans TTFs at `/app/backend/fonts/` so ₹/↳/× glyphs survive container restarts (previous apt install was lost on pod recycle).
- testing_agent_v3_fork iteration_15: **20/20 backend tests pass**, all 4 findings verifiably closed. Canonical regression at `/app/backend/tests/test_security_patches.py`.

## Test credentials
See `/app/memory/test_credentials.md`.

## Backlog (Next iterations)

### P0
- **WhatsApp inbound (live)** — wire Twilio webhook stub to real Twilio account (creds needed).
- **Email inbound (live)** — wire Zoho webhook stub to real Zoho Mail (creds needed).

### P1
- Historical PDF quotation parser (Claude via Emergent LLM key) — upload old PDFs to back-fill the CRM.
- Purchase Orders to OEMs.
- Multi-currency catalog + Forex tracking.
- Dealer / Reseller tiered pricing.
- Warranty + RMA workflow.
- Demo Unit Pool tracker.

### P2
- Landed Cost Calculator.
- Receivables / Aging report.
- Brand microsites.
- Project Milestones.
- Stripe / Razorpay payment links on quotations.
- Audit log / activity feed for admins.
