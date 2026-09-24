# Verifier-Gated Self-Improvement Contract — Step 3

The AI Business OS may learn new skills and policies, but learning is not deployment.

## Promotion path

```
CURRENT CHAMPION
      ↓
candidate mutation
      ↓
frozen dev + held-out manifests
      ↓
independent verifier scores baseline and candidate
      ↓
zero hard regressions + dev improvement + held-out improvement
      ↓
VERIFIED
      ↓
3 independent canary agents
      ↓
GLOBAL_ELIGIBLE
      ↓
explicit designated-curator approval
      ↓
GLOBAL CHAMPION
```

## Hard invariants

1. The current champion remains active while a candidate is DRAFT, EVALUATING, VERIFIED, or CANARY.
2. Proposer, verifier, and curator must be distinct agents.
3. Development and held-out task IDs must be disjoint.
4. Evaluation manifests are frozen before scoring.
5. Only tasks in the frozen manifests may be scored.
6. Evaluation records are immutable.
7. Missing frozen-task results block assessment.
8. Any hard regression quarantines the candidate.
9. A candidate must improve development performance and clear a minimum held-out improvement delta.
10. VERIFIED is not GLOBAL.
11. At least three independent canary agents must succeed with zero regression before GLOBAL_ELIGIBLE.
12. Canary agents must be independent of proposer, verifier, and curator.
13. Only the skill's designated curator may promote or roll back the champion.
14. Promotion fails if the baseline champion changed after evaluation.
15. Every champion artifact is bound to a SHA-256 identity and every promotion/rollback leaves an audit record.

The gate does not train a model by itself. It governs whether a learned prompt, policy, procedure,
tool strategy, or other skill artifact is allowed to become shared global behavior.
