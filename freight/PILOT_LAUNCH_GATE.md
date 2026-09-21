# Freight Recovery — Pilot Launch Gate

Updated: 2026-09-21

This is the **final go/no-go gate** before confidential buyer data is handled for
a paid blind Freight Audit Acceptance Test.

It deliberately separates three different questions:

1. **Is the buyer/data set audit-ready?** — `freight/readiness.py`
2. **Is the product legally/operationally usable for a controlled pilot?** —
   component rights + rights evidence gates
3. **Is the chosen data-handling environment safe enough for the way this pilot
   will actually run?** — `freight/pilot_launch_gate.py`

A READY Data Readiness score can never override deployment-security blockers.

## Current classification

### Current Netlify deployment
**DEPLOYED CUSTOMER-DATA PILOT: BLOCKED**

Reasons:
- Netlify team MFA is not enforced.
- No Freight customer data plane has been discovered.
- If multi-tenant storage/API is later used, tenant isolation is still unproven.
- If a production parser is later used, parser sandboxing is still unproven.
- The collected Netlify snapshot is time-bounded through **2026-09-27** and must
  be recollected earlier after relevant access/deployment changes.

The current Netlify project is therefore a **protected demo/control shell**, not
an approved confidential-customer-data plane.

### Separate controlled environment
**MANUAL/CONTROLLED PILOT: CONDITIONAL — ONE BASE CONTROL REMAINS**

A dedicated single-tenant Google Drive workspace was staged on 2026-09-21 and
confirmed owner-only / not shared. It contains no customer data and is explicitly
separate from the Netlify shell. The current evidence manifest is:

- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_2026-09-21.json`
- evidence root: `freight/evidence/separate_environment_2026-09-21/`

The evidence pack records:
- single-tenant workspace scope;
- Google Drive provider encryption at rest and in transit;
- owner-only access snapshot;
- manual/no-parser operating route;
- immutable-source/read-only-ingestion policy;
- retention and deletion policy;
- explicit exclusion of buyer data from Netlify;
- a redacted Google security alert showing a passkey was added.

The only unproven base control is **current MFA enforcement on every permitted
sign-in path**. A passkey exists, but that alone does not prove that Google
2-Step Verification is enabled/enforced for all account access. Therefore the
manifest remains `DRAFT` and the route remains **CONDITIONAL**.

Only current account-security evidence proving the MFA requirement may promote
the manifest to `VERIFIED`. No confidential buyer data may enter this workspace
before that promotion.

The separate route no longer accepts a caller-supplied `verified=True` flag.
It requires a structured environment evidence manifest governed by:
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json`
- `freight/separate_environment_evidence.py`
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE.md`

VERIFIED means:
- evidence references have matching lowercase SHA-256 receipts;
- the environment has a configuration fingerprint;
- verifier role + verification date are recorded;
- the validity window is no more than 90 days;
- the evidence has not expired at launch time;
- every required base control is proven.

The separate route is deliberately independent of the current Netlify snapshot:
an expired Netlify observation blocks the Netlify route, not an independently
verified separate environment.

## Why this improves commercialization

This avoids three bad states:

- **Unsafe SaaS shortcut:** buyer READY, deployment unsafe.
- **Unnecessary sales freeze:** waiting for a full multi-tenant SaaS before a
  supervised service pilot can exist.
- **Self-attested manual exception:** an operator simply marks a separate
  environment "verified" without evidence.

The intended sequence is:

1. qualify the buyer;
2. choose the actual data path;
3. collect the environment evidence for that path;
4. pass the launch gate;
5. only then accept confidential data.

## Current CI expectations

Current Netlify customer-data route:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path current \
  --as-of-date 2026-09-21 \
  --expect BLOCKED
```

Separate controlled environment using the staged evidence manifest:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path separate \
  --separate-evidence-json freight/SEPARATE_ENVIRONMENT_EVIDENCE_2026-09-21.json \
  --as-of-date 2026-09-21 \
  --expect CONDITIONAL
```

The expectation may change to READY only after current MFA enforcement evidence
is collected, hashed, committed, and the manifest is promoted to VERIFIED.
