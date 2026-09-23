# Freight Recovery v15 — Value-Maximization Roadmap

Updated: 2026-09-20

## Unreleased hardening checkpoint - 2026-09-23

This is current working-tree engineering evidence, not a replacement for the
historical v15.14 release/CI record and not external customer proof.

- Freight settlement evidence now requires canonical SHA-256 source digests,
  canonical UTC operation times, and chronology enforcement in both service code
  and direct-SQL triggers. Existing noncanonical stores fail closed on reopen.
- Freight audit timestamps are canonical and nondecreasing; unsafe SQLite busy
  timeout values are rejected instead of reaching PRAGMA construction.
- RecoveryWorks recovered cash now requires verified, hash-bound settlement
  evidence. Lifecycle approvals/authorizations cannot be rewritten after state
  progression, nested proof payloads are immutable, and replay preserves
  authenticated event times.
- RecoveryWorks local compare-and-swap persistence is now serialized across
  processes and private-file permissions are verified on POSIX and Windows.
- All repository workflow actions are immutable SHA pins. Freight deployment
  freshness checks now use the actual UTC workflow date and will fail when the
  September 27 deployment snapshot expires unless it is recollected.
- The composite pilot launch gate now blocks non-permissive runtime components
  until executed permission evidence is verified and commercial use is
  confirmed allowed; a private evidence-manifest input supports legitimate
  clearance without committing executed documents.
- A buyer-shareable controlled synthetic pilot ZIP now packages exact fictional
  inputs, current review/report outputs, machine receipts and a hash manifest.
  Verification replays the scenario byte-for-byte and the public site embeds
  the generated ZIP digest without claiming customer value or external action.
- The repaired Freight Recovery sales site now has an exact five-file public
  build boundary and a SHA-pinned GitHub Pages workflow. Pull requests verify
  it; main can deploy only after an owner configures a verified public inbox
  and enables the GitHub Pages environment. No deployment was performed here.
- These changes are locally verified; a new canonical release identity and
  hosted CI run must be recorded only after the change is committed and CI passes.

## North-star milestone

The first milestone that materially changes the business is:

**paid blind pilot -> challenger-only validated finding -> buyer-approved dispute/action -> issued credit/refund/remittance -> unambiguous settlement -> recovery certificate -> annual assurance contract**

Everything below is prioritized by how directly it moves toward that chain.

## Current checkpoint — v15.14

Internal commercialization controls now completed:
- paid offer/ICP/pricing defined;
- machine-scored Data Readiness gate;
- blind population/truth/incumbent ordering enforced;
- canonical freight gap register with **zero ACTIVE_SEARCH gaps**;
- hunter/integrator freight work bound to registered EXP-001 gaps;
- settlement deduplication/validated caps;
- automatic incumbent-known success-fee exclusion;
- proof-derived buyer pilot metrics/report template;
- fixed-fee qualification and analyst-hour budget with success-fee upside excluded;
- Freight outcome adapter into the global search/outcome learning schema;
- adaptive v2 domain authorization tied to `freight/GAP_REGISTER.json`, preventing generic capability-gap ranking from reopening blocked Freight search;
- buyer-cohort commercial calibration with small-sample anti-overfit gates;
- full synthetic diagnostic→pilot→persistent-settlement→report rehearsal;
- rights-operability registry;
- repository workflow hardening and pinned CI;
- scope-bound buyer/BU/shipment proof objects and sealed incumbent-source chain;
- machine-checkable pilot data-room/package manifests;
- fail-closed PDF/CSV/XML/EDI/X12 pre-parser guard + spreadsheet export neutralization;
- deterministic control-file/component provenance generator;
- buyer-facing security/data-handling statement with explicit non-claims;
- CENSUS/SCOPE/PROOF retention/deletion lifecycle with explicit `DELETE_UNKNOWN` vs `DELETE_CONFIRMED`;
- PRESENT / VERIFIED_EMPTY / UNAVAILABLE source-observation receipts;
- buyer/BU-scoped append-only audit hash chain;
- deterministic CycloneDX 1.6-shaped partial SBOM;
- deterministic unsigned in-toto/DSSE-shaped attestation payload ready for external signing;
- persistent buyer/BU-scoped SQLite audit store with immutable UPDATE/DELETE triggers and serialized appends;
- semantic backup/restore drill across audit + settlement state;
- deterministic zero-customer-data buyer/acquirer diligence ZIP with per-entry checksums;
- evidence-backed rights promotion manifest/validator that prevents hosted/SaaS/assignment/change-of-control claims without verified executed-evidence metadata;
- fail-closed incident-response runbook + closure/notification evidence model + tabletop template;
- Technology Intelligence validation CI pinned to immutable Actions and read-only, with write permission isolated to a main-only persistence job;
- live Netlify deployment evidence addendum for `freightleak-audit`, including SSO config, zero Forms/env-vars, provider inventory, fail-closed tenant/parser status and completed incident tabletop;
- final deployment-aware Pilot Launch Gate that prevents a READY buyer from bypassing deployment/data-handling security;
- structured separate-environment evidence manifest/validator that removes the self-asserted manual-pilot exception;
- deterministic Pilot Launch Brief that converts BLOCKED/CONDITIONAL gate codes into prioritized owners, evidence requests and unlock criteria without overriding the machine gate;
- buyer-safe Pilot Activation Packet that binds readiness, published offer/price band, launch route, remediation, data-room timing, buyer/Freight responsibilities, blind-pilot stages and report semantics into one deterministic handoff without exposing internal cost/margin assumptions;
- machine-checkable Pilot Charter that verifies the activation hash, freezes engagement scope/fee/roles/acknowledgments, and separates PRELAUNCH acceptance from actual KICKOFF authorization;
- Pilot Amendment change-control that keeps accepted Charters immutable, classifies scope/fee/role changes, suspends changed-scope kickoff, and requires a validated replacement Charter before any amendment becomes operative;
- authoritative Engagement State Resolver that walks immutable Charter/Amendment history and outputs the single operative Charter plus customer-data/audit/report/settlement authorization flags;
- revocable External Action Authorization that binds one buyer-approved carrier action to an ACTIVE engagement, CONFIRMED validated findings, exact carrier/recipient/payload hashes, dollar cap and expiry while explicitly excluding money movement, settlement acceptance, account changes, credential use, general contact and automatic execution.

