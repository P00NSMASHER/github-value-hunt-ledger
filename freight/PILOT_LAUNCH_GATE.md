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
**MANUAL/CONTROLLED PILOT ENVIRONMENT: VERIFIED**

A dedicated single-tenant Google Drive workspace was staged on 2026-09-21 and
is now backed by a VERIFIED evidence manifest:

- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_2026-09-21.json`
- evidence root: `freight/evidence/separate_environment_2026-09-21/`
- valid through: **2026-12-20**, unless a material configuration change requires earlier reverification.

The evidence pack proves the currently used manual route's applicable base
controls: MFA enforcement, provider encryption at rest and in transit, owner-only
access scope, read-only source ingestion, retention/deletion policy, and explicit
exclusion of confidential buyer data from the public/Netlify shell. The route is
single-tenant and uses no production parser runtime, so multi-tenant isolation
and parser-sandbox controls are not applicable to this route.

Environment verification does **not** by itself authorize a customer's data.
Before any buyer records are accepted, the buyer/data readiness assessment must
be READY, the commercial-use rights gate must be clear, scope/retention must be
agreed, and the engagement/charter must authorize kickoff.

With those buyer-specific conditions satisfied, the machine launch route is
`CONTROLLED_MANUAL_BLIND_PILOT` / **READY**.

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

Separate controlled environment using the verified evidence manifest:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path separate \
  --separate-evidence-json freight/SEPARATE_ENVIRONMENT_EVIDENCE_2026-09-21.json \
  --as-of-date 2026-09-23 \
  --expect READY
```

READY applies to the controlled manual data path only and still requires a
buyer-specific READY assessment plus an authorized engagement before records move.
