# Freight Recovery — Separate Controlled Environment Evidence

Updated: 2026-09-21

This control supports a **service-led/manual pilot** without pretending the
current Netlify shell is a customer-data plane.

The separate environment route is intentionally fail-closed. It cannot become
READY from an operator checkbox or boolean.

## Canonical files

- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json`
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_2026-09-21.json`
- `freight/evidence/separate_environment_2026-09-21/`
- `freight/separate_environment_evidence.py`
- `freight/pilot_launch_gate.py`

## Base controls required for VERIFIED status

Every separate environment must prove, with an evidence reference **and
lowercase SHA-256 receipt** for each applicable control:

- MFA enforced;
- encryption at rest;
- encryption in transit;
- access scope defined;
- read-only source ingestion;
- retention defined;
- deletion defined;
- buyer data excluded from the current Netlify `freightleak-audit` shell.

The environment must also have:

- a unique environment ID;
- a diligence-room evidence root reference + SHA-256;
- a configuration-snapshot SHA-256;
- an identified provider/host;
- a verifier role;
- `verified_at` and `valid_until` ISO dates.

A verification window longer than **90 days** stays CONDITIONAL. Expired
evidence stays CONDITIONAL and must be recollected/reverified.

## Conditional controls

### If the environment is multi-tenant
Cross-tenant isolation must be `PROVEN` with an evidence reference + SHA-256.

### If a parser runtime is used
Parser sandboxing must be `PROVEN` with evidence reference + SHA-256 pairs for:

- CPU limit;
- memory limit;
- execution timeout;
- network isolation;
- credential isolation.

## Status semantics

### DRAFT
Structurally valid evidence record with one or more unproven controls. The launch
gate remains **CONDITIONAL**.

### VERIFIED
All applicable controls have evidence references + SHA-256 receipts, the
configuration snapshot is fingerprinted, verifier metadata is present, and the
evidence is still inside its validity window. Only then may the separate/manual
route become **READY**.

## Current state — 2026-09-21

A dedicated single-tenant Google Drive workspace now exists and was observed as
owner-only / not shared, with no customer data present. The evidence pack records
provider encryption, access scope, manual/no-parser operation, immutable-source
handling, retention/deletion rules, and Netlify exclusion.

A Google security alert provides evidence that a passkey was added on
2026-09-17. That is useful authentication evidence, but it does **not** establish
that 2-Step Verification is currently enabled/enforced for every permitted
account sign-in path.

Therefore:
- all base controls except `mfa_enforced` are currently evidenced;
- `mfa_enforced` remains unproven;
- the current manifest remains `DRAFT`;
- the route remains **CONDITIONAL**;
- no confidential customer data may be accepted yet.

The final promotion step is to obtain current account-security evidence that
proves the required MFA posture, hash and record that evidence, set
`mfa_enforced.value=true`, and change `evidence_status` to `VERIFIED`.
The gate should then be re-run and must return READY before use.

Do not place secrets, raw buyer contracts, invoices, credentials, or other
confidential customer payloads in the evidence manifest or Hunter repository.
