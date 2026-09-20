# Pair 3 — CONTROL results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

TASK: 16
CONDITION: CONTROL
STARTING HYPOTHESIS: The strongest public airline-disruption engine would model aircraft, crew and passenger state together under operational constraints and disruptions, with a replayable simulation or optimization core rather than merely predicting delays.
DISCOVERY METHODS: Broad airline-recovery repository/paper search; GitHub repository-name and adjacent-term search; code/tree-level inspection of candidate implementations plus independent publication validation.
CANDIDATE: broad-well/recovair-abm (RecovAir)
CANONICAL URL: https://github.com/broad-well/recovair-abm
EXACT REVISION: 7b3379cb431591c148a26993097a08487ae6886b
VERDICT: WATCH
A-F SCORE: A3 B5 C4 D4 E4 F2 = 22/30
EVIDENCE INSPECTED: README/build and scenario instructions; src/crew.rs, src/dispatcher.rs, src/scenario.rs, src/airport.rs and src/model.rs; repository tree/test and validation surfaces; exact HEAD commit; peer-reviewed Frontiers 2025 RecovAir article; comparison against mkoa/airline.disr.mgt and kahyakursat1-cloud/hybrid-cpsat-qiga-airline-recovery.
CLAIMS VERIFIED: IMPLEMENTED event-driven airline network simulation with aircraft, crew, flights, passenger demand and airport state; crew availability, location, turnaround and simplified rolling duty-time checks; airport departure/arrival rate constraints and disruption clearances; delay/cancellation handling; aircraft recovery/reassignment including a DFS strategy; scenario loading from fixed SQLite state; passenger movement along itinerary paths subject to aircraft capacity. TESTED/EXTERNALLY VALIDATED: repository contains executable test/validation scripts, and the peer-reviewed RecovAir paper reports validation against Southwest 2022 disruption and 2024 operational scenarios and comparison of recovery strategies.
CLAIMS NOT VERIFIED: No full FAA Part 117 legality implementation was established; crew legality is simplified. Passenger logic is simulation/path loading rather than a verified passenger reaccommodation optimizer. The inspected core is a simulator plus heuristic recovery strategies, not a general exact constrained-optimization engine. Probabilistic/stochastic uncertainty handling was not established beyond configurable disruption scenarios. Byte-for-byte deterministic replay was not explicitly tested, although fixed scenario state and a deterministic event loop support repeatable runs. No explicit repository license file was observed in the inspected tree.
STRONGEST OBJECTION: RecovAir is unusually deep and integrated, but it does not fully satisfy the task's strongest wording: exact constrained optimization, comprehensive crew legality, optimized passenger recovery, stochastic uncertainty and explicitly tested deterministic replay are not all present in the verified implementation.
COMMERCIAL WEDGE: Airline operations-control disruption digital twin: replay a historical or planned disruption, compare aircraft/crew recovery policies, quantify cancellations/delays/passenger impact, and sell strategy-evaluation/implementation work before attempting live decision automation.
SEARCH EFFORT: 8 materially distinct searches; 3 deep repository inspections plus 1 independent peer-reviewed publication check.
FALSE-PROMOTION RISK: MEDIUM — the integrated-recovery framing and real validation make it easy to overread the project as a complete operational optimizer when several requested capabilities are simplified or absent.
LESSON: N/A
COMPLETED_AT: 2026-09-20T01:33:01-04:00
