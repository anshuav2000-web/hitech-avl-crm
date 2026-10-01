# Product Catalogue Import Report

Generated: 2026-10-01 14:18 UTC

**3,939 active products** in the catalogue: **3,924 scraped** from manufacturers and **15 entered by hand** before this work began.

Products were read from **18 of 21** approved brands. Every scraped product carries its manufacturer's own official URL and the date it was read. No model, specification, price or description was invented. Where a catalogue could not be read, the brand is recorded as needing manual import rather than left silently empty.

## Per-brand counts

| Brand | Active | Scraped | Entered by hand | Discontinued | Official site | Catalogue |
|---|---:|---:|---:|---:|---|---|
| RCF | 1,239 | 1,235 | 4 |  | https://www.rcf.it/ | read from manufacturer |
| L-Acoustics | 316 | 311 | 5 |  | https://www.l-acoustics.com/ | read from manufacturer |
| DiGiCo | 81 | 78 | 3 |  | https://digico.biz/ | read from manufacturer |
| TT+ Audio | 110 | 110 | 0 |  | https://www.ttaudio.com/ | read from manufacturer |
| Sound Devices | 215 | 215 | 0 |  | https://www.sounddevices.com/ | read from manufacturer |
| Klang Technologies | 13 | 13 | 0 |  | https://www.klang.com/ | read from manufacturer |
| Radial Engineering | 196 | 196 | 0 |  | https://www.radialeng.com/ | read from manufacturer |
| Fourier Audio | 5 | 5 | 0 |  | https://fourieraudio.com/ | read from manufacturer |
| Audio Press Box | 0 | 0 | 0 |  | https://www.audiopressbox.com/ | **no catalogue read; needs manual import** |
| MA Lighting | 119 | 119 | 0 |  | https://www.malighting.com/ | read from manufacturer |
| MADRIX | 12 | 12 | 0 |  | https://www.madrix.com/ | read from manufacturer |
| ETC | 650 | 650 | 0 |  | https://www.etcconnect.com/ | read from manufacturer |
| Zactrack | 3 | 3 | 0 |  | https://www.zactrack.com/ | read from manufacturer |
| Luminex | 44 | 44 | 0 | 16 | https://www.luminex.be/ | read from manufacturer |
| Klotz | 19 | 19 | 0 |  | https://www.klotz-ais.com/ | read from manufacturer |
| K&M | 0 | 0 | 0 |  | https://www.k-m.de/ | **no catalogue read; needs manual import** |
| Sennheiser | 403 | 400 | 3 |  | https://www.sennheiser.com/ | **partial: more products remain** |
| Cotodama | 0 | 0 | 0 |  | https://www.cotodama.com/ | **no catalogue read; needs manual import** |
| DPA Microphones | 202 | 202 | 0 |  | https://www.dpamicrophones.com/ | read from manufacturer |
| JH Audio | 38 | 38 | 0 |  | https://jhaudio.com/ | read from manufacturer |
| Wisycom | 274 | 274 | 0 |  | https://wisycom.com/ | read from manufacturer |
| **Total** | **3,939** | **3,924** | **15** | | | |

## Incomplete items

4 of 21 approved brands have an incomplete catalogue and need manual work before they can be quoted from. Each reason below was established by fetching the site, not assumed.

### No products read (3 brands)

**Audio Press Box** — https://www.audiopressbox.com/

- Reason: Site reachable but serves no product listing; the page is a news and press service, not a product catalogue.
- Needed: the product line, entered manually or supplied by the manufacturer.

**K&M** — https://www.k-m.de/

- Reason: Official site returned HTTP 503 on every attempt.
- Needed: the product line, entered manually or supplied by the manufacturer.

**Cotodama** — https://www.cotodama.com/

- Reason: Official site timed out on every attempt.
- Needed: the product line, entered manually or supplied by the manufacturer.

### Partial: products were read but the scrape stopped early (1 brands)

