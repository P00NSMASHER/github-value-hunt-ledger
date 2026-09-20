# TECHNOLOGY_RADAR

Emergence radar for technical capabilities that may become commercially important before they are obvious categories.

Scores use 0–5 for:
- N = Novelty
- M = Technical maturity
- A = Adoption acceleration
- C = Commercial importance
- X = Cross-domain applicability

Emergence product = N × M × A × C × X. Treat it as a prioritization aid, not scientific precision.

## Radar — 2026-09-20

### RAD-001 — Proof-carrying operational software
- Thesis: high-value systems are moving from “produce an answer” toward “produce an answer plus authority, evidence, replayability and outcome lineage.”
- Signals: freight recovery, structured invoice validation, recovery proof, compliance evidence and identity mastering independently converge on source hashes, explicit unknown states, deterministic replay and signed/traceable outputs.
- Score: N4 M4 A4 C5 X5 = **1600**.
- Status: BUILD / EXPAND.
- Commercial implication: strongest direct-money and regulated workflows may differentiate on proof quality rather than model cleverness.
- Search next: systems that bind source authority -> deterministic expected state -> actual state -> evidence -> realized outcome.

### RAD-002 — Selective prediction / abstention for business automation
- Thesis: calibrated refusal and human review are becoming core infrastructure when AI-extracted facts drive money or compliance.
- Signals: Assay-style field-level accept/review; money-bearing stacks already fail closed on ambiguity.
- Score: N4 M4 A4 C5 X5 = **1600**.
- Status: BUILD / CROSS-POLLINATE.
- Commercial implication: a reusable acceptance layer can be more valuable than another extraction model.
- Search next: production systems with explicit false-accept budgets, legal alternatives and review-routing economics.

### RAD-003 — Reviewed identity compilers
- Thesis: identity resolution is shifting from one-off fuzzy matching toward versioned registries with durable positive/negative judgements, human promotion, reversible merge/split correction and exact runtime replay.
- Signals: Canon supplies promoted-version production registry/replay; Nomenklatura independently contributes durable POSITIVE/NEGATIVE/UNSURE reviewer judgements plus remove/explode correction of mistaken clusters; controlled writeback systems add governed source correction.
- Score: N4 M4 A3 C5 X5 = **1200**.
- Status: BUILD / BENCHMARK.
- Commercial implication: potentially reusable control plane underneath procurement, AP, CRM, freight and public-data products.
- Search next: stop broad resolver hunting; benchmark Nomenklatura-style negative knowledge/reversible clustering feeding Canon-style promoted-version replay, including aliases, mergers, splits, corrections and noncanonical clusters.

### RAD-004 — Negative-control infrastructure assurance
- Thesis: proof systems that only pass positive tests are insufficient; intentionally wrong states are becoming part of the acceptance standard.
- Signals: restore-drill wrong-target/archive-gap fixtures; recovery-proof portfolio explicitly requires test-the-test negatives.
- Score: N5 M4 A3 C5 X4 = **1200**.
- Status: BUILD.
- Commercial implication: creates a stronger assurance product than “backup succeeded” dashboards.
- Search next: negative-control patterns in cybersecurity, industrial QA, data pipelines, finance and scientific instrumentation.

### RAD-005 — Prospective prediction ledgers
- Thesis: high-stakes forecasting products need append-only future calls and later resolution, not only retrospective backtests.
- Signals: interconnection-queue prediction registry; strong system-wide emphasis on frozen truth before output.
- Score: N5 M3 A3 C5 X5 = **1125**.
- Status: WATCH / BUILD CORE.
- Commercial implication: can become a credibility moat for decision products where hindsight leakage is common.
- Search next: prediction registries, model/version freezing, resolution deadlines and auditable calibration.

