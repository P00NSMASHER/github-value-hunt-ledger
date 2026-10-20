# RETALLY — real-document laboratory, frozen research benchmark

**Date:** 2026-10-19 US/Eastern (executed 2026-10-20 UTC). **Scope:** research only.
**Verdict:** **ACCOUNTING MATCHING QUALITY FAIL / REAL FREIGHT ACCURACY UNMEASURABLE**.
**Actual GitHub Actions execution (head 3b9e3d9ce9b18740418dbbee848f77195ad7b67a):**
https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39351956212

## 1. Exact original-document ingestion

Public, original court-exhibit PDFs were downloaded directly to a short-lived
GitHub Actions process, without repository storage or artifact upload. The actual
RETALLY `freight.ingestion_gateway.ingest_bytes` accepted both:

| Original issued document | Pages | Verified SHA-256 | Real ingress | Independent document-text control |
| --- | ---: | --- | --- | --- |
| GlobalTranz broker-issued invoice exhibits | 120 | `45d4b8fae33234d3b9efe087e60a10dc5f6fc45f8cc9f5099560c6c63bfb33b4` | ACCEPT → DOCUMENT_EXTRACTION_REQUIRED | 5/5 independent invoice-amount pairs locatable in page text |
| ArcBest/ABF original carrier invoice exhibits | 74 | `4c3e2f69ae7414bcebacd7d74f31320c2dad37d18f5e85370f46f00aca0bbb17` | ACCEPT → DOCUMENT_EXTRACTION_REQUIRED | 10/10 independent invoice-amount pairs locatable in page text |

The exploratory *nonproduction* PDF text parser matched labeled identifier and
amount fields **0/5 GlobalTranz and 10/10 ArcBest**. The failed GlobalTranz
table layout extraction must not be counted as accurate. The document-text
locatability control is **not** field-extraction accuracy and cannot be used
as a blind generalization metric. No OCR was performed. The PDF ingestion gateway
has no production invoice-field extractor, so original PDFs could **not** be
normalized to freight records trustworthy enough for `rate_record`.
**Actual freight rating invocations: 0. Controlling-rate authorities: 0.
Verified overcharge labels: 0.** No made-up rate/shipment/payment fields were
injected to force a billing number.

## 2. Real licensed Pennine Care accounting benchmark (separate from freight)

Real publisher source: April–August 2026 official CSVs, UK Open Government
Licence v3; five original SHA-256 fingerprints are pinned in
`freight/research/real_document_engine_lab.py`.
The benchmark re-downloaded the sources and exercised the unmodified actual
`recoveryworks.reconciliation_kernel.reconcile` and `parse_amount_to_minor`.
Source payment annotations were formed from the *same publisher rows*, **not**
from independent bank remittances.

- **314** published records; **273** economic invoice identities.
- **41** August entries repeat July with unchanged identity, reported amount
  and payment reference; these are republication, **not double payment**.
- **£74,236,677.42** unique source-reported invoice face value.
- **273/273 exact** independent-vs-kernel decimal-to-cents comparisons.
- **39** payment references occur on more than one unique invoice; multi-invoice
  payment references are ordinary, not proof of fraud or duplicated cash.

| Kernel configuration | Matched pairs | Correct publisher associations | Incorrect associations | Unmatched invoices |
| --- | ---: | ---: | ---: | ---: |
| Real invoice ref vs reported payment ref; **3-day** matching | 36 | 25 | **11** | 237 |
| Same genuine refs, expanded **365-day** matching | 271 | 265 | **6** | 2 |
| Source identity propagated to both sides, control only | 273 | 273 | 0 | 0 |

The last row deliberately supplies identical identifiers and dates to the two
sides, so its perfect match is an **identity-transmission control, not evidence
of autonomous payment reconstruction**. The other two configurations reveal
**source-association false joins** from generic amount/date fallback.
A source-association mismatch is a useful accounting benchmark failure, **not**
a verified wrongly bank-cleared payment or freight invoice overcharge.

**Quality gate: FAIL_UNSAFE_GENERIC_CROSS_INVOICE_JOINS**.
Production customer settlement decisions must **not** auto-promote weak
amount/date joins absent independent identity/payment corroboration. A 365-day
window increases coverage but does not eliminate misjoins.

## 3. Historical blinded freight evaluation — unknown truth stays unknown

Eight named public GAO reference decisions are inventoried. None constitutes
a complete independent frozen per-shipment truth record that binds **all**
original issued invoice, governing effective carrier rate, shipment
evidence, independent actual payment, independent overcharge adjudication,
and blinded operator/reviewer checks. All **8/8 are UNRESOLVED for RETALLY
shipment-level detection**; they are not presumed negative even where a court
issued a disposition on a narrower issue.

**Eligible freight cases: 0. Precision/recall/specificity/accuracy: N/A.**
No true-positive, true-negative, false-positive or false-negative RATE is
reported. No freight recoveries or independently bank-confirmed payments.

`blind_score` enforces per-case completeness and reviewer-independence
booleans before inclusion; synthetic unit tests exercise known labels, but those
test cases are never counted as real freight evidence.

## 4. Tested boundaries and next corrective work

- Real CSV bytes and original PDF bytes stay in ephemeral runner process memory.
  No bank numbers, invoice IDs, customers, source rows, raw PDF, or access secrets
  are published in test reports or committed.
- Five isolated synthetic lab-safety/unit tests passed, the official ledger
  replay passed, and repository-level existing CI succeeded on that exact head.
  **Diagnostic job pass does not override the financial quality gate failure.**
- To rate the original freight bills: implement an independently reviewed
  field extractor with invoice layout controls, normalize only real observed
  shipment/charge facts, independently bind effective governing rates, and keep
  unresolved cases `REVIEW_REQUIRED`.
- To fix the accounting defect: require supplier/currency/invoice identity
  or an independently linked remittance key for automatic posting; route
  amount/date-only candidates to review and regression-test those 6–11
  source-association counterexamples without publishing source rows.
- To measure freight precision/recall: freeze a licensed real shipment cohort,
  independent adjudications and the engine output separately, then unseal and
  score only fully labeled cases in the existing audit-acceptance process.

**Do not merge or describe this diagnostic as customer-ready freight accuracy
evidence without independent review.** No outreach, release, real customer
invoicing, confirmed recovery, or paid services were performed.
