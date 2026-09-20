# KNOWLEDGE_GRAPH

Human-readable graph connecting findings to capabilities, technologies, opportunities, experiments and outcomes.

## Node types
- REPO — repository/project/revision
- DATA — dataset/source pipeline
- CAP — reusable capability from CAPABILITIES.md
- TECH — emerging technology category from TECHNOLOGY_RADAR.md
- OPP — business opportunity from OPPORTUNITIES.md
- EXP — falsifiable experiment from EXPERIMENTS.md
- OUT — recorded result from OUTCOMES.md

## Core edge types
IMPLEMENTS, VALIDATES, CHALLENGES, DEPENDS_ON, COMBINES_WITH, ENABLES, TESTED_BY, PRODUCED, INVALIDATES, STRENGTHENS.

## Current high-value graph — 2026-09-20

### Freight Recovery
- kodekinetics79/opstrax-enterprise-build -> IMPLEMENTS CAP-005.
- emoss08/Trenova -> IMPLEMENTS CAP-003 and STRENGTHENS CAP-006.
- sengtha/Kareya-Silo -> IMPLEMENTS CAP-004.
- A-Jatin/freight-ratecon-extraction -> IMPLEMENTS CAP-001 and STRENGTHENS CAP-003.
- OmarFaig/Assay -> IMPLEMENTS CAP-001.
- srthck/trustmesh -> IMPLEMENTS CAP-007.
- CAP-001 + CAP-003 + CAP-004 + CAP-005 + CAP-006 + CAP-007 -> ENABLES Freight Audit Acceptance Test / Recovery -> TESTED_BY EXP-001.

### AP Assurance
- mgilbir/formalis -> IMPLEMENTS CAP-008.
- cmdrvl/canon -> IMPLEMENTS CAP-002.
- CAP-001 + CAP-002 + CAP-007 + CAP-008 + CAP-016 -> ENABLES AP Leakage Assurance -> TESTED_BY EXP-002.

### Commission Assurance
- CAP-002 + CAP-006 + CAP-007 + CAP-016 -> ENABLES Partner / Commission Payout Assurance -> TESTED_BY EXP-003.

### Recovery Proof
- duke5am/pg-restore-drill -> IMPLEMENTS CAP-010.
- open-eid/SiVa -> STRENGTHENS CAP-010.
- srthck/trustmesh -> STRENGTHENS CAP-010.
- CAP-007 + CAP-010 -> ENABLES Recovery Proof SLA -> TESTED_BY EXP-004.

### CaptureBrief
- GSA/srt-fbo-scraper -> IMPLEMENTS CAP-011.
- GSA/GSA-Acquisition-FAR -> IMPLEMENTS CAP-011.
- fedspendingtransparency/usaspending-api -> IMPLEMENTS CAP-011.
- fedspendingtransparency/data-act-broker-backend -> IMPLEMENTS CAP-011.
- CAP-002 + CAP-007 + CAP-011 -> ENABLES CaptureBrief FAR-Deviation Readiness -> TESTED_BY EXP-006.

### Permit Intelligence
- adamleap02/PermitBuild -> IMPLEMENTS CAP-012.
- CAP-002 + CAP-012 -> ENABLES Permit-to-Development Opportunity Intelligence -> TESTED_BY EXP-009.

### Lab Automation / Sequencing Operations
- Benchling-Open-Source/allotropy -> IMPLEMENTS CAP-013.
- SemaphoreSolutions/s4-clarity-lib@ad577fff3a3c4c93f4bb898940a0b45268c7dbe7 -> IMPLEMENTS CAP-017.
- Illumina/interop@015a85ec100c7a770ed0e27ce7fadc6230a38208 -> IMPLEMENTS CAP-017.
- ORNL/Flowcept -> STRENGTHENS CAP-013 and CAP-017 through provenance/evidence lineage.
- labscript-suite/labscript-suite + labscript-devices -> CHALLENGES/STRENGTHENS deterministic scientific execution under the broader lab opportunity without displacing the installed-base integration leaders.
- CAP-013 + CAP-017 -> ENABLES Installed-Base Lab Automation / Sequencing Operations Evidence / Governed Campaign Shadow Audit -> TESTED_BY EXP-007.

### Insurance Subrogation Recovery
- sidnov6/recoupe@60e0e02bec789ab505752dacfecdd76438aacd48 -> IMPLEMENTS a deterministic subrogation workflow/quantum/evaluation substrate but DEPENDS_ON independently authoritative current rule/policy sources before hard-dollar use.
- CAP-001 + CAP-006 + CAP-007 + Recoupe deterministic quantum/workflow -> ENABLES Insurance Subrogation Recovery Diagnostic -> TESTED_BY EXP-011.
- Recoupe illustrative/default jurisdiction rule data -> CHALLENGES the opportunity's authority boundary; unknown/conflicting authority must remain REVIEW/$0 rather than silently default.

### Revenue Decision Assurance
- GiovanniGatti/talos@41fae94f941ea36fccddd395e86cd5662002e3cb -> STRENGTHENS constrained-capacity/booking-horizon policy evaluation.
- Dimitres-Kisimov/revops-optimizer + Talos -> ENABLES a broader shadow-mode Revenue Decision Assurance concept; no production-economic claim is accepted without held-out replay against simple/incumbent baselines.

### Money-State / Payment Integrity
- amrit-kumar/fintechcore@b27a22890e8b5173d2a97be512a198a4564ed425 -> CHALLENGES/STRENGTHENS CAP-016 with append-only ledger, idempotency, settlement and independent reconciliation semantics.
- The Fintechcore test-deferred ADR -> LIMITS its maturity; it remains a reference/challenger until automated invariant/race/refund/reversal/outbox tests exist.
- CAP-006 + CAP-016 -> ENABLES Money-State Integrity / Close Assurance -> TESTED_BY EXP-010.

### Industrial Pre-FAT
- Gaskony-Ignition/module-plc-emulator -> IMPLEMENTS CAP-014.
- CAP-014 -> ENABLES Industrial Pre-FAT / Virtual Commissioning -> TESTED_BY EXP-008.

### Prediction Credibility
- owgreen-dev/grid-crunch -> IMPLEMENTS CAP-015.
- savabs/queue_attrition -> STRENGTHENS CAP-015.
- CAP-015 -> ENABLES Queue Materialization Intelligence.

## Graph maintenance rule
Every MASTER promotion must answer:
1. Which CAP node does it implement, strengthen or challenge?
2. Which TECH radar category does it support or contradict?
3. Which OPP becomes stronger or weaker?
4. Which EXP should change because of it?

If the answer is none, the finding is not yet integrated into the value system.
