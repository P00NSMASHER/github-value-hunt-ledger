# Three-Hunter Shadow Pilot

## Purpose
Test the production contracts on live research without contaminating the frozen 50-task A/B benchmark.

## Shadow lanes
1. SHADOW-AI — AI model tooling / persistent-agent infrastructure.
2. SHADOW-SCIENCE — scientific software / research-to-code discoveries.
3. SHADOW-COMMERCIAL — finance/recovery/decision systems with direct money paths.

## Authority
Shadow hunters may write only:
- production/shadow/results/<lane>.md
- production/shadow/state/<lane>.md
- production/shadow/referrals.md

They may NOT edit MASTER, SEARCH_SKILLS, COMBINATIONS, SEARCH_QUEUE, CAPABILITIES, TECHNOLOGY_RADAR, or benchmark files.

## Per-run procedure
1. Read production/ARCHITECTURE.md, ROLE_CONTRACTS.md and this protocol.
2. Read lane state and previous shadow results.
3. Choose one explicit hypothesis.
4. Use >=3 discovery methods when practical.
5. Deep-inspect <=3 serious candidates.
6. For the best candidate, write a claim/evidence packet.
7. Run an independent verifier/red-team pass using a separate reasoning context.
8. Record verdict and proposed score, but do not promote centrally.
9. Update lane-local lessons only.
10. Emit cross-lane referrals.
11. Report cost proxies: materially distinct searches, deep inspections, external tool calls and any reproducible test executions.

## Shadow KPIs
- verifier-passed strong candidates per run;
- verifier overturn rate;
- false-positive/rejected-after-strong rate;
- unique candidates not already in ledger;
- search effort per verifier-passed strong candidate;
- number of lessons reused successfully later;
- number of candidate skills reaching two-task eligibility.

## Success gate
Shadow architecture is promising when, over at least 15 combined shadow runs:
- no sensitive-source or verifier-bypass incident;
- <= legacy live-hunt false-promotion rate;
- at least 3 verifier-passed genuinely new strong candidates OR 3 high-value negative findings preventing duplicate work;
- at least 2 local lessons reused on a later independent task;
- search effort does not exceed 1.5x ordinary hunter effort without a clear quality gain.

## No benchmark contamination
Do not read BENCHMARK_GOLD.md. Do not use benchmark tasks as shadow assignments. Do not write to benchmark result/state files.
