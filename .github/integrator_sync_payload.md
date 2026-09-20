MARKER: <!-- INTEGRATOR-R11-DECISION-ACTION-2026-09-20T0112-0400 -->

=== APPEND COMBINATIONS.md ===
## Grid uncertainty-to-restoration acceptance loop — model parity -> uncertain state -> operating envelope -> inspection/restoration action
- Add `frederikgeth/PowerOptLab.jl@4f417d470c8bff78bd0941658f97030e5ddb7692` after CIMHub/DREAMS as the uncertainty-aware state/model and dynamic operating-envelope challenger, and `leadcatlab/MWLP-Storm-Repair@07adc8df235b6c95df7c8a679819a91256d40a7c` as the post-failure crew-sequencing component. Keep Jestrada stochastic inspection and ORBIT UAS mission planning as separate pre-failure/field-action layers, with TrustMesh preserving the evidence/decision obligations.
- Combined capability: electrically validated feeder model -> competing state/parameter hypotheses -> evidence-aware import/export envelope -> risk-priced inspection or storm-failure state -> minimum-weighted-latency crew action -> field/repair outcome -> replayable evidence. Each stage remains independently falsifiable; no component may validate its own upstream truth.
- First paid wedge: offline feeder uncertainty/operating-envelope study plus historical storm-restoration replay for one authorized utility case. Compare PowerOptLab against a simpler deterministic OPF on identical feeder inputs, and MWLP against nearest-first/severity-first on identical failures/repair times/customer weights.
- Promotion gate: uncertainty must materially change a decision or reduce false confidence, and minimum-latency dispatch must materially reduce customer-minutes-out/weighted downtime. Until then both remain below MASTER despite 27/30 and 24/30 component scores.
- Rights: PowerOptLab code is BSD-3-Clause and repo-described data are CC BY 4.0; MWLP is MIT. Customer feeder/operations data, external standards/models and third-party datasets remain separately governed.

## Airline IROPS Decision Assurance — normal RM -> disruption risk -> constrained reaccommodation -> evidence/outcome
- Components: existing `airsim/rmol` normal revenue-management leader + `Robertn02/Airline-Revenue-Management-IROPS-Seat-Allocation-Optimizer@9a235b1ceb7a53f467c060b6a2750590b1ee0cd1` + `mizuharaa/olus` disruption-recovery work where independently useful + TrustMesh evidence/authorization.
- Combined capability: frozen disruption/passenger/cabin/connection facts -> calibrated risk and explicit economic objective -> constrained seat/reaccommodation allocation -> deterministic explanation/audit record -> realized service/economic outcome. Repository-reported synthetic savings are benchmark evidence only, not customer ROI.
- First paid wedge: historical/shadow IROPS replay against FCFS/status-priority and buyer incumbent allocations; price expected and later realized economic/service loss before any live-decision integration.
- Hard invariant: no live passenger/customer decision or dollar claim without buyer-authorized operational truth, frozen cost assumptions and post-event outcome evidence. Synthetic benchmark economics cannot be promoted into realized savings.
- Status: 27/30 challenger; keep out of MASTER until independent replay beats simple baselines on realistic economics and preferably one authorized historical period.

=== APPEND COMPONENTS.md ===
### frederikgeth/PowerOptLab.jl — uncertainty-aware distribution-grid decision lab
- Revision: `4f417d470c8bff78bd0941658f97030e5ddb7692`.
- Score: **27/30 — A3 B5 C5 D5 E4 F5**.
- Rights: BSD-3-Clause repository code; repo-described data CC BY 4.0; external/customer feeder data and standards remain separate.
- Capability: four-wire distribution state/parameter estimation, candidate-model screening, scenario/fairness/security-aware dynamic import/export envelopes, multi-period OPF, DER scheduling and closed-loop convergence/stability evidence with substantial tests.
- Integration: CIMHub model parity -> DREAMS deterministic hosting/QSTS -> PowerOptLab uncertainty/evidence challenge -> inspection/restoration action. Keep as a challenger, not an authority, until it changes a decision or reduces false confidence versus deterministic OPF on the same rights-clean feeder.

### leadcatlab/MWLP-Storm-Repair — weighted-latency storm restoration kernel
- Revision: `07adc8df235b6c95df7c8a679819a91256d40a7c`.
- Score: **24/30 — A3 B4 C4 D4 E4 F5**.
- Rights: MIT; operational outage/customer/road data remain separately governed.
- Capability: multi-crew repair assignment/sequencing around minimum weighted latency, targeting customer waiting/downtime rather than raw route distance, with graph/simulation/benchmark code and tests.
- Integration: post-failure action layer after feeder/risk evidence. Require a frozen benchmark against nearest-first and severity-first, including repair-time uncertainty, before treating the method as commercially differentiated.

=== APPEND OPPORTUNITIES.md ===
### Airline IROPS Decision Assurance — shadow disruption economics before live control
- Sources: `Robertn02/Airline-Revenue-Management-IROPS-Seat-Allocation-Optimizer@9a235b1ceb7a53f467c060b6a2750590b1ee0cd1` + existing airline RM/disruption components + TrustMesh.
- Buyer/problem: airline OCC/revenue-management teams must trade reaccommodation capacity, misconnect/spill risk, loyalty and yield under disruption while retaining an auditable reason for each allocation.
- First paid wedge: historical/shadow replay on one rights-clean or buyer-authorized disruption population, compared with FCFS/status-priority and the incumbent/manual allocation.
- Monetization: fixed decision-assurance study -> recurring shadow monitoring/decision support; no autonomous live passenger action initially.
- Score: **27/30 — A4 B5 C5 D4 E4 F5**. The repository is unusually complete, but current savings evidence is synthetic/repository-reported rather than independent production proof.
- Next validation: freeze realistic disruption economics and constraints first, then compare expected and realized service/economic outcomes. Promote only if it materially beats simple baselines and survives outcome reconciliation.