### RAD-006 — Authority-aware money assurance
- Thesis: deterministic “expected vs actual” engines are converging across freight, AP, commissions, telecom, utilities, RMAs and subscription close.
- Signals: multiple independent verticals now share the same pattern: authority snapshot -> expected state -> actual state -> exception -> outcome settlement.
- Score: N3 M5 A4 C5 X5 = **1500**.
- Status: EXPAND.
- Commercial implication: likely a reusable assurance platform family rather than isolated vertical products.
- Search next: verticals with expensive reconciliation, authoritative rate/entitlement sources and measurable closed-loop outcomes.

### RAD-007 — Customer-configuration-derived digital twins / virtual commissioning
- Thesis: customer-authorized controller/configuration or frozen protocol profiles can create software-only acceptance environments before physical hardware/plant access.
- Signals: L5K-derived virtual PLC with namespace/type fidelity; independent SECS/GEM host+equipment state machine over HSMS/TCP with communication/control state, alarms/events/remote commands/spooling/error behavior; protocol regression/pre-FAT opportunities.
- Score: N4 M4 A3 C5 X4 = **960**.
- Status: BENCHMARK.
- Commercial implication: potentially shortens commissioning and integration cycles with clear engineering ROI across controls and semiconductor equipment integration.
- Search next: configuration/profile importers that preserve types, topology, failure states and protocol behavior; require independent endpoint comparison and do not equate implementation agreement with standards conformance.

### RAD-008 — Machine-readable regulatory/source authority
- Thesis: official schemas, rule corpora and versioned public-source pipelines enable deterministic decision support that generic web/RAG systems cannot safely provide.
- Signals: FAR DITA, USAspending/DATA Act schemas, solicitation packet/history acquisition, structured invoice rule packs, plus an independent procurement implementation showing deterministic version hydration/diffs, idempotent reruns and explicit source/history failure states.
- Score: N3 M5 A4 C5 X4 = **1200**.
- Status: EXPAND.
- Commercial implication: strong moat where stale, superseded or misapplied rules/records create expensive decisions.
- Search next: official machine-readable rule/source systems with effective-date/supersession semantics and deterministic history; use cross-jurisdiction implementations only as architecture patterns unless their authority applies directly.

### RAD-009 — Governed autonomous experimentation
- Thesis: scientific automation is shifting from optimizer-only loops toward explicit permission, validation, recovery, stop and provenance policies.
- Signals: HELIOS-style campaign governance combined with instrument normalization/orchestration/provenance.
- Score: N5 M3 A3 C4 X4 = **720**.
- Status: WATCH / SHADOW-TEST.
- Commercial implication: likely enterprise value in reducing invalid actions and improving auditability, but integration/sales cycles are heavy.
- Search next: independent lab-control policies, shadow-mode results and replayable experiment governance.

### RAD-010 — Installed-base scientific operations adapters
- Thesis: near-term lab-automation value is increasingly concentrated in preserving incumbent LIMS/instruments while adding programmable workflow state, vendor-format normalization, device control and evidence/provenance, rather than replacing the entire laboratory operating stack.
- Signals: independent mature surfaces now span SLIMS integration, Clarity workflow automation, official Illumina run-metric parsing, cross-vendor analytical normalization, deterministic timed benches, scan/device plugin ecosystems, EPICS/Tango async control and provenance infrastructure. `AD-SDL/MADSci` adds source/test evidence that lost physical-action responses can be reconciled against the same action identity and unresolved outcomes can become `UNKNOWN`; its generic retry loophole independently shows that recovery authority must span all later retry/resume surfaces. Official `Opentrons/opentrons@03b991fb...` adds an external vendor run/action/command state plane that survives Robot Server restart, while exposing a second hard boundary: positive persisted state is stronger evidence of APPLIED than missing action history is evidence of NOT_APPLIED because play/resume can begin before the action row is stored.
- Score: N3 M5 A4 C5 X4 = **1200**.
- Status: BUILD / BENCHMARK.
- Commercial implication: service-first “automate one installed workflow/bench without replacing the system of record” may reach revenue faster and with less organizational resistance than a new lab OS; an ambiguity/retry acceptance pack can be a concrete commissioning wedge.
- Search next: stop generic laboratory frameworks unless they add a missing installed-base adapter or hard operational invariant; prioritize exact vendor/workflow handoffs, migration compatibility, failure recovery, single-actuation authority and measurable analyst/technician time or failed-run reduction.
- Next evidence needed: a synthetic cross-system acceptance fixture including actuated-but-response-lost -> external vendor run/status readback -> APPLIED / NOT_APPLIED / UNKNOWN -> retry/restart gate, with an explicit crash in the side-effect-before-action-persistence window, followed by one explicitly authorized customer workflow proving deployment effort and operational value.

