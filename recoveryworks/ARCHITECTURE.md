# RecoveryWorks architecture

## RecoveryOS shared layers

1. **Ingestion** — branch-specific adapters normalize source data while original source hashes remain addressable.
2. **Authority** — effective-dated governing rules carry source hashes and explicit verification status.
3. **Calculation** — deterministic expected-vs-actual arithmetic; LLM output is never accepted as money math.
4. **Evidence** — every load-bearing source has a locator, content hash, type, and verification state.
5. **Recovery Ledger** — proof-deduped case lifecycle, review, authorization, claim, recovery, and fee fields.
6. **Human control** — validated dollars are not permission to act; claims require reviewer approval and customer authorization.
7. **Outcome learning** — realized recoveries, false positives, reviewer hours, and branch economics should feed the existing technology-intelligence outcome system only when supported by external evidence.

## Branch boundary

A branch owns domain-specific parsing and expected-amount logic. RecoveryOS owns
the invariants after normalization. This prevents six products from drifting into
six incompatible concepts of evidence, money, approval, and recovery status.

## Security boundary

- Payer data is sensitive and must remain inside an appropriately controlled environment.
- Source files are referenced by hash/locator; never silently replace historical rule versions.
- Unknown or conflicting authority stays REVIEW.
- No accidental credential/private-data discovery is a valid authority source.
- No external claim/dispute/contact action occurs without explicit authorization.

## Commercial surface

The universal client-facing output is the Recovery Ledger:

- potential recovery
- validated recovery
- authorized/claimed recovery
- recovered cash
- branch
- counterparty
- transaction reference
- rule/version provenance
- evidence packet readiness
- fee eligibility and realized fee

This supports one-time historical audits and continuous monitoring without changing the evidence model.

## Fulfillment boundary

Recovery packets are derived from immutable findings plus the current ledger
record. They do not create authority. They expose the rule/version and evidence
required to support a human-controlled recovery action.

The action gate is:

VALIDATED finding -> reviewer approval -> customer authorization -> AUTHORIZED

Only AUTHORIZED packets are submission-ready. Once a case moves to CLAIMED, the
packet records that state and is no longer represented as awaiting submission.

## Audit-chain boundary

Every ledger mutation appends a hash-linked event. The event includes the case,
transition, actor when applicable, timestamp, prior event hash, and transition
metadata. This provides tamper-evident lifecycle evidence without making the
event log itself permission to contact a counterparty.
