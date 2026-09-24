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

## Current state — verified controlled route

The staged Google Drive environment is now **VERIFIED** for the single-tenant,
manual/no-parser controlled-pilot route.

Current evidence establishes:
- Google 2-Step Verification/MFA for the observed pilot account;
- provider encryption at rest and in transit;
- owner-only access scope at verification time;
- read-only source-ingestion policy;
- 30-day default retention plus explicit deletion confirmation;
- no confidential buyer data in the public/Netlify marketing path;
- no multi-tenant data plane and no production parser runtime for this route.

The canonical manifest is
`freight/SEPARATE_ENVIRONMENT_EVIDENCE_2026-09-21.json`, with a current
verification window through **2026-12-20**. Reverify earlier after a material
configuration or access change.

This means the environment-control portion of the manual route is no longer the
launch blocker. Buyer-specific readiness, scope, retention, rights, and engagement
authorization still have to pass before confidential records are accepted.

Do not place secrets, raw buyer contracts, invoices, credentials, or other
confidential customer payloads in the evidence manifest or Hunter repository.
