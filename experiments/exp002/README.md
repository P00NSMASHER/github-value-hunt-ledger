# EXP-002 reversible-authority fixture

This is a rights-clean, ERP-neutral falsification fixture for EXP-002. It is not an ERP adapter and does not claim live-provider validation.

The fixture uses integer quantity atoms and integer currency minor units, an append-only bitemporal event ledger, line-specific forward and reverse capacity, reviewed identity decisions, durable semantic effect identity, payload binding, dispatch fencing and a separate synthetic target.

Run:

```bash
python -m unittest -v experiments.exp002.test_authority_ledger
```

The planted matrix covers source outage versus verified emptiness, receipt-policy differences, alias/non-match/merge/split identity, same-SKU ambiguity, partial receipts, direct and service authority, rejected quantity, exact precision, non-refunding and refunding returns, vendor credits, bill cancellation, re-receipt, concurrent reverse-capacity reservation, synchronous receipts, process death after target commit, authoritative APPLIED/NOT_APPLIED/UNKNOWN, phase-qualified provider outcome receipts, bounded replay expiry, payload conflict, zombie-worker fencing and bitemporal correction replay.

`SyntheticTarget.probe()` intentionally returns `UNKNOWN` for mere absence. Only a separately recorded authoritative negative receipt can return `NOT_APPLIED` and release the held reverse reservation.

`ProviderOutcomeReceipt` makes provider identity, processing phase, effect scope, terminality, partial-effect risk and economic-fingerprint agreement explicit. The Dynamics recurring-integration adapter admits only an exact single-effect `PreProcessingError` as `NOT_APPLIED`; `ProcessedWithErrors`, `PostProcessingFailed`, generic `Failed`, ambiguous `Canceled`, mismatched identity and batch-scoped receipts remain `UNKNOWN`. A `Processed` status becomes `APPLIED` only when the exact economic fingerprint also matches.
