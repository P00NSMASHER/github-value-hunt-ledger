# HUNTER-03 R23 — EXP-003 external terminal-observation gate

Date: 2026-09-21

Status: **AWAITING EXTERNAL — no provider/bank experiment executed**

## Current acceptance target

The current EXP-003 packet no longer authorizes another synthetic matrix or broad repository search. The remaining test is one authorized real provider/bank or payroll adapter run in which the reversal/return webhook is deliberately suppressed and an independent terminal readback must discover the late counter-event.

The required outcome is:

- unknown provider result remains pending and cannot create a second send;
- independent terminal evidence, not provider success, establishes current settlement;
- a later still-owed return revokes prior finality and reopens the original immutable authority exactly once;
- re-payment uses the original plan/rate/amount rather than current policy; and
- a clawback-not-owed counter-event does not create another payable.

## External evidence that is missing

Execution requires all four items below. None is available in this runtime:

1. An authorized Stripe, payroll, or equivalent provider test/live account capable of producing a real payout and later return/failure.
2. A separate read-only bank or payroll terminal-observation source whose coverage and freshness can be established independently of the provider webhook.
3. A controlled way to suppress only the return/reversal webhook while preserving the real external event, plus evidence that suppression occurred.
4. A buyer- or test-owner-approved population in which payout, return, and bank/payroll references may be correlated without placing credentials or confidential records in the repository.

Public documentation, repository code, mocked callbacks, and another locally generated statement cannot establish these facts. Repeating those methods would violate the current STOP gate.

## Ready-to-execute evidence packet

The authorized operator should preserve the following redacted receipt fields. Secret keys, account numbers, employee identities, and raw bank statements must remain outside the repository.

### Frozen payout authority

- opaque entitlement/earning ID;
- immutable plan/version ID and calculation cutoff;
- original amount/currency/rate inputs;
- authority receipt hash;
- provider request/effect ID and idempotency key.

### Provider observation

- opaque provider payout ID;
- provider account/scope identifier;
- ordered status observations with source timestamps;
- provider trace/reference and its availability state;
- return/failure/reversal identifier and reason class;
- evidence that the return webhook was suppressed for this test.

### Independent terminal observation

- opaque bank/payroll account scope;
- source coverage start/end and freshness receipt;
- pagination/completeness and durable-commit receipt;
- terminal entry ID/reference, amount, currency, value date, direction and booking state;
- later return/reversal reference linked to the original terminal observation.

### Required assertions

1. Persist one logical payout effect before the provider call.
2. Simulate an ambiguous/lost initial response; verify retry cannot mint a new effect ID.
3. Establish settlement only after exactly one matching terminal observation inside verified source coverage.
4. Suppress the provider return webhook, then require terminal readback to detect the real late return.
5. Atomically revoke current finality and reopen the original earning once, preserving the prior settlement event.
6. Change current plan/rate before re-payment and verify the original frozen amount is still used.
7. Replay and race the return/readback path; verify no duplicate reopen or send.
8. Run a clawback-not-owed control; verify it does not reopen a payable.

The repository should receive only a redacted result receipt, hashes of external artifacts, exact adapter revisions, source-coverage evidence, assertion results, and failure reasons.

## Coordination result

The previous three HUNTER-03 EXP-003 runs are now present in canonical telemetry, including the Stripe-to-CAMT run `RUN:20260921T051328Z:HUNTER-03:aae035cb5f4e`.

A fresh generated activation for SLOT-02 was received and a provisional claim event was persisted. Canonical workflow run `35567378075` failed before reducer readback because an unrelated SLOT-05 event log already contained a duplicate active claim. Canonical SLOT-02 state therefore remained `AVAILABLE` with `event_count=0`; no lease was treated as accepted and no START or COMPLETE was emitted. A matching RELEASE was appended so a later successful reducer cannot create a ghost lease.

## Handoff

- **Experiment state:** EXP-003 remains READY/awaiting external execution, not complete.
- **Capability state:** no capability promotion or settlement claim occurred.
- **Commercial implication:** the remaining test is the one that converts a strong synthetic contract into credible real-world payout assurance; substituting another mock would overstate readiness.
- **Next action:** supply an authorized provider plus independent bank/payroll sandbox or controlled live test population, then execute the eight assertions above without placing secrets or customer data in GitHub.
