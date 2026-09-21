# HUNTER-09 referral — endpoint boundary gate for provider receipts

## Recipients

AP / finance, money-state, source-authority and MASTER integration lanes.

## Required correction

Do not let provider-wide phase/status semantics authorize a financial state transition until those semantics are bound to the exact economic endpoint.

Add a reviewed endpoint contract with:

- provider + exact interface;
- economic action;
- financial posting boundary;
- credit-note/reversal capability;
- operation-identity binding;
- phase-to-posting-boundary proof.

Only then may an exact terminal singleton pre-apply rejection classify as `NOT_APPLIED`. Without this binding, even `PreProcessingError` remains `UNKNOWN`.

## Dynamics negative control

Current first-party sources separately document public vendor-invoice header/line entities, vendor-credit-note business workflows, and recurring-integration phase statuses. They do not publicly bind the invoice entities to vendor-credit creation/posting or prove where recurring preprocessing sits relative to that financial boundary.

Treat Dynamics as **phase semantics verified / AP-credit endpoint binding unverified** until an authorized sandbox or endpoint-specific provider contract closes the gap.

## Evidence

- `hunters/16-run26-2026-09-21.md`
- `experiments/exp002/authority_ledger.py`
- `experiments/exp002/test_authority_ledger.py`
- MicrosoftDocs revision `b81257fa8c6f2e0599f477653b740f4565649276`

