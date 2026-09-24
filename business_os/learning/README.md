# Upgrade 3 — Verifier-Gated Self-Improvement

Status: **IMPLEMENTED**

Agents are allowed to learn and propose new shared skills, but the agent that proposes a change is not allowed to declare the change good enough for global use.

## Promotion path

```
candidate skill
   ↓
confirm evaluation
   ↓
held-out evaluation
   ↓
adversarial evaluation
   ↓
READY_FOR_CANARY
   ↓
canary evaluation
   ↓
GLOBAL_ELIGIBLE
   ↓
explicit INTEGRATOR approval
   ↓
GLOBAL
```

## Fail-closed rules

A candidate is rejected when:
- a required evaluation split is missing;
- confirm/held-out/adversarial datasets are not independent;
- the proposer verifies its own candidate;
- a verifier marks a split failed;
- any hard regression is present;
- measured improvement is below the configured threshold;
- canary evidence is ambiguous or fails.

`GLOBAL_ELIGIBLE` never writes the registry by itself.

## Hunter sources

This implements the promotion contract identified in:
- `kenhuangus/ASG-SI@c1da9a1d15883d04518f4a7213ccba612b0e6b28`
- the existing Hunter `production/LEARNING_ENGINE.md` principles around disjoint train/confirm evidence, immutable evaluation and separate global approval.

No ASG-SI source code is copied here.
