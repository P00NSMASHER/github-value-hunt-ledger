# Upgrade 9 — Evidence / Truth Engine

Status: **IMPLEMENTED**

The final upgrade makes proof structure explicit. An AI statement is not a
fact merely because the model is confident.

Each claim is evaluated against typed proof obligations. Evidence must satisfy
the obligation's authority, admissibility, freshness, support-count and source-
independence requirements. Contradictory evidence is preserved instead of
being averaged away.

Possible claim verdicts:

- `PROVEN` — every required obligation is satisfied.
- `CONTESTED` — admissible evidence conflicts with or contradicts a required
  obligation.
- `NOT_PROVEN` — some evidence exists, but required proof is stale,
  inadmissible, incomplete or insufficiently independent.
- `UNKNOWN` — no relevant evidence exists. Absence is not converted into
  falsehood.

Each receipt binds the claim, evaluation time, obligation findings and exact
evidence-set identity with SHA-256.

## Next-best evidence

When proof is incomplete, the engine can rank candidate evidence-acquisition
actions. It does not invent a probability of success. Instead it simulates
each candidate as fresh supporting evidence and measures whether that
counterfactual would improve an obligation or the final verdict, while
filtering unavailable, expired, wrong-authority and duplicate-source actions.

This independently implements the strongest pattern identified in Hunter's
TrustMesh research: proof obligations, fail-closed evidence state, preserved
contradictions and deterministic next-evidence planning.
