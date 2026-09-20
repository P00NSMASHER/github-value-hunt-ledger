# Freight Recovery v15 — Value-Maximization Roadmap

Updated: 2026-09-20

## North-star milestone

The first milestone that materially changes the business is:

**paid blind pilot -> challenger-only validated finding -> buyer-approved dispute/action -> issued credit/refund/remittance -> unambiguous settlement -> recovery certificate -> annual assurance contract**

Everything below is prioritized by how directly it moves toward that chain.

## Current checkpoint — v15.4 candidate

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
- full synthetic diagnostic→pilot→persistent-settlement→report rehearsal;
- rights-operability registry;
- repository workflow hardening and pinned CI.

**Internal engineering freeze:** no new freight subsystem, UI, parser, rating layer, or repository hunt is justified until EXP-001, a paying customer, security diligence, or rights diligence exposes a named gap.

## Next 24 hours — make the asset diligence-ready

### P0
1. **DONE:** v15 / v15.1 / v15.2 / v15.3 commercialization and machine-gate PRs merged after CI.
2. **DONE:** canonical Freight Recovery v15.3 release identity recorded in `freight/RELEASE_MANIFEST.md`.
3. Produce a release manifest with:
   - source commit;
   - exact component revisions;
   - rights-registry version;
   - test command/result;
   - checksums;
   - known limitations.
4. Complete the missing rights-document evidence checklist for Trenova/Opstrax and any non-permissive runtime component.
5. **DONE when v15.4 CI passes:** full synthetic readiness → qualification → blind proof → persistent settlement → report rehearsal runs from committed code; this is technical validation only, not external customer proof.

### Stop
- no new generic freight repositories;
- no new TMS/UI/rating subsystem;
- no outbound/customer contact unless explicitly approved.

## Next 7 days — make the paid pilot boring to buy

1. Turn the Data Readiness Diagnostic into a repeatable checklist/report template.
2. Produce a sample blind-pilot report with the four required totals:
   - reviewed discrepancy;
   - validated finding;
   - challenger-only validated;
   - uniquely attributable realized.
3. Add source manifest / truth manifest / incumbent-output manifest templates.
4. Add a buyer-facing security/data-handling one-pager derived from `RELEASE_AND_SECURITY_GATE.md`.
5. Execute parser/input negative tests for PDF/XML/EDI/CSV.
6. Validate tenant/business-unit isolation in whatever data service will hold pilot data.
7. Keep an explicit list of every manual analyst touch so pilot gross margin can be measured.

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
   - rights/SBOM;
   - signed provenance;
   - data-retention/deletion policy;
   - incident-response plan;
   - backup/restore evidence;
   - access-control/cross-tenant test evidence.
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
