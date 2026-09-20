# Freight Recovery v15.8 — Canonical Release Manifest

Release checkpoint: **v15.8-governance-diligence-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Canonical v15.8 governance/diligence merge commit: `361061b380d98a69b34f362d4cfd9c4f526ccba2`
- Governance/diligence pull request: **#29**
- Earlier Freight lineage retained from v15–v15.7.
- Repository `main` may continue to advance independently as hunters/integrators commit; the Freight merge commit above is the canonical v15.8 control checkpoint.

## Verified CI checkpoints

### Freight Commercial Contracts
- PR #29 final run: `35528127691`
- Result: **success**
- Final Freight suite included **141 tests** after the rights-evidence edge-case correction, plus:
  - controlled-pilot rights gate;
  - controlled-pilot rights-evidence gate;
  - canonical Freight gap gate;
  - Data Readiness fixture;
  - full synthetic commercial rehearsal;
  - deterministic release provenance generation/verification;
  - component inventory generation;
  - deterministic CycloneDX SBOM generation/verification;
  - unsigned DSSE attestation generation/verification;
  - deterministic diligence ZIP generation/verification.

### Technology Intelligence System
- PR #29 final run: `35528127720`
- Result: **success**
- Pull-request execution ran the **read-only validate job only**.
- All registry, provenance-debt, query-family, graph, data-quality, candidate-learning, outcome-attribution, objective, report, adaptive-policy, measurement-plan/campaign, surface-yield and validation steps passed.
- The write-capable persistence job did not run on the pull request.

## Research-model supply-chain state

The Technology Intelligence workflow now:
- pins `actions/checkout` to `11d5960a326750d5838078e36cf38b85af677262`;
- pins `actions/setup-python` to `a26af69be951a213d495a4c3e4e4022e16d87065`;
- grants `contents:read` to normal validation;
- grants `contents:write` only to a separate main-only persistence job after validation;
- uses workflow concurrency and explicit timeouts;
- refreshes main with `git pull --ff-only` before generated-state persistence;
- remains covered by Freight release provenance and CI regression tests.

This reduces the chance that the research system's own supply chain or token scope silently weakens Freight's evidence model.

## Current Freight control plane

### Commercial / proof
- `freight/BUSINESS_MODEL.md`
- `freight/COMMERCIAL_QUALIFICATION.md`
- `freight/COMMERCIAL_LEARNING.md`
- `freight/DATA_READINESS_DIAGNOSTIC.md`
- `freight/PILOT_PROTOCOL.md`
- `freight/PILOT_DATA_ROOM.md`
- `freight/PILOT_REPORT_TEMPLATE.md`
- `freight/contracts.py`
- `freight/settlement_store.py`
- `freight/pilot_package.py`
- `freight/pilot_reporting.py`

### Data / audit / recovery evidence
- `freight/data_lifecycle.py`
- `freight/audit_ledger.py`
- `freight/audit_store.py`
- `freight/backup_restore.py`
- `freight/PERSISTENT_AUDIT_AND_BACKUP.md`

### Release / diligence
- `freight/release_provenance.py`
- `freight/sbom.py`
- `freight/release_attestation.py`
- `freight/diligence_bundle.py`
- `freight/BUYER_DILIGENCE_BUNDLE.md`
- `freight/RELEASE_AND_SECURITY_GATE.md`

### Rights evidence
- `freight/COMPONENT_RIGHTS_REGISTRY.json`
- `freight/RIGHTS_EVIDENCE_MANIFEST.json`
- `freight/rights_evidence.py`
- `freight/RIGHTS_DILIGENCE.md`

### Incident response
- `freight/incident_response.py`
- `freight/INCIDENT_RESPONSE.md`
- `freight/INCIDENT_TABLETOP_TEMPLATE.md`

### Research authorization / learning
- `freight/GAP_REGISTER.json`
- `freight/gap_registry.py`
- `freight/outcome_adapter.py`
- `intelligence/domain_search_policies.json`

## Rights state

The repository now prevents separately licensed rights from being promoted to resolved hosted/SaaS/assignment/sublicensing/change-of-control claims without:
1. a controlled diligence-room evidence reference;
2. `ATTACHED_VERIFIED` status; and
3. a lowercase SHA-256 for the executed evidence object.

