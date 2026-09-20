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
- Thesis: identity resolution is shifting from one-off fuzzy matching toward versioned registries with human promotion, correction/split semantics and exact runtime replay.
- Signals: Canon + controlled writeback systems + privacy-preserving challengers.
- Score: N4 M4 A3 C5 X5 = **1200**.
- Status: BUILD / BENCHMARK.
- Commercial implication: potentially reusable control plane underneath procurement, AP, CRM, freight and public-data products.
- Search next: independent implementations with promotion/version semantics, negative matches and rollback.

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
- Thesis: customer-authorized controller/configuration exports can create software-only acceptance environments before physical hardware/plant access.
- Signals: L5K-derived virtual PLC; protocol simulators and pre-FAT opportunities.
- Score: N4 M4 A3 C5 X4 = **960**.
- Status: BENCHMARK.
- Commercial implication: potentially shortens commissioning and integration cycles with clear engineering ROI.
- Search next: configuration importers that preserve types, topology, failure states and protocol behavior.

### RAD-008 — Machine-readable regulatory/source authority
- Thesis: official schemas, rule corpora and versioned government source pipelines enable deterministic decision support that generic web/RAG systems cannot safely provide.
- Signals: FAR DITA, USAspending/DATA Act schemas, solicitation packet/history acquisition, structured invoice rule packs.
- Score: N3 M5 A4 C5 X4 = **1200**.
- Status: EXPAND.
- Commercial implication: strong moat where stale or misapplied rules create expensive decisions.
- Search next: official machine-readable rule sources with effective-date/supersession semantics.

### RAD-009 — Governed autonomous experimentation
- Thesis: scientific automation is shifting from optimizer-only loops toward explicit permission, validation, recovery, stop and provenance policies.
- Signals: HELIOS-style campaign governance combined with instrument normalization/orchestration/provenance.
- Score: N5 M3 A3 C4 X4 = **720**.
- Status: WATCH / SHADOW-TEST.
- Commercial implication: likely enterprise value in reducing invalid actions and improving auditability, but integration/sales cycles are heavy.
- Search next: independent lab-control policies, shadow-mode results and replayable experiment governance.

### RAD-010 — Installed-base scientific operations adapters
- Thesis: near-term lab-automation value is increasingly concentrated in preserving incumbent LIMS/instruments while adding programmable workflow state, vendor-format normalization, device control and evidence/provenance, rather than replacing the entire laboratory operating stack.
- Signals: independent mature surfaces now span SLIMS integration, Clarity workflow automation, official Illumina run-metric parsing, cross-vendor analytical normalization, deterministic timed benches, scan/device plugin ecosystems, EPICS/Tango async control and provenance infrastructure.
- Score: N3 M5 A4 C5 X4 = **1200**.
- Status: BUILD / BENCHMARK.
- Commercial implication: service-first “automate one installed workflow/bench without replacing the system of record” may reach revenue faster and with less organizational resistance than a new lab OS.
- Search next: stop generic laboratory frameworks unless they add a missing installed-base adapter or hard operational invariant; prioritize exact vendor/workflow handoffs, migration compatibility, failure recovery and measurable analyst/technician time or failed-run reduction.
- Next evidence needed: a synthetic cross-system acceptance fixture first, followed by one explicitly authorized customer workflow proving deployment effort and operational value.

## Radar operating rule
A radar category should move toward BUILD only when:
1. at least two independent technical signals exist;
2. implementation evidence is stronger than marketing;
3. a concrete buyer/problem exists;
4. a falsifiable experiment is defined.

Demote categories when adoption stalls, independent evidence fails or a simpler commodity alternative wins.
