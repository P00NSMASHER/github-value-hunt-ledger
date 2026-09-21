# HUNTER-03 R22 — EXP-003 Stripe payout to CAMT observation adapter fixture

Date: 2026-09-21

Status: **format-level synthetic adapter executed; provider/bank mapping remains external**

## Question

Can the concrete shape `Stripe payout -> provider trace/reference -> independent CAMT.053 entry` obey EXP-003's exact-unique, source-authoritative settlement rule without turning Stripe `paid`, a nullable/pending trace, aggregate equality, or an ambiguous bank match into money finality?

## External implementation evidence

- Stripe's current payout-list documentation exposes payout ID, amount, arrival date, currency, status, `reconciliation_status`, and `reversed_by`, and lists the payout states `pending`, `paid`, `failed`, and `canceled`: https://docs.stripe.com/api/payouts/list
- Stripe's first-party payout documentation explicitly warns that a payout may initially show `paid` and then change to `failed` within five business days: https://docs.stripe.com/payouts#payout-failures
- The Stripe OpenAPI fixture at exact revision `7ec24599c27c862a0a27fd2c890b564edbd5f8d7` includes a payout `trace_id` object with separate `status` and nullable `value`, beside `original_payout`, `reconciliation_status`, `reversed_by`, and payout `status`: https://github.com/stripe/openapi/blob/7ec24599c27c862a0a27fd2c890b564edbd5f8d7/openapi/fixtures3.yaml
- `sebastienrousseau/reconcile-mcp` at exact revision `d5e81b593060f6a99b03b28efb253262d2b0eb0b` converts CAMT.053 `acct_svcr_ref`/`ntry_ref` into the canonical observed record ID rather than dropping it: https://github.com/sebastienrousseau/reconcile-mcp/blob/d5e81b593060f6a99b03b28efb253262d2b0eb0b/reconcile_mcp/adapters.py

These sources establish that the relevant fields exist and that a real implementation preserves CAMT statement references. They do **not** establish that every Stripe trace value appears unchanged as the buyer bank's `AcctSvcrRef`; that remains a provider/bank/rail-specific mapping hypothesis.

## Executed fixture

`referrals/hunt03-r22-2026-09-21-exp003-stripe-camt-adapter-fixture.py` parses synthetic CAMT XML and requires all of the following before returning `SETTLED_BANK_OBSERVED`:

1. current provider state is `paid` with no `reversed_by` counter-event;
2. the normalized provider trace state is `AVAILABLE` and its value is non-empty;
3. the independent statement coverage receipt is current, scope-complete, fully paginated, durably committed, and includes the payout destination account;
4. exactly one booked bank credit matches the full trace value, amount, currency, destination account, and bounded value-date contract.

Observed result: **20/20 cases passed**, including one valid exact-unique observation and negatives for provider pending, trace pending/unsupported, no bank entry, wrong or substring reference, wrong money/account/date/direction/status, duplicate exact matches, stale/partial/incomplete bank coverage, provider failure/reversal, and aggregate-equal wrong identity.

Four unsafe evaluators were detected: provider-`paid` as finality, substring reference matching, trace-only first-match selection, and amount/currency-only matching.

The lifecycle test first records an independently observed settlement, then applies a later provider `failed` state. Current finality is revoked while the earlier observation remains a separate historical result.

Deterministic result digest: `f5dbbb3c59f1ec7cb51463d54ce7604b8b14d44618e801a7fbee7e7bd325aa3d`.

## Material result

The format bridge is implementable, but the trace field is only a **candidate join key**. `paid` is not final; a trace value without source-complete bank readback is not final; and an exact trace collision is ambiguous unless the remaining economic/account/date constraints make the observation unique.

The fixture deliberately fails closed when the trace is pending or unsupported. It does not fall back to amount/date heuristics, because aggregate equality can preserve total cash while swapping payout identity.

## Claims and limits

**Source-inspected:** Stripe first-party payout documentation, Stripe OpenAPI fixture at an exact revision, and CAMT adapter implementation at an exact revision.

**Locally tested:** 20 deterministic provider/CAMT/source-coverage cases, four unsafe mutants, and a late provider-failure transition.

**Not verified:** live Stripe API/webhook behavior, a real Stripe trace value appearing in any bank's CAMT statement, live bank-source freshness/completeness, ACH-return lineage, customer-authorized data, or realized commission recovery. The local `AVAILABLE`/`PENDING` normalization is an adapter contract, not a claim about Stripe's literal enum values.

## Handoff

- **Capability delta:** CAP-018 now has an executable concrete provider-to-CAMT acceptance corpus instead of only a provider-neutral finality rule.
- **Graph edge:** strengthens `Stripe payout identity -> CAMT observed reference -> CAP-018 -> EXP-003`, subject to a still-unproven bank-specific mapping contract and CAP-019 coverage receipt.
- **Experiment impact:** closes the synthetic field-level join prerequisite but not the real provider/bank sandbox gate.
- **Commercial impact:** blocks commissions from being released on provider `paid`, ambiguous statement identity, or incomplete bank observation.
- **Negative knowledge:** trace presence is not proof that the buyer bank exposes the same value, and aggregate-equal statement matching is not payout identity.

## Coordination and next gate

This was executed as unallocated work because no valid activation/claim was available; no generated assignment provenance is asserted.

Next: obtain one authorized Stripe test/live payout plus its destination bank's machine-readable statement and verify the literal mapping from `payout.id` and provider trace metadata to the bank entry reference. Re-run the same negatives against the real adapter, including a later failed/returned payout, before promoting any state to settlement authority.
