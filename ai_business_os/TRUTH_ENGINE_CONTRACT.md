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
14. A next-evidence recommendation is bound to the exact truth receipt/evidence snapshot; if real evidence changes, the claim must be re-evaluated.
15. Evidence acquisition requests pass through Step-6 governance. This engine recommends/authorizes acquisition; it does not bypass permissions or execute external tools.

## Intended loop

claim -> proof obligations -> real evidence -> truth receipt -> missing blocker -> ranked evidence action
-> Step-6 authorization -> external acquisition -> real evidence added -> re-evaluation.

This is the layer that lets an agent say not just 'I think this is true,' but exactly which
requirements are proven, which are contradicted, which remain unknown, and what evidence would
most efficiently improve the decision.