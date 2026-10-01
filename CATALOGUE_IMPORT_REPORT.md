# Product Catalogue Import Report

Generated: 2026-10-01 12:23 UTC

**2,453 active products** imported across **17 of 21** approved brands.

Every product below carries its manufacturer's own official URL and the date it was read. No model, specification, price or description was invented. Where a catalogue could not be read, the brand is recorded as needing manual import rather than left silently empty.

## Per-brand counts

| Brand | Active products | Discontinued | Official site | Status |
|---|---:|---:|---|---|
| RCF | 404 |  | https://www.rcf.it/ | complete |
| L-Acoustics | 316 |  | https://www.l-acoustics.com/ | complete |
| DiGiCo | 81 |  | https://digico.biz/ | complete |
| TT+ Audio | 117 |  | https://www.ttaudio.com/ | complete |
| Sound Devices | 215 |  | https://www.sounddevices.com/ | complete |
| Klang Technologies | 13 |  | https://www.klang.com/ | complete |
| Radial Engineering | 196 |  | https://www.radialeng.com/ | complete |
| Fourier Audio | 5 |  | https://fourieraudio.com/ | complete |
| Audio Press Box | 0 |  | https://www.audiopressbox.com/ | **needs manual import** |
| MA Lighting | 119 |  | https://www.malighting.com/ | complete |
| MADRIX | 12 |  | https://www.madrix.com/ | complete |
| ETC | 400 |  | https://www.etcconnect.com/ | complete |
| Zactrack | 0 |  | https://www.zactrack.com/ | **needs manual import** |
| Luminex | 44 | 16 | https://www.luminex.be/ | complete |
| Klotz | 14 |  | https://www.klotz-ais.com/ | complete |
| K&M | 0 |  | https://www.k-m.de/ | **needs manual import** |
| Sennheiser | 3 |  | https://www.sennheiser.com/ | complete |
| Cotodama | 0 |  | https://www.cotodama.com/ | **needs manual import** |
| DPA Microphones | 202 |  | https://www.dpamicrophones.com/ | complete |
| JH Audio | 38 |  | https://jhaudio.com/ | complete |
| Wisycom | 274 |  | https://wisycom.com/ | complete |
| **Total** | **2,453** | | | |

## Incomplete items

4 of 21 approved brands have no imported products. Each reason below was verified by fetching the site, not assumed.

### Audio Press Box

- Official site: https://www.audiopressbox.com/
- Reason: Site reachable but serves no product listing; the page is a news and press service, not a product catalogue.
- Needed to complete: the product list from Audio Press Box's current catalogue, entered manually or supplied by the manufacturer.

### Zactrack

- Official site: https://www.zactrack.com/
- Reason: Site is a JavaScript application. Product data loads from an API that is not exposed as server-rendered links or a sitemap, so no product URL could be read.
- Needed to complete: the product list from Zactrack's current catalogue, entered manually or supplied by the manufacturer.

### K&M

- Official site: https://www.k-m.de/
- Reason: Official site returned HTTP 503 on every attempt.
- Needed to complete: the product list from K&M's current catalogue, entered manually or supplied by the manufacturer.

### Cotodama

- Official site: https://www.cotodama.com/
- Reason: Official site timed out on every attempt.
- Needed to complete: the product list from Cotodama's current catalogue, entered manually or supplied by the manufacturer.

## Rows excluded from the catalogue

Non-product pages that the site crawl picked up were archived with a reason rather than deleted, so they can be reviewed and restored.

| Reason | Rows |
|---|---:|
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

- Every active product has an official manufacturer URL and a `last_verified_at` timestamp, except 15 pre-existing products that predate this import and were left untouched.
- No product carries a price. Manufacturer catalogues do not list dealer pricing, so `price_status` is `pending` for all rows.
- No duplicate product names exist within any brand.
- Every active product belongs to one of the 21 approved active brands; no orphans.
- Products scraped from a manufacturer are marked `product_status: discontinued` where the manufacturer says so, rather than being hidden.
- Where a source scrape produced unusable model numbers for a whole brand, the field was discarded rather than stored, because a wrong model number can collide with a different product.

## Business data

The import touched only brands, product categories and products. Existing business records are unchanged:

- users: 45 (43 imported staff, plus `admin@hitechaudio.in` and `sales@hitechaudio.in`)
- customers: 3 (Taj Hotels, Marriott International, ITC Hotels)
- contacts: 2
- quotations: 37
- purchase orders: 1
- projects: 3
- leads: 0

On leads: the 11 lead rows previously present were test fixtures created by the backend test suite (named `TEST_PDF_Customer`, `TEST_PDF_Glasshouse`, `TEST_Sales_Lead`, all timestamped 2026-10-01 between 09:41 and 10:08). They were removed, so the real lead count is 0. The earlier "leads 11" figure counted those fixtures, not business records.
