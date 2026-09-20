# Freight Recovery v15 — Value-Maximization Roadmap

Updated: 2026-09-20

## North-star milestone

The first milestone that materially changes the business is:

**paid blind pilot -> challenger-only validated finding -> buyer-approved dispute/action -> issued credit/refund/remittance -> unambiguous settlement -> recovery certificate -> annual assurance contract**

Everything below is prioritized by how directly it moves toward that chain.

## Current checkpoint — v15.8 candidate

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
- deterministic zero-customer-data buyer/acquirer diligence ZIP with per-entry checksums.

The global outcome loop now contains one Freight **PARTIAL technical-only** record with **$0 revenue and $0 customer value**. Synthetic test dollars are not treated as market evidence.

Live adaptive policy now confirms **Freight search authorized = no**, **active search gaps = none**, and Freight-exclusive **CAP-003/CAP-004/CAP-005** are suppressed from generic capability-gap priority.

Commercial repricing remains locked to the existing priors until direct external evidence reaches the v15.5 calibration threshold: **5 unique buyer cohorts, 5 paid engagements, and margin evidence from 5 unique buyers**. One customer cannot unlock repricing by generating repeated engagements.

v15.6 Freight CI run `35524672964` passed the full Freight suite, controlled-pilot rights gate, gap gate, readiness fixture, synthetic rehearsal, deterministic provenance verification and component-inventory generation.

v15.7 Freight CI run `35525286692` passed the full Freight suite plus deterministic provenance, CycloneDX SBOM and unsigned DSSE generation/verification.

**Internal engineering freeze:** no new freight subsystem, UI, parser, rating layer, or repository hunt is justified until EXP-001, a paying customer, security diligence, or rights diligence exposes a named gap.

## Next 24 hours — make the asset diligence-ready

### P0
1. **DONE:** v15 through v15.7 commercialization, proof, adaptive-authorization, commercial-learning, pilot-security, lifecycle/audit and supply-chain diligence PRs merged after CI.
2. **DONE:** canonical Freight Recovery v15.7 release identity recorded in `freight/RELEASE_MANIFEST.md`.
3. **DONE internally:** deterministic control provenance, component inventory, partial CycloneDX 1.6-shaped SBOM and unsigned in-toto/DSSE-shaped attestation are generated/verified in CI. **OPEN externally:** approved signing identity/trusted timestamp and any buyer-required complete transitive deployment SBOM.
4. Complete the missing rights-document evidence checklist for Trenova/Opstrax and any non-permissive runtime component.
5. **DONE:** full synthetic readiness → fixed-fee qualification → blind proof → persistent settlement → report rehearsal passed CI and reconciled exactly; this is technical validation only, not external customer proof.

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
5. **PARTIAL DONE:** fail-closed pre-parser negative tests cover PDF/XML/EDI/X12/CSV, archives, size/segment bounds and CSV formula neutralization. OS/container parser sandbox/resource limits remain deployment work.
6. **PARTIAL DONE:** proof/source/package layers now carry buyer+BU scope with cross-scope negative tests. The actual customer data service/database/object-store still requires deployment-specific cross-tenant tests.
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
   - **OPEN externally:** signed provenance/trusted timestamp;
   - **DONE internally:** data-retention/deletion semantics;
   - **OPEN:** incident-response operating plan/evidence;
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
