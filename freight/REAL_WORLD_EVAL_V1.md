# FreightRecovery Real-World Evaluation Pack v1.0.0

**Prepared:** 2026-10-22  
**Scope:** retrospective public-source facts + synthetic, isolated engine exercises.  
**Operational state:** research-only. No customer invoices ingested into production, no original third-party documents stored here, no contacts or disputes sent, no identified customer recovery or billable fee.

## What is genuinely real, versus hypothetical?

Nine published source leads form four classes of challenge. This is not nine independently validated customer overcharges.

| Case IDs | Source and real anchor | Exercised behavior | Legal/commercial result |
| --- | --- | --- | --- |
| BIG_G_2026_FACE | Publicly accessible Big G freight bill: $387.00 linehaul + $50.16 fuel = $437.16; printed bill date 2026-02-18, ship date 2026-02-27 | Arithmetic, nine-day date-sequence review, **real** canonical/rating/evidence functions on explicitly fabricated buyer/shipper records | REVIEW_REQUIRED, **not** $437.16 recovery |
| PYLE_2021_FACE | Public A. Duie Pyle freight bill: $118.59 transportation + $59.13 liftgate + $17.20 fuel = $194.92. Fuel is 14.5% of the face transportation line, rounded to cents | Three-component reconciliation, surcharge rounding, production fail-closed review | Face arithmetic agrees; no buyer contract or payment truth, **not** a clean-rate label |
| EVERGREEN_TCW_2026_COURT | [D.C. Circuit, No. 25-1104](https://media.cadc.uscourts.gov/opinions/docs/2026/04/25-1104-2170734.pdf), opinion p.3–5: $1,490 invoiced detention; $510 challenged for May 23–25, 2020 port closure; FMC finding sustained on 2026-04-28 | $150 container/day + $20 chassis/day for three closed days = $510 | **Adjudicated historical reference**, not a new customer claim or recovered cash |
| GIBSON_FMC_2030I | [FMC administratively final notice, 2026-04-28](https://www2.fmc.gov/readingroom/docs/2030%28I%29/%2815%29%202030%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf): $8,668.79 reparations + $985.72 interest = $9,654.51 | Separate principal from interest and awarded total | Legal reparations reference; **not** proof that $9,654.51 was an invoice overcharge or paid by RETALLY |
| BAKERLY_SEAFRIGO_FMC | [FMC Second Series Vol. 8, Bakerly v. Seafrigo](https://www.fmc.gov/wp-content/uploads/2025/06/8-F.M.C.2d.pdf); $2,774,923.42 disputed across claims, Shipping Act claims dismissed | Adversarial negative **legal-outcome** reference | Neither a proven customer overcharge nor proof every underlying charge was correct |
| TESORO_2011_TRUCKING | [SEC EDGAR Exhibit 10.1, Schedule II](https://www.sec.gov/Archives/edgar/data/1507615/000150761511000033/exhibit101.htm): 40–45-mile band at $2.70/bbl, dispatch $0.50/bbl up to first 700k monthly barrels, $0.05 thereafter | Exact-cent 699,950→700,050 synthetic threshold split; reject ambiguous published 66–70 / 66–75 mileage overlap | Published historical rate facts; not established as controlling on any hypothetical shipment |
| MARATHON_2026_MARINE | [SEC EDGAR Exhibit 10.56, Exhibit B](https://www.sec.gov/Archives/edgar/data/1552000/000155200026000009/mplx-20251231xex1056.htm): Jan 2026 published C2 barge $1,006/day, H3 barge $2,408/day, B1 boat $6,094/day | Day rate × **synthetic** equipment days, with exclusions explicit | Partial-price exercise only; not a comprehensive charter invoice or governed rate |
| STB_2024_WAYBILL | [Surface Transportation Board Public Use Waybill Sample](https://www.stb.gov/reports-data/waybill/) | Future high-volume importer / shipment matching corpus | **Not downloaded here**; public rail revenue can be masked; not billing truth |
| EIA_DIESEL_HISTORY | [EIA fuel price series](https://www.eia.gov/petroleum/gasdiesel/) | Future date-indexed fuel context and stale-source tests | **Not downloaded here**; pump price by itself never authorizes a carrier surcharge |

For the two private-party invoices, the manifest deliberately contains *publisher domain only*; the original document-specific URL has identifiers and names and is withheld from the public repository. The other records link to official government or SEC publications. No invoice PDFs, source text, extracted party names, remittance information, customer identifiers, or payer documents are republished. Reuse and commercial data-processing rights must be independently confirmed.

## What the runnable test does

```bash
python -m pip install pytest==8.4.2
python -m pytest -q freight/test_real_world_eval_v1.py
python -m freight.real_world_eval_v1
```

The suite has no external network or credentials. It validates the rights/payload manifest, exact published money and date anchors, government outcomes and adversarial cases, and bounded synthetic historical-rate calculations. Two remapped numerical invoice faces are explicitly run through the **existing production** `freight.canonical_schema`, `freight.rating_engine`, and `freight.priority2_evidence`. They must remain `REVIEW_REQUIRED`, with absent buyer-specific contracts, independent shipment evidence and payment proof. The fixture SHA-256 is **only a digest of this curated JSON** and is NOT a byte-level hash of any original invoice or judgment.

The replay is added to the pre-existing read-only public-freight GitHub Actions workflow (Ubuntu + Windows), without changing production, branch protection, contact preferences, settlements or customer-data processing.

## Acceptance tiers / interpretation

1. **Tier 0 — public arithmetic, dates and legal-history facts:** validated here; never score as real invoice recovery precision.
2. **Tier 1 — original document extraction:** requires lawful private custody, original-byte hashes, redact-on-ingestion, PDF inspection, and a frozen baseline. Public original URLs alone are not a license for redistribution.
3. **Tier 2 — price authority:** requires a *specific buyer/carrier* executed rate agreement and amendment/effective-date reconciliation, with disputes for missing or overlapping terms.
4. **Tier 3 — economic correctness:** requires independent BOL/shipment events plus independently verified payments, credits, interest and refunds.
5. **Tier 4 — blind benchmark:** freeze model predictions before independent dual-review truth decisions; include adjudicated negatives and unresolved cases. Only then compute precision/recall.
6. **Tier 5 — operational recovery:** requires actual buyer authorization and independently verified carrier resolution/cleared payment. Nothing in this pack authorizes outreach or fees.

### Explicit exclusions

- A future-dated ship date on a bill is an anomaly, not evidence of fraud or an overcharge.
- A mathematically matching invoice is not proven contractually valid.
- An awarded legal remedy can contain interest/damages rather than an invoice-rate discrepancy.
- A claim's dismissal is not a certification that every charge was justifiable.
- SEC transport terms can have other escalators, approvals, vessel services, add-ons, minimums, and historical amendments. The test only models the highlighted numbers.
- STB revenue masks, EIA spot prices and unrelated judicial precedents cannot substitute for a specific customer's contract or bank entry.

**Truth accounting:** original documents processed for this pack **0**; new independently matched buyer invoices **0**; newly verified recoverable claims **0**; RETALLY recovered cash **$0**; customer accuracy/precision/recall **not estimable**.

Existing separate original-document work is in `freight/REAL_DOCUMENT_LAB.md`, and earlier public sources in `freight/PUBLIC_FREIGHT_SOURCE_LAB_2026-10-22.md`. Do not pool their unlabeled invoice records into the adjudicated-legal-reference cases or assert a larger labeled sample.
