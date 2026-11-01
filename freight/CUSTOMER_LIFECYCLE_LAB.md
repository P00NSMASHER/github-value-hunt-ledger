# Freight Recovery: Customer Lifecycle Simulation Lab

Status: **portable simulation plus draft real-code bridge; no production integration or customer claims.**

This is a **separate laboratory** from the synthetic invoice/financial benchmark in
draft PR #263. The portable customer laboratory is delivered in the conversation
as a downloadable archive, not checked in here as a giant 1M-row data blob.

## What it does

- Reuses the previously generated 1M fictional six-mode freight-invoice rows and frozen
  reference labels. Customer relationships are linked to invoices, **not** presented
  as actual customers or as independently measured RecoveryOS accuracy.
- Generates 10,000 stable fictional customer profiles and 1M complete simulated
  customer lifecycles with multi-year follow-ups, complaints and claim disputes.
- Produces streaming shard files: event history with per-scenario SHA-256 chain,
  communication threads, balanced revenue/receipt postings and case summaries.
- Replays money and authorization prerequisites through an **independently coded**
  validator. In-memory mutation campaigns are controls testing the simulator,
  not security defects verified in production RecoveryOS.
- Includes local-only customer ID lookup, a standalone executive HTML dashboard,
  a scenario coverage report, operations/communications playbooks and fictional PDFs.
- Report labels separate confirmed synthetic generation, actual repository tests,
  simulated operations, hypothetical financial forecasts, and not-tested areas.

## The actual RecoveryOS bridge in this pull request

`freight/customer_lifecycle_product_probe.py` invokes the EXISTING production-domain
Python module `freight.payment_orchestration`: provider-neutral instruction,
separate human authorization, valid provider transitions and settlement/reversal
snapshots. It wraps only **fictional** case IDs and evidence hashes. No network,
carrier contact, email, database write or live payment is attempted.

Crucial invariant: even a provider-observed `SETTLED` state cannot produce a
customer-reconciled amount or a contingency fee until a **separate simulated
customer receipt reconciliation** flag is present. `REVERSED` forces fee
eligibility back to zero. Unsigned engagements, revoked authorization, missing
proof or no independently validated positive amount remain blocked.

Run the 13 regression checks with:

```bash
python -m unittest -v freight.test_customer_lifecycle_product_probe
```

These pass against exact source head
`ddef7c9731270150f8b2a9b280abacbd8648f07d` in a separate project
execution environment. They are not a production deployment or an authenticated
Floot app HTTP test.

## Major known gaps

1. No real customer CRM, outbound-email, consent, cancellation or enterprise
   contract integration has been demonstrated in the deployed app.
2. No actual carrier API or external bank/payment reconciliation evidence.
3. Actual RecoveryOS OCR/model accuracy still needs a representative blind
   independently adjudicated customer corpus under privacy agreements.
4. Draft import-boundary economic-key guards in Floot development remain
   unpublished; database-wide concurrency/unique-key guarantees are not proved.
5. Customer satisfaction, lead conversion, recovery probability and margins
   are **fully simulated**, not estimates from actual operations.
6. Mathematical tariff ground truth comes from the existing synthetic invoice
   fixture, not verified historical carrier contracts.

## Safety and governance

- No real customer/account/lead records in this public repository.
- No production changes, customer emails, payments or carrier submissions.
- The portable archive is a generator and test harness, not authorization to
  impersonate customers or certify commercial product quality.
- Manual human review is required before any future customer-facing claim.

Use the portable archive's `README.md`, `data/full_million/manifest.json`,
`verification.json`, and `reports/RELEASE_EVIDENCE.json` for exact execution
receipts when the full data gate has completed.
