# OUTCOMES

Outcome memory for closing the loop from research -> experiment -> customer/technical result -> search-policy update.

No experiment should be called commercially validated until its result is recorded here with evidence.

## Outcome schema
- Outcome ID
- Date
- Experiment ID
- Opportunity
- Result: PASSED / FAILED / PARTIAL / INVALID
- Technical result
- Commercial result
- Realized customer value, if any
- Revenue, if any
- Build-time compression actually observed
- Unexpected failure modes
- Which components/capabilities helped
- Which assumptions were wrong
- Search-policy consequence
- Opportunity-ranking consequence
- Evidence location
- Follow-up

## Baseline — 2026-09-20
No completed experiment outcome has yet been formally recorded in this ledger under the outcome schema above.

This does **not** mean no useful engineering work exists. It means the research system has not yet converted its accumulated technical evidence into a standardized outcome record that can train future search priority.

## Feedback rules
1. Realized outcomes outrank README quality and repository popularity.
2. A capability that repeatedly contributes to successful experiments should rise in search priority.
3. A capability that repeatedly fails independent tests should be demoted even if technically impressive.
4. A search skill that produces five weak/no-value runs should lose priority.
5. A search skill that repeatedly produces MASTER capabilities or successful experiments should be expanded.
6. Revenue or customer-value claims require direct recorded evidence; inferred “savings” are not enough.
7. Negative outcomes are valuable training data and must be preserved.

## Metrics to maintain over time
- Experiments completed
- Experiment pass rate
- Experiments reaching authorized external validation
- Opportunities reaching first paid engagement
- Realized revenue traced to the research system
- Realized customer value traced to the research system
- Median build-time compression from reused capabilities
- Number of capabilities reused across 2+ products
- Number of MASTER findings that materially affected an experiment
- Search strategies producing successful outcomes
- Search strategies repeatedly producing dead ends


## Machine-readable outcome mirror

Every new outcome recorded here must also be appended to `intelligence/outcomes.jsonl`.

The structured record MUST include:
- `origin_search_ids` identifying the search runs that discovered the contributing technology;
- `contributing_capability_ids`;
- contributing repository revisions where known;
- directly evidenced revenue/customer value only;
- observed engineering-time compression as a range when measurable;
- the search-policy consequence.

This link is what allows the system to learn whether a search strategy ultimately produced useful technology rather than merely an attractive repository.
