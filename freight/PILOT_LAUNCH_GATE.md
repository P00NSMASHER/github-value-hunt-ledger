# Freight Recovery — Pilot Launch Gate

Updated: 2026-09-20

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

The current Netlify project is therefore a **protected demo/control shell**, not
an approved confidential-customer-data plane.

### Separate controlled environment
**MANUAL/CONTROLLED PILOT: CONDITIONAL**

The separate route no longer accepts a caller-supplied `verified=True` flag.

It now requires a structured environment evidence manifest governed by:
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json`
- `freight/separate_environment_evidence.py`
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE.md`

The repository currently contains only a DRAFT template, so the route remains
CONDITIONAL.

Only a VERIFIED manifest with all applicable evidence references may unlock the
controlled manual pilot route.

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
  --expect BLOCKED
```

Separate controlled environment using the current DRAFT template:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path separate \
  --separate-evidence-json freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json \
  --expect CONDITIONAL
```

Those expectations should change only when new evidence is actually collected
and committed.
