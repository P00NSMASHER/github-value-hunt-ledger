# Hunter Repair Workbench

Generated advisory queue for bounded hunter-system repair. **This file does not authorize automatic mutation or promotion.**

## Summary

- Tasks: **1**
- Ready for bounded repair: **1**
- Needs reproduction first: **0**
- Blocked source packets: **0**

## Active tasks

### REPAIR:416a843ab95507c6 — READY_FOR_REPAIR

- Priority: **100**
- Target: workflow / EXP-007 central-state-to-allocation reconciliation
- Source: failure_packet / FAIL:20260922T143415Z:HUNTER-13:stale-exp007-route
- Failure class: false_positive
- Observation: Allocator generated an EXP-007 verification assignment whose stated next actions are already contradicted/completed by canonical search_runs.jsonl evidence.
- Regression-test requirement: Generation must reject or supersede an assignment when canonical prior runs already satisfy or falsify its exact next-action fingerprint; EXP-007 should not reissue entry.scan_event repair after the LTQ-v66 repair run is canonical.
- Next action: Create one bounded candidate repair inside the logical target, add/run the stated regression test, freeze the diff hash and decision history, then submit to assess_repair_candidate. Do not change the live/global skill.
