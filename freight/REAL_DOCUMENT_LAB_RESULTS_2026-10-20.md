# RETALLY Real-Document Test Laboratory — 2026-10-20

**Disposition:** research-only benchmark **PASSED**; freight detection accuracy
**NOT ASSESSABLE**; production PDF-extraction acceptance **NOT PASSED**.
No approved commercial recovery, verified refund or first-customer accuracy claim.

**Reproducible run:** https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39354189557
**Tested source commit:** ff2a5174ff16cebf98fef1b8b5de0806d21f3342
**Isolation:** read-only GitHub-hosted Ubuntu runner, no checkout credentials
retained, no Git writes, raw invoice bytes or extracted invoice rows committed,
no uploaded artifacts. Research scope only.

## Original-document extraction

| Original source | Pages | Invoice faces | Extracted face amounts | Native RETALLY PDF route |
|---|---:|---:|---:|---|
| GlobalTranz / Walker & Zanger | 120 | 100 distinct | 100/100 | DOCUMENT_EXTRACTION_REQUIRED |
| ArcBest / SDI USA | 74 | 10 | 10/10 | DOCUMENT_EXTRACTION_REQUIRED |

- Direct original PDF sources:
  - GlobalTranz: https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247
  - ArcBest: https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/408
- Input SHA-256:
  - GlobalTranz: 45d4b8fae33234d3b9efe087e60a10dc5f6fc45f8cc9f5099560c6c63bfb33b4
  - ArcBest: 4c3e2f69ae7414bcebacd7d74f31320c2dad37d18f5e85370f46f00aca0bbb17
- Fifteen previously observed public face-value anchors passed (5 GlobalTranz
  and 10 ArcBest). The lab uses PyMuPDF as a **separate, research-only**
  extraction adapter; RETALLY's native PDF ingress is a request for extraction,
  not an already deployed PDF invoice extraction engine.

### GlobalTranz statement reconciliation

- All **100/100** original invoice faces share exact **invoice identifiers
  and original dollar amounts** with statement entries.
- The 6-page account statement contains **102 distinct invoice entries**.
  Two entries have no corresponding extracted invoice face in the exhibit.
- Actual RETALLY reconciliation kernel matched **98/100** invoice faces to
  statement entries under the configured 180-day window. The remaining **two**
  matching identifier-and-amount pairs exceed the date bound (maximum gap in
  the population: **207 days**). This is **date-window review**, not an amount
  mismatch or evidence of fraud.
- Statement original charges: **$26,026.61**; stated current balance:
  **$25,954.47**; difference: **$72.14**. The statement is **not independent
  payment or credit settlement evidence**. The difference is not asserted as
  recovered cash or an overcharge.

### ArcBest freight engine smoke test

- The real freight canonical schema and freight rating engine were invoked on
  **five** laboratory proxy records made from the original PDF's observed
  shipment information. All five returned **REVIEW_REQUIRED**, with no
  unsupported expected rate, variance or dollar recovery.
- Five other invoices remained normalization-blocked: three had unreadable
  billed pieces/weight, one had nonpositive billed pieces/weight, and one had
  ambiguous origin/destination postal extraction.
- The five smoke-test records are **NOT admissible for real rating accuracy**:
  shipment date substitutes for missing invoice-issue date, bill-reported
  rated weight substitutes for independently established actual weight, and
  invoice grand total substitutes for true per-charge rate lines.
- No controlling customer tariff/rate was independently verified; all ten
  remain freight **UNKNOWN/REVIEW**, not proven carrier errors.

## Pennine Care general-accounting benchmark (separate from freight)

Monthly source CSVs for April–August 2026 are under the UK Open Government
Licence: https://www.data.gov.uk/dataset/31ef5153-cf9c-45f7-9bcf-e2c86200d00b/spend-over-25-000-in-pennine-care-nhs-foundation-trust

- Original source row counts: April **67**, May **53**, June **50**,
  July **103**, August **41**; total **314** disclosed rows.
- Deduplication by supplier, invoice ID, invoice date and exact integer-penny
  amount yielded **273 unique invoice identities** and **41 repeated
  cross-month disclosures**; no changed payment reference for a repeated
  identity. Repeated disclosures are **not duplicate payments**.
- Deduplicated source-declared invoice amount total: **£74,236,677.42**,
  not cleared bank outflow and not RETALLY-recovered revenue.
- **217** source-declared payment-reference/date/currency groups; 178 single
  invoice groups and 39 legitimate multiple-invoice groups (largest: eight).
- With original RETALLY kernel on one unpartitioned population:
  **195/273** invoices matched and **78** remained unmatched. The native
  many-to-one search uses a first-18 candidate bound across different
  references and can miss valid larger-population groups.
- With the **same real RETALLY kernel** invoked separately per exact
  source-declared payment reference (max group size eight):
  **273/273** matched, **217/217** groups, **0** incorrect payment-reference
  joins, **0** unmatched invoice declarations. This is a valid same-source
  structural join/amount-conservation check, **not independent payment
  verification**.
- Money is parsed in integer minor units; malformed comma grouping, fractional
  overprecision, NaN, exponential amounts and invalid dates fail closed.
- Real economic false-positive and duplicate-payment rates are
  **not estimable** without a second, independent bank/payment ledger.

## Blind freight evaluation and historical references

- Total authentic extracted freight invoice identities: **110**.
- Independently labeled true-positive or true-negative cases with complete
  original invoice + controlling effective rate + actual payment + independent
  adjudication: **0**.
- Unknown/held for further evidence: **110**.
- **Precision, recall, specificity and freight detection accuracy: NULL /
  NOT ESTIMABLE**, not zero percent and not 100 percent.
- Eight historical U.S. GAO rulings are indexed as adjudication reference
  leads. The runner received HTTP errors trying to fetch their source pages.
  Three separately inspected published decisions were registered as
  **non-scoring** challenge precedents:
  - https://www.gao.gov/products/b-143246 — mixed-commodity package rating,
    government audit sustained after partial allowance.
  - https://www.gao.gov/products/b-148465 — historical overcharge collected
    by offset after routing/rate dispute.
  - https://www.gao.gov/products/b-221594-0 — government overcharge
    determination reversed because the tender used for lower rates had been
    rejected; negative/false-positive authority example.
- None of those historical cases labels any GlobalTranz or ArcBest invoice in
  the present documents. No historical settlement is RETALLY's own recovery.

## Gate conclusion

**Research laboratory: GREEN. Customer-proof/real-accuracy acceptance: HOLD.**

Remaining evidence gaps: native production PDF extractor, provenance-complete
shipment and line-item facts, shipment-specific effective contractual rate,
independent bank-cleared payments/refunds, a blinded independently adjudicated
linked positive-and-negative freight population, and separate commercial
authorization/release review. Do not merge as a substitute for independent PR
review, deploy customer-facing claims, or contact any third party from this lab.
