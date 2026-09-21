# HUNTER-05 R24 — NuGet temporal-rule authority transfer

**Date:** 2026-09-21  
**Worker:** HUNTER-05  
**Mode:** unallocated bounded research; no activation packet or accepted claim  
**Strategy:** `STRAT:rule-period-authority-version-audit`  
**Coverage gap:** `COV:package-ecosystem:nuget`  
**Objective:** `OBJ:current-rule-authority`

## Hypothesis

A .NET/NuGet implementation outside government procurement may supply a reusable source-backed pattern for selecting the rule version that was both effective at the evaluated time and known at a historical knowledge cutoff. To satisfy the assignment target it also needs credible authority provenance, not merely dates and a rule owner string.

## Discovery surfaces

1. Literal GitHub repository/code searches for tax, regulation, `effective_date`, `evaluationDate`, `ValidFrom`, and historical payroll evaluation in C#.
2. Official NuGet package discovery and package extraction for published artifact provenance.
3. Payroll-Engine organization adjacency across the main test repository, backend, client/service packages, and shared domain model.
4. Exact-revision source, schema, fixture, and commit-history inspection.

Broad discovery was noisy. Three plausible families were triaged; Payroll Engine was the only one taken through deep inspection because it exposed an unusually explicit dual-time query and executable-looking historical fixtures.

## Candidate

- **Main repository:** `Payroll-Engine/PayrollEngine@2ddb5c770b0a955936562355a1021f06e922886a`
- **Backend:** `Payroll-Engine/PayrollEngine.Backend@ecd049ee43a64c130981301192a0f8ab36eed1ed`
- **License:** MIT
- **Observed repository profile:** main 124 stars / 32 forks; backend 4 stars / 8 forks; neither archived.
- **Verdict:** **24/30 — WATCH / strong temporal-rule architecture component, not a complete authority engine**

## Source and schema verification

The backend exposes two separate historical axes in `PayrollQuery`: `RegulationDate` and `EvaluationDate`.

`PayrollRepositoryRegulationCommand` maps:

- `RegulationDate` to the effective-rule selection date.
- `EvaluationDate` to `CreatedBefore`, the knowledge/creation cutoff.

The SQL Server and MySQL regulation queries then:

1. enforce tenant ownership or explicitly shared regulation access;
2. reject regulation rows created after the knowledge cutoff;
3. reject versions whose `ValidFrom` is after the effective date;
4. partition by regulation name within the payroll layer; and
5. choose the greatest `ValidFrom`, then greatest `Created`.

Primary paths:

