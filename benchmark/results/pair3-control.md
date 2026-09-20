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

TASK: 17
CONDITION: CONTROL
STARTING HYPOTHESIS: A strong match would normalize multiple payment and settlement sources into money-safe records, use deterministic exact/net/refund/split rules, explicitly quarantine ambiguity and duplicates as exceptions, and prove those edge cases with executable tests rather than only a dashboard.
DISCOVERY METHODS: Broad multi-processor/payment-reconciliation repository search; capability-term search for fee-adjusted/refund/split/dedupe semantics; code/test-level inspection and comparison of three promising repositories.
CANDIDATE: Etherlabs-dev/multi-processor-reconciliation
CANONICAL URL: https://github.com/Etherlabs-dev/multi-processor-reconciliation
EXACT REVISION: 2f9397fbe56a76abeee42a01a37536ad1811a806
VERDICT: STRONG
A-F SCORE: A4 B5 C5 D4 E5 F5 = 28/30
EVIDENCE INSPECTED: Repository metadata/license and exact HEAD commit; .github/workflows/ci.yml; src/reconciliation/matching.py; src/reconciliation/models.py; src/reconciliation/benchmark.py; tests/test_matching.py; tests covering idempotency, normalization, Postgres, service/workflows; comparison against sebastienrousseau/reconcile-mcp and himanisharrma/payops-copilot plus lighter triage of VsevaTech/payment-reconciliation-helper and other searched candidates.
CLAIMS VERIFIED: IMPLEMENTED deterministic Decimal-based reconciliation over canonical source/account records; exact-reference/exact-amount/date-window matching; fee-aware classification when gross differs but net agrees; full/partial refund and reversal matching with type isolation; bounded many-to-one split-payment matching with ambiguity quarantine; duplicate-input detection from idempotency keys; explicit discrepancy classes for ambiguous candidates/splits, currency/date/amount mismatches, unmatched refunds and missing counterparts; stable SHA-256 input fingerprint. TESTED: unit tests directly cover exact, fee-aware, full/partial refund, unique split, ambiguity, duplicates, order independence and invalid config; CI also runs pytest against a Postgres-loaded schema/seed, workflow validation, deterministic benchmark, package audit and Docker test.
CLAIMS NOT VERIFIED: Live Stripe/PayPal/Square/ACH integrations were not executed against production data; benchmark data are synthetic; marketing claims about hours saved/error reduction were not independently validated; split matching is bounded many-to-one (max group size configurable 2–5), not unrestricted many-to-many settlement solving.
STRONGEST OBJECTION: The core engine is unusually well aligned to the task, but the repository is still a portfolio-style implementation whose hardest remaining production risk is messy real provider/bank data and unbounded/high-volume settlement grouping rather than the matching semantics themselves.
COMMERCIAL WEDGE: Multi-processor close/revenue-assurance service for merchants: ingest processor and bank exports, auto-clear exact/net/refund/split cases, route ambiguous/duplicate/unmatched exceptions with evidence, then sell managed daily reconciliation or recurring SaaS.
SEARCH EFFORT: 11 materially distinct searches; 3 deep repository inspections.
FALSE-PROMOTION RISK: LOW-MEDIUM — the code/tests verify the requested matching semantics, but synthetic data and bounded split size make it easy to overstate production readiness.
LESSON: N/A
COMPLETED_AT: 2026-09-20T02:03:21-04:00

TASK: 18
CONDITION: CONTROL
STARTING HYPOTHESIS: The strongest match would make inventory decisions from temporally admissible evidence, explicitly distinguish event/availability/decision time, preserve immutable issued decisions, settle physical inventory through a ledger, calibrate only from actually resolved observations, and convert uncertainty into orders without leaking future information.
DISCOVERY METHODS: Broad inventory-decision/replenishment searches emphasizing temporal correctness and reconciliation rather than forecast accuracy; code-level search for observation availability, event-time watermarks, settlement ledgers, calibration windows and order-up-to logic; low-attention/zero-star discovery and deep comparison of Vzlentin/calibre, sushant5/rfid-inventory-replenishment-platform and howardcodes/PulseInventory.
CANDIDATE: Vzlentin/calibre
CANONICAL URL: https://github.com/Vzlentin/calibre
EXACT REVISION: 264b6fc27fd4293660983c2adf9f86cfa1b4d733
VERDICT: STRONG
A-F SCORE: A4 B5 C5 D5 E5 F3 = 27/30
EVIDENCE INSPECTED: Exact repository metadata/HEAD and recursive tree; src/calibre/observations.py; src/calibre/engine/calibration.py; src/calibre/settle.py; src/calibre/order.py; tests/test_observations.py; tests/test_order.py; pyproject.toml; comparison against the RFID replenishment platform's durable event-time/projection semantics and PulseInventory's reconciliation/learning architecture.
CLAIMS VERIFIED: IMPLEMENTED temporal actuals model separates target period from `available_at`; withheld actuals are NaN rather than zero; a value is admissible only when target and publication time are both at or before the observation clock. Delivery is once-only with idempotent identical retries and conflicting revisions rejected. Hierarchical aggregates wait for all contributing members and inherit the latest member availability time. TESTED: late deliveries resolve their original issuance row without rewriting already-issued points/interval widths; early publication cannot resolve future targets or unissued forecasts; late old scores keep original-origin semantics and do not displace newer calibration-window rows. IMPLEMENTED bounded calibration state retains newest K resolved origin keys rather than arrival-order rows, explicitly handling late members. IMPLEMENTED settlement mutates on-hand/in-transit inventory through arrivals, demand, sales, missed sales, end inventory and holding/shortage costs; order-up-to subtracts both on-hand and the full inbound pipeline. TESTED ordering backtests enforce warm-up readiness, settle gaps/tail periods exactly once, avoid repeating orders, and persist a decision/cost ledger suitable for audit/replay.
CLAIMS NOT VERIFIED: The inspected revision is a compact library/backtest engine rather than a production ERP/WMS integration; live inventory adapters, purchase-order execution and production-scale persistence were not established at this exact revision. Forecasting itself is still comparatively simple in the inspected source. Repository metadata at the inspected revision exposes no detected public license, so deployment/right clarity is weaker than the technical semantics. No independent real-retailer outcome benchmark was established.
STRONGEST OBJECTION: Calibre's temporal semantics are unusually rigorous, but the exact inspected revision proves a decision/backtest kernel, not a production replenishment service; the commercial value depends on wrapping these semantics around real ERP/WMS data and execution.
COMMERCIAL WEDGE: Evidence-correct replenishment audit/decision service for retailers or distributors: ingest inventory/demand snapshots with explicit availability times, replay what was knowable at each decision point, generate calibrated order-up-to recommendations, and produce an immutable settlement/cost ledger that explains why each order was or was not justified.
SEARCH EFFORT: 10 materially distinct searches; 3 deep repository inspections.
FALSE-PROMOTION RISK: LOW-MEDIUM — the temporal/provenance invariants are directly implemented and heavily tested, but it would be easy to overstate the current revision as a deployable enterprise planning platform rather than a high-quality decision kernel.
LESSON: N/A
COMPLETED_AT: 2026-09-20T02:09:36-04:00