### Grid Model Acceptance + Hosting/Resilience Study — evidence-to-action extension
- Extend the existing grid opportunity with `PowerOptLab.jl@4f417d470c8bff78bd0941658f97030e5ddb7692` for uncertainty-aware state/model and operating-envelope analysis and `MWLP-Storm-Repair@07adc8df235b6c95df7c8a679819a91256d40a7c` for post-failure weighted-latency restoration.
- The commercial sequence becomes model-conversion parity -> deterministic hosting/QSTS -> uncertainty/evidence challenge -> risk/inspection or storm-restoration action -> measured field/outage outcome.
- Do not sell “better grid decisions” from method novelty alone. Require same-input baseline tests: deterministic OPF versus PowerOptLab, and nearest/severity dispatch versus MWLP, with planted model uncertainty and repair-time uncertainty.

=== APPEND REJECTED.md ===
## Decision-engine dominated patterns — 2026-09-20
- `AbedSalekin/revenue-decision-engine@4a545f96255c758b6886a86306c490156579ac7c` — reject/deprioritize. Broad app scaffolding and AI recommendation text do not provide deterministic/causal decision logic, auditable objective math or evidence that recommendations improve revenue. Revisit only with tested economic models, reason codes and controlled outcome evidence.
- `AkramZaabi/Operational-Resaerch-Inspection-Routing-Optimizer@c5e847b3e02abd1f79f869f167c4e4f9511cd6b7` and `maudefish/operator-task-optimization@ede0acf65addd6d79d8425a4317724b3dc535911` — generic routing/assignment formulations are dominated by Jestrada/SAGE/RosterSpec/MIP++ and the established inspection/scheduling stack. Revisit only if they add unique domain authority, stronger route semantics, conventional tests and an incumbent-quality benchmark.
- `anara-analytics/decision-intelligence-inventory-optimization-olist@e18efdf867bde9e3296f9665b16d7a8d74f23232` and `nathaniel-gordon/stockmind@68435497715497cb309eb40ce4b0228eb86c1129` — standard forecast/reorder/BI logic is dominated by `inventory_tools`, Calibre-style temporal correctness and `deepbullwhip`. Revisit only for materially richer constraints, live operational state or decision-cost validation.
- `tadiwamark/pdM_Genset_Analytics@e7c79ddb7f022661d58047ce3f9d7372e6482c8b` — anomaly-to-LLM recommendation prototype without deterministic action economics or surfaced conventional tests. External model/API and bundled data/model rights remain separate. The inspected README showed only a placeholder environment-variable example; no credential or sensitive value was collected, retained or tested. Revisit only with validated maintenance-action economics and auditable deterministic decision logic.

=== APPEND SEARCH_QUEUE.md ===
## Decision-engine refinement from Hunter 38
- **Grid evidence-to-action:** benchmark `PowerOptLab.jl@4f417d470c8bff78bd0941658f97030e5ddb7692` against a simpler deterministic OPF on the exact same rights-clean feeder. Seed state/model/parameter ambiguity and require the uncertainty/evidence layer to change a decision or correctly widen/restrict the operating envelope. If that survives, benchmark `MWLP-Storm-Repair@07adc8df235b6c95df7c8a679819a91256d40a7c` against nearest-first and severity-first with identical failures, crew counts, customer weights and uncertain repair times. Search only for authoritative asset criticality/failure-cost/outage/repair outcome sources or missing interoperability needed to run those tests; stop generic OPF, crew-routing and drone-planning discovery.
- **Airline IROPS:** benchmark `Robertn02/Airline-Revenue-Management-IROPS-Seat-Allocation-Optimizer@9a235b1ceb7a53f467c060b6a2750590b1ee0cd1` on a frozen rights-clean/buyer-authorized disruption corpus against FCFS, status-priority and incumbent/manual allocations. Freeze cabin/connection constraints and cost assumptions before scoring; measure realized service/economic outcome where available. Search only for hard operational/source adapters, reaccommodation settlement/service outcomes or failure modes the current engine cannot represent; stop generic airline RM/optimization demos.
- **Inventory repair-first:** `DPFNeiland/demand-forecasting-inventory-optimization@93645b67082400591a6f99676a2f98b44c5683b2` remains watch because retrospective test-quarter demand influences ABC/low-demand policy. Do not promote reported economics until every feature/policy input is point-in-time and walk-forward results beat seasonal-naive plus the incumbent reorder policy. Stop additional generic EOQ/(s,S)/forecast prototypes.
- `Richard-0403/CMJCC@54b5cfc04e27355d8f3b11628245cf0574fe68c9` is useful only as an evidence-bound hard-filter/soft-rank pattern for CaptureBrief/vendor qualification. Deepen it only if a procurement fixture exposes a gap not already covered by TrustMesh + Canon; do not create a separate matching-product lane.
