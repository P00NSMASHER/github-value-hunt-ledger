# RETALLY R1 — financial integrity (proposed, not production approved)

## Compatibility

- v1 canonical freight invoices retain exactly their old hash and JSON
  when no adjustments exist.
- v2 adds original-document-bound typed DISCOUNT / INVOICE_CREDIT
  magnitudes. Arbitrary negative rated charge lines remain forbidden.
  Gross charges - original invoice discounts/credits = billed net in
  exact integer cents.
- Bank payments, post-invoice credits, refunds and full-event reversals
  are immutable separate ledger entries and cannot change original
  invoice identity.
- The financial claim gate exposes rate discrepancy separately from
  independently adjudicated validated opportunity and independently
  observed realized cash. Missing governing rates / payment / adjudication /
  human authorization produce 0 validated dollars. In the R1 engine,
  realized cash remains 0 until independent recovery-allocation support
  has been separately authorized.
- The existing pinned reconciliation kernel remains unchanged. A separate
  buyer/business-unit/counterparty/currency/reference-scoped caller
  prevents unrelated amounts from matching merely because dates and money
  agree, while retaining bounded many-to-one replay and review holds.

## Deliberate safeguards

This is a code candidate, not authorization to import additional buyer data,
run customer collections, assert freight detection accuracy or make production
financial changes. Independent review, CI, existing pilot/release gates and
original-document replay are required. Issue #509 is only closed when the
production-candidate signed model is wired through the PDF extraction path
and accepted by an independent reviewer.
