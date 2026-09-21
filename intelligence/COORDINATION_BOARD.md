# COORDINATION BOARD

Integrator-owned compact view of unresolved cross-hunter signals.

This board is intentionally **not** a second search queue and not a finding archive. It contains only cross-lane items that can change another hunter's next action. Source evidence lives in immutable packets under `intelligence/coordination_spool/` and the referenced hunter/referral records.

## Current state

- Coordination protocol introduced: 2026-09-21.
- No historical findings were retroactively converted into signals.
- Existing `SEARCH_QUEUE.md`, capability/experiment state, leases and domain STOP gates remain authoritative.
- Hunt 15 should add only newly emitted, evidence-linked unresolved signals after its frozen benchmark scoring duty.

## Open signals

_None yet from the new immutable coordination channel._

## Closed / superseded signals

_None yet._

## Board rules

- Keep unresolved entries short: signal ID, source packet/run, subject, target lane, exact question/failure obligation, priority and evidence refs.
- A signal closes only with concrete evidence or a current central state transition.
- Do not turn another hunter's score or claim into fact.
- Do not copy sensitive/private/confidential material into this board.