**Sennheiser** — https://www.sennheiser.com/

- 400 products were imported successfully.
- Reason: The catalogue index is client-side and exposes no enumerable sitemap or product listing, so products were reached one page at a time and the run stopped at its request budget. The real total is higher than the count shown.
- Needed: the remaining products in that brand's line.

## Rows excluded from the catalogue

Non-product pages that the site crawl picked up were archived with a reason rather than deleted, so they can be reviewed and restored.

| Reason | Rows |
|---|---:|
| superseded by a later catalogue scrape | 119 |
| pre-import archive | 50 |
| newsroom press release, not a product | 46 |
| merchandise, not a product | 21 |
| corporate information page, not a product | 6 |

## Rows needing a title review

These have a correct official product URL but a scraped title that is a tagline or a fragment rather than the product name. They are active in the catalogue and flagged for a human to rename.

| Current title | Expected product | Source |
|---|---|---|
| Introducing The Quantum638 | Quantum 638 | https://digico.biz/consoles/quantum638/ |
| transform. engine | transform.engine | https://fourieraudio.com/transform-engine |
| transform. go | transform.go | https://fourieraudio.com/transform-go |
| ultra low latency between transform and DiGiCo consoles. | Fourier Audio HyperPort | https://fourieraudio.com/hyperport |
| Take control like never before. | MADRIX STELLA 8 | https://www.madrix.com/products/stella8/ |

## Data provenance and integrity

- Every scraped product has an official manufacturer URL and a `last_verified_at` timestamp.
- 15 products predate this import, were entered by hand, and have no scraped provenance. They were left untouched:

| Product | Brand |
|---|---|
| SD7 Digital Console | DiGiCo |
| SD12 Digital Console | DiGiCo |
| Quantum 338 Digital Console | DiGiCo |
| K2 Line Array Element | L-Acoustics |
| K1 Line Array Element | L-Acoustics |
| K2 Solo Line Array | L-Acoustics |
| XTG12 Loudspeaker | L-Acoustics |
| DP12 Delay Loudspeaker | L-Acoustics |
| MDX Loudspeaker Series | RCF |
| ART 9 Loudspeaker | RCF |
| SUB 8 Subwoofer | RCF |
| C-Mix 6 Digital Console | RCF |
| e965 Handheld Transmitter | Sennheiser |
| EW 112P G4 Wireless Lav | Sennheiser |
| HD 25 Headphones | Sennheiser |

- No product carries a price. Manufacturer catalogues do not list dealer pricing, so `price_status` is `pending` for every row.
- No duplicate product names exist within any brand.
- Every active product belongs to one of the 21 approved active brands; no orphans.
- Products are marked `product_status: discontinued` where the manufacturer says so, rather than being hidden.
- Where a source scrape produced unusable model numbers for a whole brand, the field was discarded rather than stored, because a wrong model number collides with a different product.
- RCF and ETC were re-scraped without the 400-product cap that the first pass applied, so their counts reflect the full catalogue rather than a truncated slice.

## Business data

The catalogue work touched only brands, product categories and products. Current business records:

- users: 45
- customers: 3
- contacts: 2
- leads: 0
- quotations: 0
- purchase_orders: 1
- projects: 3
- tasks: 15

Leads and quotations are both 0. The 11 leads and 37 quotations present earlier in this session were test fixtures written by the backend test suite into the live database (named `TEST_PDF_Customer`, `TEST_PDF_Glasshouse`, `TEST_Sales_Lead`, `TEST_SalesCo`, all created 2026-10-01 between 09:41 and 12:24). They have been removed, so the earlier counts were measuring test output, not business records. No real lead or quotation existed in this database.

Users are 45: the 43 staff imported from the staff directory plus `admin@hitechaudio.in` and `sales@hitechaudio.in`. The 43 staff have no invented email addresses or passwords and cannot sign in until credentials are supplied.
