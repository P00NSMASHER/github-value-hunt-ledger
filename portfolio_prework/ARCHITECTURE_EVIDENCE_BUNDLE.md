# Architecture Evidence Bundle

This is the compact handoff from the completed 10-step parallel prework plan into Portfolio Brain Step 0.

## Verified portfolio baseline

- **7** connected repositories
- **12** canonical top-level project identities
- **2,499** files in the pinned repository snapshot
- **47** GitHub Actions workflows
- **367** discovered test paths
- **14** discovered dependency manifests
- **0** repository snapshot failures
- **0** `pull_request_target` workflows in the pinned workflow set
- **0** projects with unbounded external `ACT` authority

The last prework delta found **6 unchanged repositories and 1 changed repository**: `P00NSMASHER/abvmschoolstarworld`, with six changed files across the recorded comparison.

## What Step 0 should not repeat

Do **not** begin by rereading every repository. Read the durable state and this bundle, then run the SHA-based change detector. Deep inspection should be limited to repositories/files that changed or to evidence specifically required by an architecture decision.

Do **not** recreate project identity. `PROJECT_ID_REGISTRY.json` is canonical.

Do **not** infer authority from existing workflow credentials. `AUTONOMY_MATRIX.json` governs Portfolio Brain authority.

Do **not** invent another control plane merely because the existing systems have unfashionable filenames. Reuse should be the default whenever Hunter, AI Business OS, truth/evidence, learning, verification, or software-factory capability already exists and satisfies the architecture requirement.

## Accepted architecture constraints

1. Existing product repositories remain independent.
2. Portfolio Brain is the portfolio-level control plane, reserved as `PRJ-000`.
3. Exact repository SHAs are the primary cache key.
4. Autonomy classes are `OBSERVE`, `EXPERIMENT`, `MODIFY`, and `ACT`.
5. The most restrictive applicable autonomy rule wins.
6. Consequential external actions remain human-gated.
7. Live market trading and brokerage execution remain prohibited.
8. Existing workflow write/deploy credentials are not inherited authority.
9. Validation should be changed-path and risk aware.
10. Dependency manifests and lockfiles are promotion evidence.

## Highest-priority unresolved risks

- **ABVM freshness:** the repository changed after the original snapshot. Re-run delta before Step 0 uses its cached architecture evidence.
- **Workflow authority:** nine workflows have write/deploy capability. Invocation and credential boundaries need explicit governance.
- **Cross-project automation:** CaptureBrief contains a scheduled write-capable ABVM school-pack refresh, so cross-project edges cannot be hand-waved away.
- **Test coverage wiring:** ABVM's `qa:unit` and the legacy `business_os` test subtree are not represented by matching pinned workflow invocations.
- **Dependency reproducibility:** ABVM floats on `latest`; StarBlox lacks discovered npm/Cargo locks; primary production Python requirements mostly use ranges.
- **Operational-state visibility:** `permitplate-state` should have its access/visibility explicitly reverified before integration because durable state treats it as sensitive operational state.

## Step 0 start sequence

1. Read `PORTFOLIO_BUILD_STATE.json`.
2. Read `ARCHITECTURE_EVIDENCE_BUNDLE.json`.
3. Run `detect_repository_changes.py`.
4. Inspect only changed repositories/files unless a specific architectural question requires deeper evidence.
5. Use `PROJECT_ID_REGISTRY.json` for identity and `AUTONOMY_MATRIX.json` for authority.
6. Reuse existing capabilities before designing replacements.
7. Persist any new architecture decisions and inspected SHAs back into durable state.

## Scope limits

This evidence bundle does **not** prove revenue, customer validation, production readiness, or commercial traction. It does not claim that repositories without discovered manifests are dependency-free. It also does not authorize production deployment, customer contact, money movement, destructive actions, or trading.

Machine-readable source: `ARCHITECTURE_EVIDENCE_BUNDLE.json`.