The global outcome loop now contains one Freight **PARTIAL technical-only** record with **$0 revenue and $0 customer value**. Synthetic test dollars are not treated as market evidence.

Live adaptive policy now confirms **Freight search authorized = no**, **active search gaps = none**, and Freight-exclusive **CAP-003/CAP-004/CAP-005** are suppressed from generic capability-gap priority.

Commercial repricing remains locked to the existing priors until direct external evidence reaches the v15.5 calibration threshold: **5 unique buyer cohorts, 5 paid engagements, and margin evidence from 5 unique buyers**. One customer cannot unlock repricing by generating repeated engagements.

v15.6 Freight CI run `35524672964` passed the full Freight suite, controlled-pilot rights gate, gap gate, readiness fixture, synthetic rehearsal, deterministic provenance verification and component-inventory generation.

v15.7 Freight CI run `35525286692` passed the full Freight suite plus deterministic provenance, CycloneDX SBOM and unsigned DSSE generation/verification.

v15.8 governance CI: Freight run `35528127691` and Technology Intelligence run `35528127720` both passed after rights-evidence and least-privilege workflow hardening.

v15.9 Freight CI run `35536987620` passed 18 hunter/model tests + 185 Freight tests and all launch/provenance/SBOM/attestation/diligence steps. The blocked Netlify route now emits a deterministic remediation brief in CI.

v15.10 Freight CI run `35538071323` passed **18 hunter/model tests + 205 Freight tests** and all post-test gates. The buyer-safe activation packet is generated in CI with published price, incumbent-output and LATER_OUTCOME settlement assertions.

v15.11 Freight CI run `35540586715` passed **18 hunter/model tests + 213 Freight tests** and every post-test gate. The current blocked route produces a PRELAUNCH_ACCEPTED Charter with customer-data and external-action authorization both false.

v15.12 Freight CI run `35544056352` passed **18 hunter/model tests + 222 Freight tests** and every post-test gate. Accepted amendments suspend changed-scope kickoff and preserve customer-data/external-action authorization as false until a validated replacement Charter is supplied.

v15.13 Freight CI run `35549203058` passed **18 hunter/model tests + 231 Freight tests** and every post-test gate. The Engagement State Resolver blocks audit/report/settlement processing during accepted-but-unreplaced amendments, and AuditStore initialization is now concurrency-safe under the existing monotonic-chain stress test.

v15.14 Freight CI run `35550422800` passed **18 hunter/model tests + 242 Freight tests** and every existing post-test gate. The External Action Authorization is ACTIVE-only, buyer-role-approved, finding/payload/recipient/dollar-bound, expiring and revocable, while money movement, settlement acceptance, general contact and automatic execution remain false.

