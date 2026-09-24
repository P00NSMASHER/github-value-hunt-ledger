# Upgrade 4 — Value-Weighted Memory

Status: **IMPLEMENTED**

The Business OS now persists lessons with more than text. Each memory carries:

- kind: `TACTIC | OUTCOME | WARNING | DECISION`;
- objective scope;
- observed value in [-1, 1];
- confidence;
- evidence count;
- timestamps;
- metadata.

## Retrieval score

The baseline retrieval score is:

```
relevance
× value factor
× confidence
× recency
× scope match
```

This prevents a repeatedly unsuccessful tactic from ranking alongside a tactic
that actually produced useful outcomes.

Negative `WARNING` memories are handled differently: strong negative evidence
remains highly retrievable so the system can avoid repeating known mistakes.

## Outcome learning

`observe_outcome()` updates value from realized evidence rather than letting an
agent simply rewrite its own memory score. Low-confidence observations receive
less weight.

## Hunter lineage

This step implements the value-memory pattern already developed in Hunter's
`production/LEARNING_ENGINE.md`, including the idea that observed downstream
outcomes should influence future retrieval without becoming authority.
