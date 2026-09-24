# Evidence / Truth Engine Contract — Step 8

The AI Business OS now evaluates consequential claims against explicit proof obligations instead
of treating model confidence, graph connectivity, or repeated assertions as truth.

## Claim verdicts

- PROVEN: every required proof obligation is satisfied.
- CONTESTED: admissible evidence conflicts with or contradicts a required obligation.
- NOT_PROVEN: relevant evidence exists, but proof is stale, inadmissible, incomplete, or insufficiently independent.
- UNKNOWN: no relevant evidence exists. Absence is not converted into falsehood.

## Obligation states

SATISFIED, MISSING, STALE, INADMISSIBLE, INSUFFICIENT_SUPPORT,
INSUFFICIENT_INDEPENDENCE, CONFLICTED, CONTRADICTED.

## Hard invariants

1. Every claim has one or more explicit proof obligations.
2. Every obligation defines admissible authority types and may define freshness, source-count, and independence requirements.
3. Every evidence item binds to a source reference and SHA-256 source identity.
4. Evidence from a future observation time is inadmissible for an earlier evaluation.
5. Expired or over-age evidence is STALE rather than silently accepted.
6. Wrong-authority or explicitly inadmissible evidence remains visible but cannot prove the claim.
7. Contradictory admissible evidence is preserved and produces CONTESTED rather than being averaged away.
8. Source-count and independence-group requirements are evaluated separately.
9. UNKNOWN means no relevant evidence; it does not mean false.
10. Every truth receipt binds the claim hash, evaluation time, findings, and exact evidence-set hash.
11. Next-evidence planning is counterfactual only; hypothetical evidence is never persisted into the real evidence ledger.
12. Duplicate independence groups are not recommended as if they were independent corroboration.
13. Wrong-authority, unavailable, expired, or non-useful acquisition actions are filtered from next-evidence recommendations.
14. SUPPORT actions are never recommended as a way to resolve a CONFLICTED or CONTRADICTED obligation.
15. Conflict-resolution actions must target one exact contradictory evidence item on the same claim and obligation.
16. Conflict-resolution planning is counterfactual and non-destructive: it never deletes or mutates the real contradictory evidence.
17. A next-evidence recommendation is bound to the exact truth receipt/evidence snapshot; if real evidence changes, the claim must be re-evaluated.
18. Evidence acquisition requests pass through Step-6 governance. This engine recommends/authorizes acquisition; it does not bypass permissions or execute external tools.

## Intended loop

claim -> proof obligations -> real evidence -> truth receipt -> missing blocker -> ranked evidence action
-> Step-6 authorization -> external acquisition -> real evidence added -> re-evaluation.

This is the layer that lets an agent say not just 'I think this is true,' but exactly which
requirements are proven, which are contradicted, which remain unknown, and what evidence would
most efficiently improve the decision.

## Conflict-resolution planning

When a required obligation is CONFLICTED or CONTRADICTED, the planner changes modes. It will not
rank another supportive source as if accumulating support could erase the contradiction. A
RESOLVE_CONFLICT action must identify the exact contradictory evidence item to adjudicate.

The counterfactual planner may simulate what would happen if that contradiction were resolved, but
the persisted evidence ledger remains unchanged. Only a real later adjudication/evidence event may
change the actual truth state.
