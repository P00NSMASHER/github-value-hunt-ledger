# HUNT-05 R25 — OpenFisca effective-rule version transfer and granularity boundary

Date: 2026-09-21  
Worker: HUNTER-05  
Assignment: SLOT-12 / SEED:measure:authority-origin-invariant-set-consistency-rule-version-transfer  
Work action: search  
Strategy: STRAT:authority-origin-invariant-set-consistency  
Objective: OBJ:current-rule-authority  
Candidate: openfisca/openfisca-france  
Exact revision: ebcb7782d17058495c6ca33c278e373e167b641b  
Verdict: PASS_WITH_LIMITS / 24 of 30 as a rule-version transfer reference; WATCH for exact effective-date adjudication

## Bounded question

Can one independent tax/benefit rules implementation join all three required invariants in executable source and tests:

1. effective rule version;
2. historical evaluation;
3. authority provenance?

The connected path inspected was the French CROUS university-meal price change taking effect on 2026-05-04.

## Discovery and disposition

The generated query family supplied three anchors:

- OpenFisca reforms parameter
- tax effective_date path:tests
- benefits rule_version

Three plausible implementations were triaged: OpenFisca France, PSLmodels Tax-Calculator and PolicyEngine US. OpenFisca France was selected for one deep inspection because its exact current revision is itself a fresh, reviewable statutory change with parameter history, official references, before/after tests, package versioning and exact-head CI. No unrestricted rules-engine sweep was performed.

## Positive implementation evidence

At exact revision ebcb7782d17058495c6ca33c278e373e167b641b, OpenFisca France version 176.1.0 adds a dated parameter value for 2026-05-04:

- 2016-09-01: EUR 3.25
- 2019-09-01: EUR 3.30
- 2021-01-25: EUR 1.00
- 2021-09-01: EUR 3.30
- 2026-05-04: EUR 1.00

The same parameter object carries date-keyed authority metadata. The new value cites both the French Service Public explanation and Loi no. 2026-103 of 19 February 2026. Earlier values retain their own CNOUS/CNOUS-board source links.

Source:
https://github.com/openfisca/openfisca-france/blob/ebcb7782d17058495c6ca33c278e373e167b641b/openfisca_france/parameters/prestations_sociales/education/alimentation/montant_repas_non_boursier.yaml

The connected formula evaluates the person's schooling and scholarship status and retrieves the meal-price parameter for the requested period. This establishes that the dated authority object is load-bearing calculation input rather than documentation detached from execution.

Source:
https://github.com/openfisca/openfisca-france/blob/ebcb7782d17058495c6ca33c278e373e167b641b/openfisca_france/model/prestations/alimentation.py

The checked-in formula tests exercise historical and new states:

- September 2023: non-scholarship higher-education student = EUR 3.30; scholarship student = EUR 1.00.
- June 2026: both scholarship and non-scholarship higher-education students = EUR 1.00.

Source:
https://github.com/openfisca/openfisca-france/blob/ebcb7782d17058495c6ca33c278e373e167b641b/tests/formulas/crous_repas_montant.yaml

The merged change also increments the package version from 176.0.10 to 176.1.0 and records the affected period and parameter path in the changelog. Pull request 2800 was reviewed and approved, explicitly required legislative references and tests, and merged on 2026-09-18.

History:
https://github.com/openfisca/openfisca-france/pull/2800
https://github.com/openfisca/openfisca-france/commit/ebcb7782d17058495c6ca33c278e373e167b641b

Exact-head GitHub Actions completed successfully for both the main OpenFisca France workflow and the reusable YAML-validation workflow:

- https://github.com/openfisca/openfisca-france/actions/runs/35360792122
- https://github.com/openfisca/openfisca-france/actions/runs/35360794163

The repository is licensed under GNU AGPL v3. The package metadata describes it as production/stable. These facts support implementation reuse analysis but do not establish government certification.

## Independent first-party authority corroboration

The French Service Public page says the EUR 1 meal became available to all students from 2026-05-04, whereas other students previously paid EUR 3.30. It identifies Loi no. 2026-103 as the legal reference.