Technology Intelligence workflow now separates read-only validation from main-only write persistence and pins checkout/setup-python to immutable SHAs.

Deployment evidence collected 2026-09-20: Netlify SSO-all is configured, but **Netlify team MFA is not enforced**, no Freight multi-tenant backend/data plane was discovered, and no production parser runtime was discovered. Cross-tenant isolation and parser sandboxing therefore remain **unproven**, not passed. The deployment evidence snapshot expires after **2026-09-27** and must be recollected earlier after relevant control/deployment changes.

Current launch classification: **Netlify deployed customer-data pilot = BLOCKED**; **separate controlled environment = CONDITIONAL pending evidence**. The protected Netlify site is a demo/control shell until those gates change.

Launch Brief now converts that classification into an operator-facing remediation plan; unknown future blockers fail safe into UNMAPPED_REVIEW instead of disappearing.

Pilot Activation Packet now removes the remaining handoff friction by combining the selected offer, exact source requests and operating sequence into one buyer-safe artifact with an activation hash.

Pilot Charter now prevents sales-to-delivery scope drift by binding that activation hash to the exact fee, population/date/carrier/mode scope and named operating roles. A blocked/conditional route can be acknowledged but cannot authorize customer-data kickoff.

Pilot Amendment now prevents post-Charter scope drift: material population/date/carrier/mode changes force fresh readiness/launch/activation, fee changes outside the published band force a new commercial activation, and role-only changes still require a replacement Charter and re-acknowledgment.

Engagement State Resolver now prevents downstream workers from guessing which Charter is current. Accepted-but-unreplaced amendments suspend audit/report/settlement processing, while superseded chains resolve deterministically to the latest verified replacement Charter.

External Action Authorization now closes the buyer-approved dispute/action boundary: only an ACTIVE engagement with CONFIRMED validated findings can receive a narrow, hash-bound, expiring and revocable carrier-action approval; creating the approval never sends the action.

The separate/manual route stays **CONDITIONAL** until a VERIFIED environment manifest proves MFA, encryption, scoped access, read-only ingestion, retention/deletion, Netlify data exclusion, and any applicable tenant/parser controls with SHA-256 receipts and a <=90-day evidence-validity window.

**Internal engineering freeze:** no new freight subsystem, UI, parser, rating layer, or repository hunt is justified until EXP-001, a paying customer, security diligence, or rights diligence exposes a named gap.

## Next 24 hours — make the asset diligence-ready

### P0
1. **DONE:** v15 through v15.14 commercialization, proof, adaptive-authorization, commercial-learning, pilot-security, lifecycle/audit, governance/diligence, actionable launch-workflow, buyer-activation, scope-freeze, amendment-control, engagement-state resolution and revocable external-action authorization upgrades merged after CI.
2. **DONE:** canonical Freight Recovery v15.14 release identity recorded in `freight/RELEASE_MANIFEST.md`.
3. **DONE internally:** deterministic control provenance, component inventory, partial CycloneDX 1.6-shaped SBOM and unsigned in-toto/DSSE-shaped attestation are generated/verified in CI. **OPEN externally:** approved signing identity/trusted timestamp and any buyer-required complete transitive deployment SBOM.
4. **DONE internally:** rights evidence manifest + fail-closed promotion validator. **OPEN externally:** attach/verify the actual executed Trenova/Opstrax permission documents and resolve hosted/SaaS/change-of-control scope.
5. **DONE:** full synthetic readiness → fixed-fee qualification → blind proof → persistent settlement → report rehearsal passed CI and reconciled exactly; this is technical validation only, not external customer proof.
6. **DONE internally:** deterministic buyer-shareable synthetic demo and
   public-site publication boundary. **OPEN externally:** verify the business
   inbox, configure repository variables/Pages, merge the reviewed release and
   inspect the resulting public URL.

### Deployment-security actions from live evidence
1. Enable Netlify team MFA before confidential buyer data is accepted.
2. When a real Freight customer data plane is deployed, run two-tenant negative isolation tests and record provider/project IDs.
3. When a production parser runtime is deployed, record/test CPU, memory, timeout, network-egress and credential-isolation controls.
4. Capture an independent unauthenticated black-box SSO/access probe when a capable probe path is available.
5. Recollect the Netlify deployment evidence no later than 2026-09-27, and sooner after relevant access/deployment changes.

### Stop
- no new generic freight repositories;
- no new TMS/UI/rating subsystem;
- no outbound/customer contact unless explicitly approved.

## Next 7 days — make the paid pilot boring to buy

