# Freight Recovery — Pilot Launch Brief

Updated: 2026-09-20

The machine Pilot Launch Gate answers whether a route may launch.

The Pilot Launch Brief answers the operator/buyer question:

> What exactly has to happen next?

## Workflow

1. Run `freight/pilot_launch_gate.py` and save its JSON output.
2. Run `freight/launch_brief.py` on that JSON.
3. Close actions by changing the underlying evidence source.
4. Rerun the launch gate; never close an item by editing the brief itself.

Example:

```bash
PYTHONPATH=. python freight/pilot_launch_gate.py \
  freight/fixtures/readiness_ready.json \
  --data-path current \
  --as-of-date 2026-09-20 > /tmp/launch-decision.json

PYTHONPATH=. python freight/launch_brief.py /tmp/launch-decision.json
```

Use `--format json` for machine-readable output.

## Brief contents

Each blocker/condition becomes a deterministic remediation action with:

- priority: P0 / P1 / P2;
- owner;
- category;
- launch-gate code;
- plain-language remediation title;
- exact evidence required to close it;
- what closure unlocks.

Unknown future blocker codes are never dropped. They become an explicit
`UNMAPPED_REVIEW` action until the product maps them deliberately.

## Current product use

For the current Netlify route, the brief should surface items such as:

- enforce Netlify team MFA;
- identify the customer data plane;
- if multi-tenant use is requested, prove A-vs-B isolation;
- if parser use is requested, prove parser resource/network/credential isolation;
- recollect deployment evidence when it expires.

For the separate/manual route, the brief requests the structured
separate-environment evidence manifest instead of accepting a human override.

## Integrity rule

The Launch Brief cannot override the launch decision.

An item is closed only when the underlying evidence changes and the machine gate
is rerun.