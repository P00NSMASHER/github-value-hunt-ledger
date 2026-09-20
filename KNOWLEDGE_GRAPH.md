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

### Lab Automation
- Benchling-Open-Source/allotropy -> IMPLEMENTS CAP-013.
- CAP-013 -> ENABLES Installed-Base Lab Automation / Governed Campaign Shadow Audit -> TESTED_BY EXP-007.

### Industrial Pre-FAT
- Gaskony-Ignition/module-plc-emulator -> IMPLEMENTS CAP-014.
- CAP-014 -> ENABLES Industrial Pre-FAT / Virtual Commissioning -> TESTED_BY EXP-008.

### Prediction Credibility
- owgreen-dev/grid-crunch -> IMPLEMENTS CAP-015.
- savabs/queue_attrition -> STRENGTHENS CAP-015.
- CAP-015 -> ENABLES Queue Materialization Intelligence.

### Cross-vertical Close Assurance
- CAP-006 + CAP-016 -> ENABLES Money-State Integrity / Close Assurance -> TESTED_BY EXP-010.

## Graph maintenance rule
Every MASTER promotion must answer:
1. Which CAP node does it implement, strengthen or challenge?
2. Which TECH radar category does it support or contradict?
3. Which OPP becomes stronger or weaker?
4. Which EXP should change because of it?

If the answer is none, the finding is not yet integrated into the value system.
