# Freight Recovery — Pilot Activation Packet

Updated: 2026-09-20

The Pilot Activation Packet is the buyer-safe handoff artifact that sits above the existing readiness, launch-gate and launch-brief controls.

It does **not** authorize launch. It packages the already-authoritative decision into one practical handoff.

## What it contains

- readiness status and score;
- selected published offer;
- buyer-facing price band;
- launch status and route;
- prioritized launch-remediation actions;
- data-room requests split into NOW / CONDITIONAL / LATER_OUTCOME;
- buyer responsibilities;
- Freight Recovery responsibilities;
- blind-pilot stages;
- four separate report totals;
- core commercial integrity rules;
- deterministic SHA-256 activation hash.

## Buyer-safe commercial language

- Data Readiness / Authority Diagnostic: **$5,000–$7,500 fixed**.
- Blind Freight Audit Acceptance Test: **$15,000–$25,000 fixed**.
- Blind-test target analysis/report turnaround: **10–15 business days after complete inputs**.

The packet intentionally excludes internal analyst-cost, delivery-budget and target-margin assumptions.

## Data-room timing

**NOW** — needed to qualify or execute the selected offer.

**CONDITIONAL** — needed only where a supported rule requires the source.

**LATER_OUTCOME** — needed after findings/actions to prove settlement or recovery; it is not treated as immediate savings evidence.

## Integrity rule

The packet inherits launch remediation from `freight/launch_brief.py` and source semantics from `freight/pilot_package.py` / `PILOT_DATA_ROOM.md`.

Editing the packet cannot close a launch blocker. The underlying evidence must change and the machine launch gate must be rerun.