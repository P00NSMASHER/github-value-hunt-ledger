# RecoveryOS Healthcare Purchasing Audit Engine — isolated research build

**Status: synthetic, read-only engineering prototype. Not a customer production service, proof of real recoveries, or a certified healthcare-compliant deployment.** No employer system, Panacea data, patient records, bank data, or vendor outreach is involved.

Additive, standard-library-only package intended for evaluation within the `P00NSMASHER/github-value-hunt-ledger` RecoveryOS Python repository. Its local development environment does **not** include the full parent repository. No parent regressions, integration CI, shared-workbench wiring, or live customer acceptance is claimed.

## Capabilities

- Authorized, SHA-256-bound JSON intake with declared population counts and typed reject/hold outcomes.
- Immutable, buyer/facility/supplier/account-scoped records and deterministic evidence references.
- Exact decimal prices with explicitly dated fixed-pack conversions and controlling contract-date selection.
- Cumulative accepted-receipt allocation, documented quantity decisions and cancelled/replaced invoice controls.
- Split-payment support; reused-identifier and over-reversal holds; genuine duplicate payment candidates.
- Supplier credits tracked separately as issued, applied, refunded, reversed and unapplied.
- Returns require externally established, pre-assessed entitlement terms and source references; no supplier-policy guessing.
- Cross-detector economic-loss deduplication; no invoice discrepancy is ever automatically promoted to a claim.
- Reports distinguish billed, expected, paid, review candidate, supplier credits and **verified realized: 0**. CSV protects leading spreadsheet formula characters.

## Run

From the repository root with Python 3.11+:

```sh
python -m unittest discover -s recoveryworks/healthcare -p 'test_*.py' -v
python -m recoveryworks.healthcare.demo > /tmp/retally-healthcare-synthetic-report.json
```

The demo uses made-up values: 100 cases billed at $31/case versus a $28/case contract, a $3,100 payment, and a $100 preexisting applied credit. The remaining **review-only candidate** is $200, not $300; the engine reports $0 verified recovered. Those values are arithmetic demonstrations, not customer financial evidence.

## Programmatic workflow

1. Create an approved scope (`ScopeKey`, `ApprovedScope`) with exact original-document hash, each table's expected row count, calendar boundaries, and explicit `synthetic` status.
2. Invoke `import_json(original_bytes, approved_scope)` and `validate_batch(import_batch, approved_scope)`; do not treat exceptions as an empty clean audit.
3. Pass a `RuleSetVersion` with full commit/config digests into `run_audit(canonical_batch, rules)`.
4. Read `result.holds` and `result.findings`. All findings remain `REVIEW`, **never `VALIDATED`, `CLAIMED`, or `RECOVERED`**.
5. Use `build_report(result, canonical_batch)` then `export_report(report, 'json' | 'csv')` for private local analysis.

`SourceRef` hashes record supplied source bytes, **not the authenticity of a supplier agreement, delivery, or bank event**. Real proof requires independently inspected source authority and payment/settlement channels. The financial core never makes outbound requests, posts to an ERP, or initiates claims.

## Explicit limitations

- Input is an approved typed JSON dataset. Production CSV mapping, arbitrary PDFs/OCR, supplier-specific pricing/tax/discount rules, hosted access, identity, retention, enterprise database state and settlement attestation are **not implemented**.
- Fixed-pack, USD, non-pharmaceutical goods with one selected authority per scope/product/date and accepted receipts. Missing or ambiguous rules produce holds.
- Quantity decisions require an explicit unit. An unsigned `verified=true` or arbitrary source hash cannot establish entitlement.
- Credit applications and refunds are accepted as synthetic accounting records, but `verified_realized_cents` is locked to zero because there is no issuer-authenticated live verification.
- Current tests are synthetic. A held-out finance-labeled real-document benchmark and existing parent-repository CI are still mandatory before any customer-data pilot.
- No PHI is needed or authorized in this package. Unexpected sensitive information must follow approved organizational handling procedures.

See `docs/RETALLY_Healthcare_Product_Spec.md` and `docs/RETALLY_Healthcare_Implementation_Plan.md` for the broader plan and remaining tasks.
