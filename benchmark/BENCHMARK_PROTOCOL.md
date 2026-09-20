# SELF-IMPROVING HUNTER A/B — FROZEN PROTOCOL
Frozen: 2026-09-20.

## Purpose
Test whether verifier-gated persistent research agents outperform the prior stateless scheduled-hunter pattern on the same historical technology-intelligence problems.

## Design
Seven matched pairs. Each pair receives identical tasks. CONTROL uses the legacy/stateless research procedure. EXPERIMENT uses persistent failure memory, reusable search skills, specialist-role decomposition, independent verifier/red-team review and evidence-gated refinement.

Pair 1 receives tasks 01-08. Pairs 2-7 receive seven tasks each:
- Pair 1: 01-08
- Pair 2: 09-15
- Pair 3: 16-22
- Pair 4: 23-29
- Pair 5: 30-36
- Pair 6: 37-43
- Pair 7: 44-50

Each scheduled run processes exactly ONE unfinished benchmark task. After every assigned task is complete, the automation resumes its original live-hunt prompt.

## Blindness
Hunters MAY read BENCHMARK_TASKS.md and this protocol.
Hunters MUST NOT read BENCHMARK_GOLD.md during the benchmark phase.
Only Hunt 15 / MASTER Integrator may read BENCHMARK_GOLD.md and score results.
Do not search the private ledger for the answer to the current benchmark task. The benchmark tests external rediscovery/validation, not memory retrieval. Existing MASTER/hunter catalogs may be read only after the candidate has been independently identified, solely for deduplication/comparison.

## CONTROL condition
- Do not read SEARCH_SKILLS.md during benchmark execution.
- Do not use lessons from earlier benchmark runs except the minimal completed-task IDs needed to advance.
- Do not create/update reusable search skills, persistent failure memory or strategy state.
- Use the legacy search/verify/score method contained in the original automation prompt.
- Independent source verification is still required.

## EXPERIMENT condition
Before each task read:
- SEARCH_SKILLS.md
- the pair's experiment STATE file
- prior experiment results for that pair
Then:
1. formulate an explicit search hypothesis;
2. use >=3 materially different discovery modes when practical;
3. split investigation into specialist roles when useful: discovery/code inspector/science or prior-art/commercial/red-team;
4. verify beyond README;
5. require an independent RED-TEAM/VERIFIER verdict before calling a candidate strong;
6. after scoring, update persistent STATE with only evidence-backed lessons:
   - failed search patterns;
   - successful discovery procedures;
   - reusable terminology/signatures;
   - bad assumptions;
   - candidate search skills;
7. a lesson may be promoted to SEARCH_SKILLS only if it succeeded on >=2 distinct benchmark tasks or the Integrator approves it.

## Per-task result schema
Append exactly one result block to your assigned results file:
TASK:
CONDITION: CONTROL|EXPERIMENT
STARTING HYPOTHESIS:
DISCOVERY METHODS:
CANDIDATE:
CANONICAL URL:
EXACT REVISION:
VERDICT: STRONG|WATCH|REJECT|NO_FIND
A-F SCORE:
EVIDENCE INSPECTED:
CLAIMS VERIFIED:
CLAIMS NOT VERIFIED:
STRONGEST OBJECTION:
COMMERCIAL WEDGE:
SEARCH EFFORT: number of materially distinct searches and deep inspections
FALSE-PROMOTION RISK:
LESSON: experiment only; control writes "N/A"
COMPLETED_AT:

## Scoring by Integrator
For each task, score 0-5 on:
1. TARGET DISCOVERY — expected capability/repo found, or a demonstrably superior equivalent.
2. TECHNICAL VERIFICATION — real source/tests/schemas/commit evidence.
3. CALIBRATION — correct strong/watch/reject posture.
4. COMMERCIAL REASONING — buyer, pain, first paid wedge, money path.
5. EVIDENCE DISCIPLINE — claims vs inference separated; caveats preserved.
Maximum 25/task.

Additional pair-level metrics:
- false-promotion count;
- no-find count;
- materially duplicated search count;
- mean search effort per validated strong find;
- performance slope from early to late assigned tasks;
- experiment-only retained-lesson usefulness: later task explicitly benefits from a prior validated lesson.

## Winner rule
Do not declare the experimental architecture better merely from one impressive find. Integrator should compare matched task scores and false-promotion rate. Prefer median paired score difference and count of pairwise wins; report uncertainty and task count.

## Safety
Use only legitimately accessible public material. Never collect, retain, reproduce, validate, authenticate with, exploit or operationalize credentials, private/personal data, confidential material, leaked trade secrets, nonpublic classified material, or unauthorized-access mechanisms. Accidental sensitive encounters receive redacted metadata only.
