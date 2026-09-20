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
The first standardized outcome is now recorded below. It is a **technical-only PARTIAL** result, not commercial validation.

The system still has **$0 directly evidenced revenue and $0 directly evidenced customer value** in the structured outcome ledger.

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


## OUT:20260920:freight-v15-4-synthetic-rehearsal
- Date: 2026-09-20
- Experiment: **EXP-001 — Freight blind audit to realized settlement**
- Opportunity: Freight Recovery
- Result: **PARTIAL**
- Technical result: the v15.4 synthetic readiness → fixed-fee qualification → blind proof → persistent settlement → buyer-report rehearsal passed. The proof-derived report and persistent settlement store reconciled on realized and fee-eligible synthetic amounts.
- Commercial result: **no external buyer validation**; no diagnostic/pilot/annual revenue and no customer recovery claimed.
- Realized customer value: **$0 recorded**
- Revenue: **$0 recorded**
- Contributing capabilities: **CAP-006, CAP-016**
- Origin search run: `RUN:20260920T155926Z:hunter03:settlement-persistence-race`
- Search-policy consequence: keep the freight discovery freeze and **zero ACTIVE_SEARCH gaps**; prioritize an authorized customer population plus rights/security diligence instead of broader repository hunting.
- Evidence: `freight/synthetic_rehearsal.py`; Freight Commercial Contracts CI run `35522536180`.
- Follow-up: first external outcome must record actual paid engagement and/or buyer-controlled realized settlement evidence before any revenue/customer-value field becomes positive.


## Search-credit attribution

An outcome can depend on more than one discovery run. To prevent double counting:

- list all contributing runs in `origin_search_ids`;
- optionally provide `search_credit_weights` mapping every origin run ID to a nonnegative weight;
- explicit weights must sum to **1.00**;
- if weights are omitted, the machine layer assigns equal credit across origin runs;
- realized revenue/customer value/engineering compression remain recorded once at the outcome level, while strategy-level reports receive only their fractional attribution.

Do not use unequal weights merely to make a favored search strategy look better.