Current evidence state:
- **Trenova:** user-asserted separate commercial license for the pinned revision remains recorded; executed permission evidence is **NOT_ATTACHED** in this repository; hosted/SaaS/assignment/sublicensing/change-of-control remain unresolved.
- **Opstrax:** user-asserted separate commercial permission for the pinned revision remains recorded; executed permission evidence is **NOT_ATTACHED** in this repository; hosted/SaaS/assignment/sublicensing/change-of-control remain unresolved.
- Permissive public-license components such as MIT/Apache-2.0 do not become artificially dependent on separately asserted evidence when the public license independently supplies the relevant code-use permission.

The pilot evidence gate passes with explicit warnings for missing executed evidence; the annual-diligence gate intentionally remains blocked while required scope is unresolved.

This is an operational consistency control, not a legal opinion.

## Incident-response state

The repository now contains a fail-closed incident decision model and runbook:
- OPEN / CONTAINED / RECOVERED / CLOSED states;
- UNKNOWN / NO_EVIDENCE / SUSPECTED / CONFIRMED exposure states;
- containment required before contained/recovered/closed status;
- verified recovery required before recovered/closed status;
- CLOSED cannot leave exposure UNKNOWN;
- SEV1/SEV2 closure requires preserved SHA-256 evidence references;
- any external notification requires explicit human authorization and a recorded basis;
- incident/customer secrets and privileged forensic detail must not enter the technology-intelligence learning ledger.

This is **not** proof of a deployed SOC/IR program, staffed on-call rotation, buyer-specific notification procedure or completed tabletop against the production environment.

## Commercial state

Freight Recovery v15.8 is **commercially specified, machine-gated, internally rehearsed, settlement-persistence hardened, audit/backup reference-hardened, deterministic-diligence packaged, rights-evidence gated, incident-response documented and research-CI supply-chain hardened; EXP-001 remains externally unproven**.

Structured external Freight evidence remains:
- directly evidenced Freight revenue: **$0**
- directly evidenced Freight customer value: **$0**
- paid diagnostic/pilot/annual conversion: **none recorded**
- Freight `ACTIVE_SEARCH` gaps: **0**

No v15.8 internal engineering result changes those external facts.

## Current internal proof boundary

The repository now demonstrates:
- buyer/BU/shipment scoped proof objects;
- blind population/truth/incumbent sequencing;
- fail-closed REVIEW/$0 semantics;
- persistent exact-cents settlement allocation and reversal handling;
- deterministic buyer reporting;
- fail-closed pre-parser guards;
- source/lifecycle observation semantics;
- application-level tamper-evident audit chains;
- immutable-trigger SQLite reference audit persistence;
- semantic audit+settlement backup/restore verification;
- deterministic release provenance;
- pinned component inventory;
- partial CycloneDX 1.6-shaped SBOM;
- unsigned DSSE/in-toto-shaped attestation payload;
- deterministic zero-customer-data diligence ZIP;
- rights-evidence promotion controls;
- documented incident-response closure/notification rules;
- pinned/least-privilege Technology Intelligence validation workflow.

## Remaining external / deployment blockers

1. first authorized real buyer population through actual later settlement;
2. actual executed Trenova/Opstrax permission documents attached/verified in the controlled diligence room and required scope resolved;
3. production DB/object-store/API cross-tenant authorization evidence;
4. production parser sandbox / CPU-memory-time-network isolation evidence;
5. deployed audit-store service authorization + external immutability/WORM/alerting if required;
6. external signing identity/trusted timestamp and any buyer-required full transitive deployment SBOM;
7. deployed backup scheduling/retention/geographic redundancy with measured RPO/RTO;
8. buyer-specific security questionnaire, encryption/configuration and retention terms;
9. deployed incident contact tree/on-call/alerting plus completed tabletop or production incident exercise evidence;
10. any external certification/attestation a buyer requires.

## Engineering / search freeze

Do not cut another Freight version for repository novelty alone.

Reopen Freight research or engineering only through:
- an explicitly activated mapped Freight search gap;
- an EXP-001/paying-customer named capability failure;
- a security or rights diligence blocker;
- a reproduced independent money-bearing disagreement;
- a measured reviewer bottleneck that can be reduced without increasing false-dollar risk.

The global adaptive policy cannot override the Freight domain gate.

## Next canonical milestone

**Paid diagnostic/pilot → externally evidenced engagement outcome → frozen real population → challenger-only validated finding or defensible clean result → buyer-approved action → issued credit/refund/remittance → unambiguous realized settlement → buyer-cohort learning record → annual assurance conversion.**

That external chain remains more valuable than additional unsponsored Freight architecture.
