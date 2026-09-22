# HUNTER RESTART READINESS

Repository-side readiness for a future adaptive-learning hunter canary. **This report never activates work or changes scheduled tasks.**

- State: **BLOCKED**
- Explicit user approval required: **yes**
- Precommitted measurement packets: **3**
- Frozen benchmark matched: **47/50**
- Unmatched benchmark tasks: **06, 07, 08**
- Shadow runs: **55** (required 15)
- Split key commitment active: **true**
- Split secret available to workflow: **true**
- Pending split claims: **0**
- Current generated activations: **0**

## Machine gates

| Gate | State |
|---|---|
| measurement_packets_ready | PASS |
| split_receipt_system_ready | PASS |
| benchmark_complete | BLOCKED |
| shadow_run_gate_complete | PASS |
| no_current_activations | PASS |

## Blockers

- **frozen_benchmark_incomplete** — Finish the remaining frozen benchmark experiment conditions in clean contexts before using adaptive measurement packets.

## Canary contract after explicit approval

- At most three precommitted packet runs in the initial canary.
- Exactly one normal generated claim per packet.
- No manual completion, partition probing, release, substitution or retry to influence train/confirm.
- Require canonical ingestion and a secret-keyed split receipt before the run can affect learning.
- Rebuild learning state after each canonical run; do not infer success from packet execution alone.