Authority:
https://www.service-public.gouv.fr/particuliers/actualites/A18811

The direct Legifrance page was referenced by the model and by Service Public, but the noninteractive retrieval path returned HTTP 403 during this run. The statutory document identity is therefore source-linked and corroborated by Service Public, while its exact bytes/text were not independently retained here.

## Red-team: effective date is not effective granularity

The candidate meets the assignment's three positive evidence requirements, but it does not establish exact daily application of the May 4 change.

The rule variable has MONTH definition granularity. Its formula calls parameters(period). OpenFisca Core converts a Period argument to period.start before selecting parameters:

https://github.com/openfisca/openfisca-core/blob/0e4be150c2697c8581c648ec72bd241e3fa2e6f8/openfisca_core/taxbenefitsystems/tax_benefit_system.py

For period 2026-05, the lookup instant is therefore 2026-05-01. That precedes the parameter's 2026-05-04 effective date, so the May monthly calculation selects the earlier EUR 3.30 value. The new regression test begins in June and does not exercise 2026-05-04, May 3 versus May 4, or any proration/split-period policy.

This is a source-derived temporal-granularity finding, not a locally executed numerical failure. Exact-head CI proves the committed tests pass; it does not prove a boundary case that the suite does not contain.

The safe conclusion is:

**Versioned historical parameters plus official citations do not establish effective-time correctness when calculation granularity is coarser than legal effective granularity.**

## Acceptance result

- Effective rule version: PASS. The package and parameter histories explicitly version the change.
- Historical evaluation: PASS_WITH_LIMITS. Before/after years are covered, but the within-May boundary is not.
- Authority provenance: PASS_WITH_LIMITS. Date-keyed official references are retained; one cited statutory page was not independently retrievable in this run.
- Exact temporal application: NOT ESTABLISHED and source-challenged for 2026-05-04 through 2026-05-31.
- Current test status: PASS for the committed suite at exact head.
- Government certification: NOT CLAIMED.

The generated assignment acceptance target is satisfied as an implementation discovery, with an important contradiction that caps the candidate at WATCH for exact adjudication.

## CaptureBrief / CAP-011 transfer

CaptureBrief should preserve at least four independent fields for every rule-bearing fact:

- rule/package version;
- legal effective instant or interval;
- evaluation/request instant and computation granularity;
- source authority identity plus observation/hash state.

A rule receipt should fail closed or declare APPROXIMATED whenever the evaluation granularity cannot represent the authority's effective instant. Month-level, day-level and instant-level rule changes must not be treated as interchangeable simply because they share a date-keyed parameter store.

Suggested EXP-006 adversary:

EFFECTIVE_2026_05_04__MONTHLY_ENGINE_USES_2026_05_01__BOUNDARY_SILENTLY_MISAPPLIED

Expected state: TEMPORAL_GRANULARITY_MISMATCH, not CURRENT_VERIFIED.

## Value handoff

1. Capability delta: CAP-011 gains an explicit authority-effective-granularity check.
2. Graph edge: RULE_VERSION -> EFFECTIVE_INTERVAL -> EVALUATION_INSTANT -> ENGINE_GRANULARITY -> AUTHORITY_SOURCE.
3. Radar signal: rules-as-code maturity depends on representable temporal semantics, not merely dated parameters and citations.
4. Commercial implication: CaptureBrief can flag procurement clauses, thresholds or deviations whose effective date falls inside a coarser model period.
5. Negative knowledge: historical versioning, green CI and official provenance can coexist with a temporal boundary the engine cannot express.
6. Cheapest next test: add May 3, May 4 and June 1 fixtures against a day-capable reference oracle; require explicit unsupported/approximated status if the monthly OpenFisca variable cannot represent the legal boundary.

## Lifecycle note

A current generated activation for SLOT-12 was obtained and a CLAIM event was written. Canonical execution reduction did not complete because the shared intelligence workflow failed on an unrelated pre-existing active-claim conflict in SLOT-05. This run must not be marked COMPLETE until canonical claim/run readback succeeds. The research evidence itself is durable; allocation/claim completion is not asserted.