- [repository query mapping](https://github.com/Payroll-Engine/PayrollEngine.Backend/blob/ecd049ee43a64c130981301192a0f8ab36eed1ed/Persistence/Persistence/PayrollRepositoryRegulationCommand.cs)
- [SQL Server version selection](https://github.com/Payroll-Engine/PayrollEngine.Backend/blob/ecd049ee43a64c130981301192a0f8ab36eed1ed/Persistence/Persistence.SqlServer/Functions/GetDerivedRegulations.sql)
- [database schema](https://github.com/Payroll-Engine/PayrollEngine.Backend/blob/ecd049ee43a64c130981301192a0f8ab36eed1ed/Database/Create-Model.sql)

The schema makes versioning intentional: `Regulation` has `Version`, `ValidFrom`, `Created`, `Owner`, sharing/isolation fields, and a unique index on `(Name, ValidFrom, TenantId)`.

This is a real reusable temporal contract:

> selected rule = newest version effective at T whose record was already created/known by cutoff K, inside the authorized tenant/share scope.

## Test and history verification

`VersionPayroll.Test` defines regulation versions with explicit `validFrom` and `created` values and historical payrun evaluation dates whose expected wage changes from 1000 to 2000 to 3000 as the rule versions become available.

- [versioned payroll fixture](https://github.com/Payroll-Engine/PayrollEngine/blob/2ddb5c770b0a955936562355a1021f06e922886a/Tests/VersionPayroll.Test/Payroll.pt.json)

A March 16, 2026 backend fix changed the boundary from `ValidFrom < regulationDate` to `ValidFrom <= regulationDate`. A March 19 test commit added the version-edge family.

- [effective-date boundary fix](https://github.com/Payroll-Engine/PayrollEngine.Backend/commit/46ce3e874e039a23713a65b4530bf09149a03191)
- [edge-fixture addition](https://github.com/Payroll-Engine/PayrollEngine/commit/df0fd1d4ab517998d058ba687c75aeee31ae3ae7)

The actual `VersionEdge.Test` JSON verifies equality at the activation boundary. But the independent evidence audit found an important mismatch:

- The README says the third run evaluates at 2024-02-28 and expects version 2, establishing that future version 3 is excluded.
- The executable JSON instead evaluates the third run at 2024-03-28 and expects version 3.

Sources:

- [edge README](https://github.com/Payroll-Engine/PayrollEngine/blob/2ddb5c770b0a955936562355a1021f06e922886a/Tests/VersionEdge.Test/README.md)
- [edge JSON](https://github.com/Payroll-Engine/PayrollEngine/blob/2ddb5c770b0a955936562355a1021f06e922886a/Tests/VersionEdge.Test/Payroll.pt.json)

Therefore the claimed future-not-yet-active negative is **not actually encoded in that fixture**. The repository also contains retro-payroll fixtures and includes the version families in `Tests/Test.All.pecmd`, but no exact-head public Actions receipt was visible for either pinned head. The required `.NET`/Payroll Engine runner was unavailable in this environment, so no test-passed claim is made.

## NuGet artifact verification

The official NuGet feed lists `PayrollEngine.Client.Services` 1.0.0. The downloaded package:

- has SHA-256 `05fa49e63689030bba9fa032013d21f47b86292f7f70cd4a2595b3971571d606`;
- is signed;
- declares MIT licensing;
- targets `net10.0`; and
- binds its repository metadata to `Payroll-Engine/PayrollEngine.Client.Services.git@0fb18669d551601686c58ecf863b454ae1e72559`.

Package page: [PayrollEngine.Client.Services 1.0.0](https://www.nuget.org/packages/PayrollEngine.Client.Services/1.0.0)

This establishes real NuGet packaging and exact package-to-source provenance. It does not prove that the pinned backend rules or test fixture were executed as part of package publication.

## Authority-provenance red team

The candidate clears effective rule version and historical evaluation at source/fixture level, but it does **not** clear government-grade authority provenance.

The regulation model has a free-form `Owner` and generic attributes, but no dedicated fields or verified receipt for:

- issuing jurisdiction/authority;
- official source document or resource ID;
- source artifact digest;
- promulgation/publication time distinct from record creation;
- explicit effective interval/end date;
- supersession lineage; or
- verifier/policy version used to admit the rule.

A customer can therefore create a temporally well-versioned rule that is still unsupported by controlling legal or government authority. Dual-time selection prevents one class of historical leakage; it does not prove the rule was ever authoritative.

## Claims

- **Effective-at version selection:** VERIFIED in source and schema.
- **Known/created-before cutoff:** VERIFIED in source.
- **Tenant/share scope enforcement:** VERIFIED in source.
- **Historical version changes:** VERIFIED in fixtures, not executed here.
- **Exact activation-boundary equality:** VERIFIED in source/history and encoded fixture.
- **Future-version exclusion fixture claimed by README:** FALSIFIED as an executable-fixture claim.
- **Exact-head automated tests green:** NOT ESTABLISHED.
- **Official/legal authority provenance:** NOT ESTABLISHED; the inspected schema is insufficient.
- **NuGet package-to-source provenance:** VERIFIED for Client.Services 1.0.0, not transitive proof of backend test execution.

## Acceptance-target verdict

The target is **PARTIAL**:

- effective rule version: **yes**;
- historical evaluation: **yes, source + fixture evidence**;
- authority provenance: **no, only local ownership/package provenance**.

Retain as WATCH and as a positive/negative architecture oracle. Do not promote to MASTER from this run.

## Transfer to government evidence

CaptureBrief/FAR/state-local rules need at least four independent coordinates:

1. **effective-at** — when the rule controls conduct;
2. **known/approved-at** — what rule evidence existed at the historical decision cutoff;
3. **scope** — agency, jurisdiction, contract, tenant, or program;
4. **authority provenance** — exact official source identity/version/digest and supersession chain.

The Payroll Engine query supplies a concrete implementation pattern for (1) and (2). The missing (4) is commercially decisive: a point-in-time rules product should be able to explain not only why version V was selected, but which official authority made V controlling.

## Proposed deterministic negatives

1. `RULE_VALID_FROM_BOUNDARY_EQUALITY`
2. `RULE_VALID_FROM_FUTURE_EXCLUDED`
3. `RULE_CREATED_AFTER_KNOWLEDGE_CUTOFF_EXCLUDED`
4. `SAME_VALID_FROM_NEWER_CREATED_SELECTED_ONLY_BEFORE_CUTOFF`
5. `CUSTOMER_OWNER_STRING_WITHOUT_OFFICIAL_SOURCE_RECEIPT`
6. `HISTORICAL_EVALUATION_REPLAYS_EXACT_RULE_VERSION`
7. `README_EXPECTATION_DIVERGES_FROM_EXECUTABLE_FIXTURE`

## Value handoff

- **Capability delta:** CAP-009 gains a concrete dual-time version query; government evidence keeps authority provenance as an independent required layer.
- **Graph edge:** `OFFICIAL_SOURCE_ARTIFACT → AUTHORIZES → RULE_VERSION → EFFECTIVE_INTERVAL / KNOWN_AT → DECISION_RECEIPT`.
- **Experiment impact:** add the seven negatives above before calling a historical rule engine evidence-grade.
- **Commercial impact:** supports a hashed, point-in-time, agency-aware rule engine that can reproduce which rules were effective and knowable without mistaking customer-authored metadata for government authority.
- **Negative knowledge:** `ValidFrom + Created + Owner` is not an official authority receipt; README-described regressions must be reconciled against executable fixtures.

## Next highest-value question

Can a .NET rule package bind the dual effective/knowledge-time selection demonstrated here to an official source artifact ID + digest + jurisdiction + supersession chain, then replay a historical government decision with an independently verifiable rule-selection receipt?
