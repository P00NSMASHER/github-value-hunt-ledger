# RETALLY official-source freight test collection — October 22, 2026

**Scope: research only; no customer data, carrier contact, new spending, payment, recovery or commercial launch.**

This is a real-publisher **facts-and-rights corpus**, not an ingested collection of third-party original files. It stores five official source URLs, reuse status, safe public numerical facts and provenance pointers. The engine tests use **fictional shipments, identifiers, buyer scopes and dates** with the source-published rate figures. No original public PDFs, SEC agreements, tariff tables, invoice IDs, addresses, account numbers, names or payment rows are copied into this public repository.

## Verified source registry and rights

| Corpus ID | Public official source | Rights finding | Data permitted inside this corpus |
|---|---|---|---|
| SEC_BULK_2007 | [SEC Exhibit 10.1](https://www.sec.gov/Archives/edgar/data/1337226/000092290707000474/form8kexh101_072507.htm), Exhibit A | [SEC EDGAR filings free to reuse](https://www.sec.gov/about/webmaster-frequently-asked-questions) | Historical $0.01299/gallon and $0.0003/gallon historical fuel-step numerical anchors, applied only to explicitly synthetic quantities. |
| SEC_INTERMODAL_2013 | [SEC operating agreement](https://www.sec.gov/Archives/edgar/data/739878/000119312514144221/d658018dex1063.htm), Schedule 2.1, p.43 | Same SEC license | Historical $2,425 Kentwood–Chino and $2,300 Cranbury–Chino fuel-inclusive lane figures; two synthetic lane-isolated probes. Schedule has 30-day quote/contract caveats, fuel and rail revisions; no signed governing rate established for a real shipment. |
| GAO_B160344 | [Official 1967 GAO freight-classification ruling](https://www.gao.gov/products/b-160344) | [GAO freely reusable with acknowledgment; no GAO endorsement](https://www.gao.gov/copyright) | Reference decision arithmetic ($275.17 paid; $139.29 allowable; $135.88 historically offset), not a RETALLY recovery, not a label on any other invoice. |
| OD_FUEL_2026 | [Old Dominion fuel surcharge schedule](https://www.odfl.com/us/en/resources/fuel-surcharge.html) | [Terms only license informational use; other use requires permission](https://www.odfl.com/us/en/terms-and-conditions.html) | URL and permission decision **only**. No table copied, no commercial tariff rerating. |
| KENTUCKY_PSC_2024 | [Kentucky PSC case 2025-00354](https://psc.ky.gov/Case/ViewCaseFilings/2025-00354), Exhibit PSC 1-13 Part 8(b), pp.2323/2326 | Public filing; **third-party commercial reuse rights unverified** | Public numerical facts $184.00 freight and $200.56 associated **expense** (1.09×). No original file, invoice ID, remittance, raw OCR/text or personal/business contact data. Only a synthetic invoice and **no** supposed bank counterpart enter the test. |

### What was deliberately excluded

The Kentucky PDF is about 40 MB and contains customer/billing data and the filing path includes a submitter email. Only the **email-free docket URL** is retained; no PDF was downloaded into this new corpus, copied, retained, exposed in CI or public artifacts. The Old Dominion table is not copied, downloaded into CI, or used as buyer-specific rate authority. The more extensive existing GlobalTranz/ArcBest real-document lab remains separate; its original 110 cases still lack independently authenticated rate/payment/adjudication labels and remain **UNKNOWN**.

**Provenance precision:** `PublicSource.url_sha256` and `catalog_sha256()` hash **metadata/locators only**, NOT original document bytes. All original-byte SHA-256 fields are null. The model's fictional synthetic source hash is explicitly labeled *not an original document*. This new lab does not pretend that web visibility, a hash, or a regulatory filing authorizes a real customer's claim.

## What the actual RETALLY engine tests

- **Rerating and fuel double-counting:** `intermodal_probe()` feeds the two official historical lane *prices* through the real `rate_record` / `review_freight_rate` functions, but with obviously synthetic shipment records, unverified compiled authorities and no bank evidence. The fuel-inclusive rate must calculate zero additional fuel; both return **REVIEW_REQUIRED**, not an approved economic recovery.
- **Cross-lane/date false positives:** native intermodal authority lacks lane fields, so the lab must enforce an exact lane/date gate before calling it. Wrong lane, direction, shipment date or unsupported price rejects; a 2026 invoice cannot automatically inherit a 2013 price.
- **Public historical arithmetic:** the SEC's $0.01299/gallon and one published $0.0003/gallon fuel step yield $13.29 for a hypothetical 1,000-gallon load; the GAO's $275.17–$139.29 calculation is $135.88 (historically adjudicated by GAO, not recovered by RETALLY).
- **Original invoice vs expense:** Kentucky's $184/$200.56 are not a carrier mismatch. `reconcile_scoped` receives only the *fabricated-ID* $184 invoice fact and an **empty** bank counterpart set; result must be unmatched with zero bank-cleared proof and no inferred recovered cash.
- **True-label safeguard:** `score_sealed_freight` rejects treating the unrelated GAO decision as independently validated truth for a new fictional buyer, leaving one `UNRESOLVED`, zero scored automatic decisions and null accuracy metrics.
- **Rights and lifecycle:** source allowlist, informational-only originals, no commercial redistribution, zero byte provenance, zero customer-data ingestion, and zero actual billing/recovery are tested explicitly.

## Run

```sh
python -m pytest -q freight/test_public_freight_corpus.py
python -m freight.public_freight_corpus
```

An isolated, read-only GitHub Action runs the same source tests on **Ubuntu and Windows**. It needs no network, credentials, original public invoice files, outside customer systems, commerce permissions or secrets. The report prints safe aggregate metadata only. Guarded protected-main release checks remain in force.

## Open gates

Before a **real** benchmark using the Kentucky/OD original bytes: confirm owner-level commercial processing and copying rights, independent source custody and privacy controls, relevant effective buyer/carrier contract and amendments, genuine bill of lading/weight, independently verified payment/credit ledger, and independent blinded freight adjudication including clean negative cases. Source-only price scenarios do not establish a false-positive rate or proof of business value.

**Real customer recovery and billable fees: $0 verified. Precision/recall: NOT ESTIMABLE.**
