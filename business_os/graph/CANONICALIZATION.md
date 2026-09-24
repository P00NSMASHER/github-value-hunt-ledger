# Upgrade 6 — Entity Canonicalization

Status: **IMPLEMENTED**

The graph can now detect and safely reconcile likely duplicate entities while
preserving every original node.

Example:

```
Federal Express Corporation ─┐
FedEx                         ├─> canonical entity
Federal Express Corp          ┘
```

## Evidence used

The deterministic scorer combines positive evidence from:
- normalized name equality;
- aliases;
- description overlap;
- graph-neighbor overlap;
- exact node-type compatibility.

Missing graph neighbors do **not** count as evidence against a match.

## Three outcomes

- `AUTO_MERGE` — strong deterministic evidence.
- `REVIEW` — ambiguous band; explicit reviewer approval required.
- `KEEP_SEPARATE` — insufficient evidence or incompatible types.

## Preservation rule

A merge never deletes source identities. It creates a canonical node and
`MERGED_INTO` edges containing the score, decision and evidence hash.

This follows the strongest Hunter pattern found in
`rasinmuhammed/node-canon`, while using an independent stdlib-only
implementation.