## Radar operating rule
A radar category should move toward BUILD only when:
1. at least two independent technical signals exist;
2. implementation evidence is stronger than marketing;
3. a concrete buyer/problem exists;
4. a falsifiable experiment is defined.

Demote categories when adoption stalls, independent evidence fails or a simpler commodity alternative wins.

<!-- INTEGRATOR-R11-2026-09-20T0856-0400 -->
## Evidence delta — scores unchanged
- **RAD-001 Proof-carrying operational software:** strengthened by MiniGraf bitemporal replay, DIGIT contract-bounded measurement and official SAM version-history semantics. The signal is broader evidence for explicit temporal/authority state, not a reason to inflate the numeric emergence score without adoption evidence.
- **RAD-006 Authority-aware money assurance:** strengthened by independent convergence in freight settlement acceptance (`edi-reconciliation-tool`), AP source-health failure semantics, public-works quantity ceilings and `chase-sets` provider-operation/receivable handling. The recurring primitive is authority → unique claim/state → unresolved-safe transition → independently evidenced outcome.
- **Remote-sensed outage outcomes:** OWL-I is a fresh technical signal for higher-resolution grid-service outcome evidence, but rights are unresolved and the method is EAGLE-I-calibrated; no new radar category/score is created until independent held-out use and reuse terms are established.

<!-- INTEGRATOR-R12-2026-09-20T0946-0400 -->
## Radar evidence delta — 2026-09-20 09:46 ET
- **Authority-aware money assurance:** strengthened, no numeric score change. Independent findings now cover source-observation receipts, immutable/one-use settlement allocation, provider ambiguity and later ACH return/reversal. The emerging primitive is `authority -> explicit unknown -> one-use state transition -> external readback -> counter-event` rather than a terminal success bit.
- **Proof-carrying recovery software:** strengthened, no numeric score change. Mukuroji extends the pattern to DynamoDB/S3 semantic state and approval-bound cleanup; nearai adds verifier-self-test evidence, making “prove the proof system fails when it should” a material maturity signal.
- **Installed-base scientific operations adapters:** strengthened, no numeric score change. `scilifelab_epps` independently demonstrates preserve-the-LIMS + bridge-the-instrument/run-metrics architecture; BO-MCP adds experiment-identity/idempotency evidence in a separate self-driving-lab lineage.
- **Temporal machine-readable public authority:** strengthened, no numeric score change. DHS APFS source-native history and SAM operational incident intervals show that event time, observation time and source-health time all matter for defensible public-data conclusions.
- **Outcome-priced grid decision intelligence:** strengthened, no numeric score change. USECPO adds an event-aligned outage outcome benchmark and interruption-cost tooling supplies a separately governed consequence layer, but EAGLE-I circularity and buyer-grade asset truth remain unresolved.

