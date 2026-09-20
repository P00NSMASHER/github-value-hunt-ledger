# Freight Recovery — Separate Controlled Environment Evidence

Updated: 2026-09-20

This control supports a **service-led/manual pilot** without pretending the
current Netlify shell is a customer-data plane.

The separate environment route is intentionally fail-closed. It cannot become
READY from an operator checkbox or boolean.

## Canonical files

- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json`
- `freight/separate_environment_evidence.py`
- `freight/pilot_launch_gate.py`

## Base controls required for VERIFIED status

Every separate environment must prove, with evidence references:

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
- a diligence-room evidence root reference;
- an identified provider/host.

## Conditional controls

### If the environment is multi-tenant
Cross-tenant isolation must be `PROVEN` with an evidence reference.

### If a parser runtime is used
Parser sandboxing must be `PROVEN` with references for:

- CPU limit;
- memory limit;
- execution timeout;
- network isolation;
- credential isolation.

## Status semantics

### DRAFT
Structurally valid planning record. The launch gate remains **CONDITIONAL**.

### VERIFIED
All applicable controls and evidence references are present. Only then may the
separate/manual route become **READY**.

## Current state

The repository contains only the DRAFT template. Therefore the separate
controlled environment route remains **CONDITIONAL**.

Do not place secrets, raw buyer contracts, invoices, credentials, or other
confidential customer payloads in this manifest.
