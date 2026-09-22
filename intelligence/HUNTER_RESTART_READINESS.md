# HUNTER RESTART READINESS

Repository-side readiness for a future adaptive-learning hunter canary. **This report never activates work or changes scheduled tasks.**

- State: **BLOCKED**
- Explicit user approval required: **yes**
- Precommitted measurement packets: **3**
- Frozen benchmark matched: **47/50**
- Shadow runs: **55** (required 15)
- Split key commitment active: **false**
- Split secret available to workflow: **false**
- Pending split claims: **2**
- Current generated activations: **0**

## Machine gates

| Gate | State |
|---|---|
| measurement_packets_ready | PASS |
| split_receipt_system_ready | BLOCKED |
| benchmark_complete | BLOCKED |
| shadow_run_gate_complete | PASS |
| no_current_activations | PASS |

## Blockers

- **split_key_commitment_inactive** — Configure the GitHub Actions repository secret TI_TRAINING_SPLIT_KEY, then rerun Technology Intelligence so the public commitment is generated.
- **split_secret_unavailable** — Make TI_TRAINING_SPLIT_KEY available to the Technology Intelligence workflow; never put its value in repository files, prompts, logs, or worker-visible state.
- **split_receipt_debt** — After the split key is configured, regenerate receipts and require the split-status validator to clear all pending generated claims before canary activation.
- **frozen_benchmark_incomplete** — Finish the remaining frozen benchmark experiment conditions in clean contexts before using adaptive measurement packets.

## Canary contract after explicit approval

- At most three precommitted packet runs in the initial canary.
- Exactly one normal generated claim per packet.
- No manual completion, partition probing, release, substitution or retry to influence train/confirm.
- Require canonical ingestion and a secret-keyed split receipt before the run can affect learning.
- Rebuild learning state after each canonical run; do not infer success from packet execution alone.
