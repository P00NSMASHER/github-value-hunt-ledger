# Freight Recovery — Pilot Activation Packet

Updated: 2026-09-20

The Pilot Activation Packet is the buyer-safe handoff artifact that sits above the existing readiness, launch-gate and launch-brief controls.

It does **not** authorize launch. It packages the already-authoritative decision into one practical handoff.

## What it contains

- readiness status and score;
- selected audit route;
- buyer-facing commercial model;
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

- Data Readiness / Authority Diagnostic: **$0 upfront as part of the free audit**.
- Blind Freight Audit Acceptance Test: **$0 upfront when approved as the
  bounded opportunity-assessment scope**.
- Recovery execution: success-based pricing under a separately accepted
  engagement; the exact percentage is confirmed before recovery begins.
- Analysis/report timing is confirmed after complete inputs and capacity review.

The packet intentionally excludes internal analyst-cost, delivery-budget,
qualification thresholds, and target-margin assumptions. It does not authorize
the detailed recovery work or any external action.

## Data-room timing

**NOW** — needed to qualify or execute the selected offer.

**CONDITIONAL** — needed only where a supported rule requires the source.

**LATER_OUTCOME** — needed after findings/actions to prove settlement or recovery; it is not treated as immediate savings evidence.

## Integrity rule

The packet inherits launch remediation from `freight/launch_brief.py` and source semantics from `freight/pilot_package.py` / `PILOT_DATA_ROOM.md`.

Editing the packet cannot close a launch blocker. The underlying evidence must change and the machine launch gate must be rerun.

## Next layer — Pilot Charter

The Activation Packet is the buyer-safe handoff, but it does not freeze a
specific engagement.

`freight/pilot_charter.py` binds the activation hash to the exact engagement
scope, fee, date range, carriers/modes, buyer truth owner, buyer action approver
and operating acknowledgments.

A blocked/conditional launch may become **PRELAUNCH_ACCEPTED**, but only a
machine-READY launch can become **KICKOFF_AUTHORIZED**.

The charter never authorizes carrier/vendor contact or money-moving action.
