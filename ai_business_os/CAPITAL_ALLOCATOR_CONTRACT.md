# Evidence-First Portfolio Capital Allocator — Step 9

The final AI Business OS upgrade converts verified operating evidence into transparent portfolio
decision support. It can rank initiatives and propose bounded resource allocations, but it does not
treat a score as truth and it cannot move money or resources outside Step-6 governance.

## What it allocates

- AI_COST_UNITS
- ENGINEERING_HOURS
- HUMAN_HOURS
- CASH_CENTS

## Evidence model

Each initiative snapshot may contain:

- realized cash collected;
- recognized revenue;
- cash costs;
- AI costs;
- contracted pipeline;
- qualified pipeline;
- recent human effort;
- remaining effort;
- time-to-cash estimate;
- retention evidence;
- market evidence;
- strategic reuse evidence.

Every metric used by the allocator requires a typed source, a source reference, a SHA-256 source
identity, and an observation time. Metric-specific source rules prevent weak evidence from
masquerading as stronger facts. For example, realized cash cannot come from a model estimate.

## Ranking model

The allocator does not output a probability of success or promise ROI.

It produces a transparent decision-support score from:

1. evidence-backed economic value;
2. a dimensionless log-scaled economic index;
3. evidence-backed retention / market / reuse signals;
4. explicit effort and time-to-cash penalties;
5. a fixed-schema evidence-coverage penalty.

Missing core metrics reduce evidence coverage even if the reported metrics are favorable. This
prevents cherry-picked data from receiving false confidence.

## Hard invariants

1. Portfolio initiatives may bind to active typed BUSINESS and PRODUCT nodes from Step 5.
2. Allocator policy changes require a HUMAN principal.
3. Every policy version is immutable and content-addressed.
4. Realized cash cannot be sourced from MODEL_ESTIMATE, CRM, or other inadmissible source types.
5. Metric evidence cannot be future-dated relative to the snapshot.
6. Stale evidence is rejected using metric-specific freshness windows.
7. Evidence coverage uses a fixed core schema, so omitted weak metrics cannot inflate confidence.
8. Snapshot dates must be sufficiently close for a fair portfolio comparison.
9. Dollars are not directly added to hours or days; monetary magnitude is converted to a
   dimensionless economic index before combination with non-monetary signals.
10. Qualified pipeline receives less influence than contracted pipeline, which receives less
    authority than realized cash.
11. The score is advisory and its component breakdown is retained for inspection.
12. Initiatives below the minimum evidence threshold are OBSERVE_ONLY and cannot receive an
    allocation plan.
13. Negative realized economics with no compensating evidence are surfaced for PAUSE_REVIEW.
14. Allocation plans use bounded proportional allocation and enforce a configurable concentration cap.
15. Cash allocations are integer-exact in cents.
16. A newer snapshot invalidates authorization of an older ranking.
17. A newer allocator policy invalidates authorization of an older ranking.
18. Resource allocation requests pass through Step-6 governance.
19. CASH_CENTS is classified as MONEY_MOVEMENT and therefore requires human approval.
20. Global/per-agent kill switches can block allocation authorization.
21. Governance authorization must bind to the exact plan hash, ranking hash, total resource pool,
    and initiative allocations.
22. Each plan can consume governance authorization only once.
23. This module proposes resource allocation; it does not directly transfer funds, deploy workers,
    or make external commitments.

## Intended operating loop

evidence-backed business snapshots
-> transparent portfolio ranking
-> bounded allocation proposal
-> stale-data / stale-policy recheck
-> Step-6 governance
-> human approval where required
-> external execution
-> outcomes
-> Step-4 value memory
-> Step-5 graph / Step-8 truth updates
-> next allocation cycle

The purpose is not to let an AI "pick winners." The purpose is to make scarce-resource decisions
more consistent, evidence-aware, explainable, and resistant to enthusiasm, stale information, and
weakly supported forecasts.