<!-- INTEGRATOR-R13-2026-09-20T1353-0400 -->
## Radar evidence delta — scores unchanged
- **RAD-001 Proof-carrying operational software:** `az-said/Interlock@822ec546...` adds checked-in test-mode evidence that a governed effect can survive real process death, recover under one identity, and later be consumed once by the provider's own billing engine. The repository's own handwritten baseline ties the money outcome, so the signal is stronger reusable proof/recovery packaging rather than unique correctness.
- **RAD-006 Authority-aware money assurance:** provider-object convergence and provider-accounting application are now better separated. Interlock demonstrates the application layer; independent bank/payout observation remains the required realized-money boundary. No score change without buyer/outcome evidence.
- **RAD-010 Installed-base scientific operations adapters:** official Opentrons run/action/command persistence independently strengthens external device-state readback and simultaneously exposes an important asymmetric evidence rule: persisted action/status can prove APPLIED more strongly than missing history can prove NOT_APPLIED. No numeric score change until the ambiguity matrix and authorized installed-device outcome run.

<!-- INTEGRATOR-R14-2026-09-20T15XX-0400 -->
## Radar evidence delta — scores unchanged
- **RAD-001 Proof-carrying operational software:** strengthened by `prathamesh-git9/effect-broker@eb273640...`, which demonstrates durable pre-dispatch reservation, explicit OUTCOME_UNKNOWN, production-path lease recovery and authoritative readback after a literal target-commit/local-receipt crash. `auths-dev/auths-proof@34fa1f33...` independently shows a second viable receipt architecture based on a stable pre-dispatch business reference embedded in the provider mutation and searchable after restart. This broadens the design space without changing adoption evidence.
- **RAD-006 Authority-aware money assurance:** strengthened by EruoFood's immutable event-time payable authority plus non-retryable UNKNOWN and compensating re-open, and by the separation of crash-safety from provider payout terminality in the Flames-up shadow result. The reusable pattern is now `historical authority -> stable effect identity -> UNKNOWN-safe reservation -> target readback -> provider accounting/finality -> external counter-event`.
- **RAD-008 Machine-readable regulatory/source authority:** live SAM verification shows that action membership, observation-time source state and object identity are separate dimensions. A latest deletion-inclusive manifest is not historical packet truth; same filename is not same resource. No numeric score change because this is stronger evidence architecture, not adoption acceleration.
- **RAD-007 Virtual commissioning / protocol acceptance:** the Dreamine↔secsgem analysis shows why the measurement harness itself must be independently specified: identical endpoint S9F7 behavior can produce different native-client T3 outcomes because requester correlation policy differs. Neutral raw-HSMS observation is now part of the acceptance architecture.
- **RAD-010 Installed-base scientific operations adapters:** strengthened by the SiLA pre-confirmation receipt boundary. Client workflow intent and server execution UUID may not coincide, and a lost confirmation can leave a potentially started command without a durable external execution receipt. The commercializable acceptance pattern increasingly centers on durable external effect identity and ambiguity recovery, not just adapter breadth.

<!-- INTEGRATOR-R15-2026-09-20T18XX-0400 -->
## Radar evidence delta — scores unchanged
- **RAD-001 Proof-carrying operational software:** independently strengthened by the convergence of TUF/Uptane currentness, in-toto functionary/threshold obligations, Sigstore exact-predicate verification, Ampel signer/applicability/result semantics and the current in-toto SVR result envelope. The important shift is from “signed evidence” to **admissible proof**: current, role-authorized, type-correct, threshold-complete, semantically applicable and durably packaged.
- **RAD-004 Negative-control infrastructure assurance:** strengthened by a recurring signed-but-wrong-predicate false-green class across adjacent verification surfaces and by the synthetic 8-case proof-admission fixture. Wrong type, SKIP-as-exit-0 and threshold shortfall now join rollback/snapshot/wrong-role as permanent verifier negatives. No score change because this is stronger assurance evidence, not demonstrated adoption acceleration.
- **Commercial implication:** a Proof Admission Gateway can become a reusable assurance layer across recovery, compliance, consequential financial actions and regulated evidence workflows, but buyer adoption/outcome evidence is still absent; do not convert technical convergence into a market-growth claim.