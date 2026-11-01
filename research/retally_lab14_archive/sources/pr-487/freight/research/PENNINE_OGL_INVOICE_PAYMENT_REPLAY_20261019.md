# RETALLY — verified actual OGL invoice-to-payment ledger replay
**Date:** 2026-10-19. **Status:** REAL PUBLISHED LEDGER DATA TESTED, NOT FREIGHT ERROR / CASH RECOVERY VALIDATED.

This is a **new actual, rights-cleared invoice-to-payment *ledger*** source, separate from historical GAO or GlobalTranz cases. We independently downloaded and profiled actual publisher CSV bytes in a read-only GitHub Actions runner. The original financial rows, supplier names, bank/remittance fields, original downloads and invoice IDs were never committed or logged.

**Original publisher:** Pennine Care NHS Foundation Trust. [Official UK open-data catalog, listing monthly source CSVs and UK Open Government Licence](https://www.data.gov.uk/dataset/31ef5153-cf9c-45f7-9bcf-e2c86200d00b/spend-over-25-000-in-pennine-care-nhs-foundation-trust). Original source is **OGL v3**, permitting commercial reuse of licensed information with attribution, subject to exclusions for third-party rights and personal information; do not assume a license for any separately linked contract/invoice image. Scope **published expenditure over GBP25,000**; below-threshold and redacted records cannot be inferred as absent from the underlying accounts.

**Exact runner receipt:** [public dataset validation GitHub Actions run 39211034165](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39211034165). Source aggregation and deep overlap audit completed successfully; 16 deterministic synthetic unit tests passed; zero actual RETALLY recoveries asserted. The tests use only synthetic invoice IDs.

## Downloaded source chain and independent content fingerprints

All original URLs below link directly to the publisher's CSV and are available for separate inspection. SHA-256 is calculated over exact downloaded bytes at replay time. There is **no cached public raw financial file in this repository**.

| Named report | Original publisher CSV | Rows | Exact source SHA-256 | Reported invoice amount (GBP) |
| --- | --- | ---: | --- | ---: |
| Apr 2026 | https://www.penninecare.nhs.uk/download_file/5855/277 | 67 | `314cd0c021f137b43b94e81bb93f26aece5b3b0a021e99c42d43546a640c3d90` | £13,917,299.57 |
| May 2026 | https://www.penninecare.nhs.uk/download_file/5874/277 | 53 | `5957ead9c23d57039e267dc18076c7b8d711a14b97cbea6d9a9ff0629aeb5028` | £14,307,737.82 |
| Jun 2026 | https://www.penninecare.nhs.uk/download_file/5910/277 | 50 | `318aeeedbf55d05bcffce5076ac893a84bdb6ebe5e7c851bb3f3c45dbbdea8fc` | £16,029,528.58 |
| Jul 2026 | https://www.penninecare.nhs.uk/download_file/5920/277 | 103 | `ecb986bd0e33cf402f7cb86ff68bc91368d18a5dfc39410e4e2019c045c3de15` | £29,982,111.45 |
| Aug 2026 | https://www.penninecare.nhs.uk/download_file/5941/277 | 41 | `4153ccbbbe27307afddba1d6651bfd9db8a774cc84e4fd23d62b3a2d1059d796` | £12,988,598.24 **ALREADY IN JULY** |

For each CSV, measured complete supported fields: supplier number, invoice number, invoice date and GBP invoice amount, payment number, date, method and `Fully paid` accounting status. No malformed required fields, amounts or dates were observed in these five files. The published `Invoice Amount` is NOT an independently bank-confirmed per-invoice remittance.

## Most important new data quality result — avoid 41 false double-counts

- **314 published rows**, but only **273 distinct invoice identities**, keyed by (supplier number, original invoice reference, invoice date). Publisher CSVs are period-labeled but not disjoint.
- **41 August records appear *verbatim by invoice identity, reported invoice amount AND payment reference* in July's CSV**, with no newly distinct invoice in August's file. The July file itself includes payments with August dates (to **2026-08-10**); the August file covers **2026-08-04 through 2026-08-10**. This supports **overlapping reporting snapshots**, NOT two actual payments.
- Raw reported invoice-face sum across five files is **£87,225,275.66**; **£12,988,598.24** is repeated in both July and August. **Unique invoice-face sum: £74,236,677.42**.
- All 314 rows passed source-supported invoice/payment-reference structural checks (100%); this is not proof that all external source invoices are present, that exact remitted amounts equal invoice amounts, or that any transaction is a true freight overcharge.
- August required skipping exactly **two report title/preamble rows** before the actual header. These are now detected rather than counted as invoices.

**Critical rule:** duplicate appearance in two *period reports* with identical payment references must be treated as repeated publication, not a second payment, fraud, price error, credit, or recovery. This is a valuable *real-data* negative control for a RETALLY billing ingest and dedup layer.

## Actual software checks executed

- Only exact HTTPS publisher CSV URLs accepted; bounded read of at most 4 MB each, same-publisher redirects only, zero secret/API key or credentials.
- Reproducible source content SHA-256; field validation, precise integer-cents decimal conversion, invoice/pay date consistency; stable composite invoice key.
- Different invoices legitimately sharing one payment reference do **not** trigger double-payment flags.
- Cross-month repeated invoices are detected separately from second payment references and changed original invoice values; false recoveries remain zero.
- Payment dates outside a named month and report-preamble lines are flagged, keeping payment-month slicing and import coverage honest.
- Actual source data processed only in memory on a read-only PR CI job; logs include **aggregates and SHA** only, no original supplier/invoice rows, raw CSV, payment-level ledger or bank data.

**Reproduce:** `PYTHONPATH=. python -m unittest -v freight.test_public_invoice_payment_validation` and, in an authorized short-lived network environment, `PYTHONPATH=. python -m freight.research.public_invoice_payment_validation --live-all`. The GitHub Actions workflow runs on changes to the isolated research file/test/workflow, never on a schedule, and has read-only contents permission. No production data movement.

## Fit for purpose and outstanding freight-specific validation gap

**PASS (scope-limited):** a genuine, downloadable, originally published, commercial-reuse-licensed **supplier invoice-reference → actual payment-reference/date/status *accounting-ledger dataset***, with verified real rows and separate evidence of cross-publication duplication. This **closes the absence-of-real-licensed-ledger-data gap for general accounts-payable matching**.

**NOT ESTABLISHED:**
- Original scanned/issued **carrier** invoices; original bill PDFs are not included.
- Underlying shipment PRO/BOL/POD or controlling tariff/rate/contract and independent weight/classification.
- Independently reconciled bank/clearing evidence proving **actual cash amount** per invoice. "Fully paid" is the source accounting status; it is not an external bank confirmation.
- Original customer freight overcharge error adjudications or contemporaneous customer credits/refund settlement.
- Blinded adjudicated real-world RETALLY freight accuracy or any verified RETALLY recovered cash.

This is a **licensed payment-event test corpus**, not a fully adjudicated, end-to-end freight-recovery benchmark. It does NOT supersede the GlobalTranz Artivo noncash-transfer negative control, PR release/commercial holds, and invoice rights rules. Do not merge/promote as commercial freight accuracy proof.

**Attribution if used commercially:** "Contains public sector information licensed under the Open Government Licence v3.0, published by Pennine Care NHS Foundation Trust via data.gov.uk; downloaded Oct 19, 2026 and transformed for source-linked deduplication by RETALLY." Link both original publisher dataset and OGL v3 terms; note transformations and scope limits.
