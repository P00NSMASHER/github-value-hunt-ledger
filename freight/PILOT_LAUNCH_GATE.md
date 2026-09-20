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

With the deployment evidence collected on 2026-09-20:

### Current Netlify deployment
**DEPLOYED CUSTOMER-DATA PILOT: BLOCKED**

Reasons:
- Netlify team MFA is not enforced.
- No Freight customer data plane has been discovered.
- If multi-tenant storage/API is later used, tenant isolation is still unproven.
- If a production parser is later used, parser sandboxing is still unproven.

The current Netlify project should therefore be treated as a **protected
demo/control shell**, not as an approved confidential-customer-data plane.

### Separate controlled environment
**MANUAL/CONTROLLED PILOT: CONDITIONAL**

A service-led pilot may proceed outside the current Netlify customer-data path
only after a separate data-handling environment has:
- its own control evidence;
- an evidence reference in the diligence room; and
- explicit verification that those controls are active.

Until then the route remains CONDITIONAL, not READY.

## Why this improves commercialization

This avoids two bad extremes:

- **Unsafe SaaS shortcut:** putting buyer contracts/invoices into a deployment
  merely because the buyer itself is READY.
- **Unnecessary sales freeze:** pretending Freight must become a full
  multi-tenant SaaS before a supervised service pilot can ever be sold.

The intended sequence is:

1. qualify the buyer;
2. choose the actual data path;
3. pass the launch gate for that path;
4. only then accept confidential data.

## Current CI expectations

The repository intentionally asserts:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path current \
  --expect BLOCKED
```

and:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path separate \
  --expect CONDITIONAL
```

Those expectations should change only when new deployment/environment evidence
is actually collected and committed.
