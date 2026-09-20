# Freight Recovery v15.11 — Canonical Release Manifest

Release checkpoint: **v15.11-pilot-charter-scope-freeze-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Canonical v15.11 product merge commit: `86a58b689df2d1a4288cd165c5494d76c9b928c5`
- Pilot Charter pull request: **#53**
- v15.11 tested branch head: `6212b95d06847109cedebdf1611e77fbd62bef33`
- Earlier Freight lineage retained from v15–v15.10.
- Repository `main` may continue to advance independently as hunters/integrators commit; the merge commit above is the canonical v15.11 product checkpoint.

## Verified CI checkpoints

### Freight Commercial Contracts — v15.11
- Tested branch run: `35540586715`
- Result: **success**
- Verified test counts:
  - hunter/model contracts: **18 passed**
  - Freight contracts: **213 passed**
- Successful post-test gates included:
  - controlled-pilot rights + rights-evidence gates;
  - deployment-security evidence validation;
  - canonical Freight gap gate;
  - Data Readiness fixture;
  - current Netlify customer-data route remains **BLOCKED**;
  - deterministic Pilot Launch Brief generation;
  - deterministic buyer-safe Pilot Activation Packet generation;
  - deterministic **PRELAUNCH_ACCEPTED** Pilot Charter generation with `customer_data_authorized=false`;
  - `external_action_authorized=false` preserved by the Charter;
  - separate-environment evidence remains **CONDITIONAL** until verified;
  - full synthetic commercial rehearsal;
  - deterministic release provenance + component inventory;
  - CycloneDX SBOM generation/verification;
  - unsigned DSSE attestation generation/verification;
  - deterministic zero-customer-data diligence ZIP generation/verification.

