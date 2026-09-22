# HUNTER-13 — EXP-007 stale-assignment preflight — 2026-09-22

## Claimed assignment
- Worker: HUNTER-13
- Slot: SLOT-13
- Assignment: ASSIGN:da63048c7581:slot-13
- Claim: CLAIM:be6863fbb5e1
- Activation: ACTIVATE:fe72e6d715b5
- Purpose: independent verification / execute_fixture for EXP-007.

## Preflight result
The current generated assignment is stale relative to canonical evidence already present in the repository.

### Thermo branch
The current HUNT_PLAN asks to patch OpenTFRaw metadata lookup from scan ordinal `idx` to `entry.scan_event` and replay the frozen fixture. That exact hypothesis has already been prospectively tested and falsified in canonical run:
- `RUN:20260921T040405Z:hunter13:exp007-opentfraw-ltq-repair-replay`
- Durable evidence: `referrals/hunt13-r25-2026-09-21-exp007-opentfraw-ltq-repair-replay.md`

That run found the `entry.scan_event` change was not the repair. The actual defect was LTQ v66 variable-size scan-event parsing; a guarded local repair using 176-byte primary / 232-byte dependent event sizes plus corrected observed-range emission restored the tested scalar semantics while preserving all 9,942,753 peak values exactly.

The current pinned OpenTFRaw revision `63380dff0d25898f5c6e1184087dc590b0d7b6ab` still contains ordinal `scan_events.get(idx)` paths, but repeating the already-falsified one-line repair would duplicate prior work and violate the duplicate-preflight rule.

### Physical-action branch
The current HUNT_PLAN also asks to run the SiLA/Opentrons kill/restart matrix. Two canonical runs already cover the relevant Robot Server ambiguity path:
- `RUN:20260921T052933Z:hunter13:exp007-opentrons-kill-recovery`
- `RUN:20260921T060826Z:HUNTER-13:opentrons-absent-action-race`

The first showed accepted play can be recovered by read-only provider query after client receipt loss without redispatch. The second falsified the claim that an absent action record proves execution never began: the provider was killed while a command was running before action persistence, then restarted with the run readable and action count still zero. Classification remained RECONCILIATION_REQUIRED. Neither run proves physical robot motion; device-in-the-loop evidence remains external.

## Authoritative-state inconsistency
`intelligence/search_runs.jsonl` contains all three runs above, but `EXPERIMENTS.md`, `SEARCH_QUEUE.md`, and the current generated HUNT_PLAN still repeat the pre-repair EXP-007 next action.

This is a coordination/state-reconciliation defect, not a reason to rerun completed work.

## Disposition
- Current assignment acceptance test: NOT RE-EXECUTED due exact prior canonical evidence.
- Result: STALE_ASSIGNMENT / DUPLICATE_AVOIDED.
- No claim is made that physical-action proof is complete.
- Next integrator action: reconcile EXP-007 central state from canonical runs, replace the falsified `entry.scan_event` repair instruction, and route the remaining external/device-level ambiguity question rather than the completed simulator work.
