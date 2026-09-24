# Value-Weighted Memory Contract — Step 4

The AI Business OS now records not only **what happened**, but whether a remembered tactic has
produced independently verified value.

## Learning path

```
memory / tactic
     ↓
observed outcome + evidence
     ↓
independent verifier
     ↓
VERIFIED / REJECTED
     ↓
recency-weighted value estimate
     ↓
confidence-weighted retrieval prior
```

## Hard invariants

1. Memory content is content-addressed and versioned.
2. Outcome observations are immutable once created.
3. An observer cannot verify its own outcome.
4. UNVERIFIED and REJECTED outcomes contribute zero learned value.
5. Verified rewards are bounded to [-1, 1].
6. Attribution per event is conserved: all VERIFIED memories together may claim at most 1.0 credit.
7. The same event cannot be counted twice for the same memory.
8. Objective-specific memories do not transfer into unrelated objectives.
9. Explicit global memories may transfer across objectives, but receive a discount.
10. Recent verified outcomes receive more weight than stale outcomes through a configurable half-life.
11. Confidence grows with verified evidence weight; one result can never create full confidence.
12. Untested memories retain a neutral prior rather than disappearing from retrieval.
13. Negative verified outcomes reduce a memory's retrieval score.
14. Retired memories are excluded from normal ranking.
15. Value-weighted retrieval is advisory; it does not bypass completion verification, self-improvement promotion, or later permission gates.

## Ranking

This layer intentionally does not perform semantic search itself. An upstream retriever supplies
semantic relevance in [0, 1]. Value Memory then re-ranks those candidates using:

- semantic relevance;
- objective match;
- verified recency-weighted reward;
- evidence confidence.

This separates **"is this relevant?"** from **"has this worked?"** and prevents business outcome
history from becoming a substitute for factual or policy authority.