### Technology Intelligence System
- v15.8 governance run retained: `35528127720`
- Result: **success**
- Read-only validation / main-only persistence boundary remains in force.

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
- `freight/PILOT_LAUNCH_GATE.md`
- `freight/PILOT_LAUNCH_BRIEF.md`
- `freight/launch_brief.py`
- `freight/PILOT_ACTIVATION_PACKET.md`
- `freight/pilot_activation_packet.py`
- `freight/PILOT_CHARTER.md`
- `freight/pilot_charter.py`
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE.md`
- `freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json`
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

## Deployment security evidence addendum — 2026-09-20

Live connected-provider inventory identified one Freight deployment:
- Netlify project: `freightleak-audit`
- Site ID: `4884fe92-34bc-411c-8fc4-202744c7e161`
- Netlify SSO team login required for all visitors: **CONFIG PROVEN**
- Netlify Forms: **0**
- Netlify environment variables: **0**
- Team members: **1**
- Team MFA enforcement: **not enforced**

No Freight backend/data plane was discovered in Vercel, Render, Floot, Replit,
AppDeploy, or Supabase.

Therefore:
- cross-tenant isolation remains **UNPROVEN** because no multi-tenant Freight data plane was available for dual-tenant negative testing;
- parser sandboxing remains **UNPROVEN** because no production Freight parser runtime was discovered;
- a deployment-specific Netlify incident tabletop was completed with outcome **PASS WITH MATERIAL GAPS**;
- Netlify team MFA is an open **P0 before confidential customer data** item.

Canonical evidence:
- `freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json`
- `freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.md`
- `freight/INCIDENT_TABLETOP_2026-09-20.md`

This addendum is deployment evidence, not a security certification.

Deployment evidence freshness:
- collected: **2026-09-20**
- valid through: **2026-09-27**
- recollect earlier after relevant access/deployment/data-plane/parser changes
- expiry blocks the Netlify route only; it does not invalidate an independently
  verified separate environment.

### Final pilot launch authorization

`freight/pilot_launch_gate.py` now composes buyer/data readiness, pilot rights
operability, rights-evidence consistency and deployment-security evidence.

Current machine classification:
- current Netlify customer-data route: **BLOCKED**;
- separate controlled/manual environment without its own verified evidence: **CONDITIONAL**;
- current Netlify deployment: protected demo/control shell only for customer-data purposes.

A buyer/data readiness result of READY is therefore necessary but not sufficient
to accept confidential customer data.

The manual route no longer trusts an operator-supplied boolean. It requires a structured VERIFIED separate-environment manifest with SHA-256 evidence receipts, a configuration fingerprint, verifier role/date metadata and an unexpired <=90-day validity window. The repository currently contains only a DRAFT template, so that route remains CONDITIONAL.

## Actionable launch workflow

v15.9 preserves `freight/pilot_launch_gate.py` as the authorization source and adds a separate deterministic operator/buyer layer in `freight/launch_brief.py`.

The Launch Brief:
- converts BLOCKED / CONDITIONAL codes into P0/P1/P2 remediation actions;
- assigns an explicit owner;
- states the exact source evidence required for closure;
- states what route/control the closure unlocks;
- uses explicit remediation ordering so immediate access-control fixes precede deeper infrastructure work;
- gives unknown future blocker codes an `UNMAPPED_REVIEW` action instead of silently dropping them;
- emits a deterministic SHA-256 brief hash;
- cannot override or mutate the launch decision.

Current known Netlify-route remediation begins with:
1. enforce Netlify team MFA;
2. identify the actual customer data plane;
3. prove tenant isolation if multi-tenant use is required;
4. prove parser sandbox boundaries if parser use is required.

A remediation item closes only when its underlying evidence changes and the machine launch gate is rerun.

## Buyer activation handoff

v15.10 adds a deterministic buyer-safe `Pilot Activation Packet` above the readiness, launch-gate and launch-brief layers.

The packet binds:
- readiness status + score;
- selected published offer and buyer-facing price band;
- launch status/route;
- launch warnings and prioritized remediation actions;
- data-room requests split into **NOW / CONDITIONAL / LATER_OUTCOME**;
- buyer responsibilities;
- Freight Recovery responsibilities;
- blind-pilot stages;
- the four separate buyer-report totals;
- commercial integrity invariants;
- a deterministic SHA-256 activation hash.

The packet rejects inconsistent readiness/launch-decision inputs and intentionally excludes internal loaded-hourly-cost, analyst-hour-budget and target-margin assumptions.

For a READY buyer, the current published offer remains:
- Blind Freight Audit Acceptance Test: **$15,000–$25,000 fixed**
- target analysis/report turnaround: **10–15 business days after complete inputs**

For a non-ready/conditional buyer, the packet routes to:
- Data Readiness / Authority Diagnostic: **$5,000–$7,500 fixed**

Settlement evidence is requested as **LATER_OUTCOME** evidence rather than being misrepresented as immediate savings proof.

Editing the packet cannot authorize launch; only new underlying evidence followed by a rerun of the machine Pilot Launch Gate can do that.

## Pilot Charter scope freeze

v15.11 adds a deterministic Pilot Charter above the buyer-safe Activation Packet.

The Charter:
- recomputes and verifies the Activation Packet SHA-256 before accepting scope;
- binds the exact engagement ID, buyer/business unit, population rule, source-date range, carrier scope, mode scope and fixed fee;
- requires the fixed fee to remain inside the published Activation Packet price band;
- records buyer truth-owner, buyer action-approver and Freight engagement-owner roles;
- requires explicit acknowledgments of scope, blind protocol, separate report totals and no guaranteed recovery;
- keeps Freight's no-external-action-without-buyer-approval acknowledgment explicit;
- emits its own deterministic SHA-256 charter hash.

Charter states are intentionally separate:
1. `PENDING_ACKNOWLEDGMENT` — one or more acknowledgments are missing.
2. `PRELAUNCH_ACCEPTED` — scope is acknowledged, but the machine launch decision is still BLOCKED or CONDITIONAL.
3. `KICKOFF_AUTHORIZED` — all acknowledgments are present **and** the Activation Packet's machine launch status is READY.

Only `KICKOFF_AUTHORIZED` sets `customer_data_authorized=true`.

The Charter never authorizes carrier/vendor contact, disputes or money-moving action. `external_action_authorized` remains false and the policy is `SEPARATE_BUYER_APPROVAL_REQUIRED`.

Current Netlify route behavior is therefore fail-closed: the CI fixture produces `PRELAUNCH_ACCEPTED`, not kickoff authorization.

## Commercial state

Freight Recovery v15.11 is **commercially specified, machine-gated, internally rehearsed, settlement-persistence hardened, deployment-aware, deterministic-diligence packaged, rights-evidence gated, incident-response documented, research-CI supply-chain hardened, operator-actionable through a deterministic launch-remediation brief, buyer-handoff-ready through a deterministic activation packet, and protected against sales-to-delivery scope drift through a machine-checkable Pilot Charter; EXP-001 remains externally unproven**.

Structured external Freight evidence remains:
- directly evidenced Freight revenue: **$0**
- directly evidenced Freight customer value: **$0**
- paid diagnostic/pilot/annual conversion: **none recorded**
- Freight `ACTIVE_SEARCH` gaps: **0**

No v15.11 internal engineering result changes those external facts.

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
3. production DB/object-store/API cross-tenant authorization evidence once a real Freight multi-tenant data plane exists;
4. production parser sandbox / CPU-memory-time-network/credential isolation evidence once a real Freight parser runtime exists;
5. deployed audit-store service authorization + external immutability/WORM/alerting if required;
6. external signing identity/trusted timestamp and any buyer-required full transitive deployment SBOM;
7. deployed backup scheduling/retention/geographic redundancy with measured RPO/RTO;
8. Netlify team MFA enforcement before confidential buyer data, plus buyer-specific security questionnaire, encryption/configuration and retention terms;
9. deployed incident contact tree/on-call/alerting plus live-environment incident exercise evidence; a Netlify-specific tabletop is now recorded;
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