1. **DONE:** Data Readiness Diagnostic is machine-scored with a repeatable delivery specification.
2. **DONE:** proof-derived pilot report template and synthetic sample semantics cover:
   - reviewed discrepancy;
   - validated finding;
   - challenger-only validated;
   - uniquely attributable realized.
3. **DONE:** machine-checkable source/data-room + population/truth + sealed/opened incumbent package chain implemented in `freight/pilot_package.py` and `PILOT_DATA_ROOM.md`.
4. **DONE:** `freight/SECURITY_AND_DATA_HANDLING.md` separates current pilot controls from deployment/security non-claims.
5. **PARTIAL DONE:** fail-closed pre-parser negative tests cover PDF/XML/EDI/X12/CSV, archives, size/segment bounds and CSV formula neutralization. Live deployment evidence found no production Freight parser runtime, so CPU/memory/time/network/credential sandboxing remains unproven deployment work.
6. **PARTIAL DONE:** proof/source/package layers now carry buyer+BU scope with cross-scope negative tests. Live provider inventory found no Freight multi-tenant customer data plane, so actual A-vs-B deployment isolation testing remains unproven and must occur when that data plane exists.
7. Record reviewer hours, invoice count, fixed fee, delivery cost and turnaround in each externally evidenced engagement outcome so buyer-level margin/effort can be calibrated.
8. **ADVANCED internally:** CENSUS/SCOPE/PROOF lifecycle, source receipts, persistent scoped audit reference storage and semantic audit+settlement restore drills are tested. **OPEN externally:** real provider deletion receipts, production audit-service authorization/WORM/alerting, deployed backup schedule/geographic redundancy and measured RPO/RTO.

## Next 30 days — prove willingness to pay and one real outcome

Subject to explicit user approval for outreach/data access:
1. Target only buyers meeting the v15 ICP.
2. Sell the **$5k–$7.5k Data Readiness Diagnostic** first where data quality is uncertain.
3. Sell the **$15k–$25k Blind Freight Audit Acceptance Test** when readiness is already high.
4. Freeze truth before incumbent output in every pilot.
5. Track findings through actual carrier/vendor settlement.
6. Convert one completed pilot into continuous assurance only after the buyer accepts the proof chain.

### 30-day success evidence
- paid pilot/diagnostic signed;
- complete frozen population;
- zero unsupported asserted dollars;
- measured analyst hours and turnaround;
- buyer accepts report semantics;
- at least one validated challenger-only finding or a defensible clean-population result.

## Next 90 days — turn project work into a software business

1. Reach 2–3 paid blind pilots.
2. Obtain at least one uniquely attributable realized recovery.
3. Convert at least one buyer to **$60k–$150k annual assurance**.
4. Productize only integrations requested by multiple paying customers.
5. Introduce automation only where it reduces reviewer touches without increasing false-dollar risk.
6. Build the minimum enterprise diligence package:
   - **DONE internally:** rights registry + partial SBOM + deterministic diligence ZIP;
   - **OPEN externally:** executed rights evidence, signed provenance/trusted timestamp;
   - **DONE internally:** data-retention/deletion semantics;
   - **DONE internally:** incident-response/breach-decision runbook + machine closure/notification rules + one deployment-specific Netlify tabletop; **OPEN externally:** deployed contact tree/alerting and live-environment incident exercise evidence;
   - **DONE internally:** semantic reference backup/restore proof;
   - **OPEN deployment-specific:** access-control/cross-tenant, backup scheduling/RPO/RTO and production audit-service evidence.
7. Keep success-fee attribution subordinate to the settlement proof engine.

## Priority model

| Priority | Work | Value effect |
| --- | --- | --- |
| P0 | pilot truth/settlement proof | changes technical potential into commercial evidence |
| P0 | rights + release + security diligence | removes buyer/acquirer discount |
| P0 | paid pilot | proves willingness to pay |
| P1 | annual assurance conversion | creates recurring revenue |
| P1 | reduce reviewer touches safely | raises gross margin |
| P1 | repeat customer integrations | improves retention/ACV |
| P2 | broader control-plane product | only after repeatability |
| STOP | broad repository count growth | low marginal value without a named gap |

## Decision rule for new engineering

A proposed feature enters the freight backlog only if it answers **yes** to at least one:
1. Did a paying pilot fail because this capability was missing?
2. Does it reduce a measured manual-review bottleneck while preserving the false-dollar ceiling?
3. Does it unblock a required buyer integration?
4. Does it close a security/rights/diligence gate?
5. Does it improve settlement attribution or proof quality?

If not, defer it.
