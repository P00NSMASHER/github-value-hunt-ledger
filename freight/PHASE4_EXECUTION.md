# RETALLY Phase 4 | Integrated laboratory research acceptance

Status: **draft implementation, not a hosted production certification.**

## Verified stack and source provenance

This branch is stacked on Phase 3 PR #295 (pinned original commit `c617fff9d9718b3b026d4f2b774a19b19b48b8e0`) and inherits the **unmerged** PRs #288, #286, #284 and #279. The historical 26 findings remain OPEN_UNVERIFIED. No user/customer/financial assets were processed or contacted.

## Executed code, not task routing

Run `PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-phase4`.

The Phase 3 execution chain reuses these real Python domain functions:
- Lab 1 `rate_record` with controlled tariff and invoice inputs
- Lab 4 `verify_record` plus separately provided fictional source assertion
- Lab 5 `SettlementStore` and `verify_settlement` for exact settlement and reversal arithmetic
- Lab 8 `analyze_contingency` with the zero-upfront commercial model
- Lab 11 temporary database copy, deliberate mutation and independent semantic rejection

Phase 4 invokes **nine additional existing repository modules**:
- Lab 2 `simulate_customer_reactions` for modeled status/credit customer responses
- Lab 3 `build_accuracy_report` / `validate_accuracy_report` on code-adjacent synthetic gold
- Lab 6 `validate_security_readiness` on the existing security evidence contract
- Lab 7 `qualify_free_audit` on controlled fictional lead data
- Lab 9 `assess_readiness` with hard authorization blockers
- Lab 10 `verify_compiled_authority` for historical tariff digest integrity
- Lab 12 `evaluate_payments` on the frozen synthetic payment corpus. **This is not real fraud-detection accuracy.**
- Lab 13 `analyze_contingency` with an adverse labor-cost sensitivity test
- Lab 14 `validate_competitor_evidence` on source-dated public vendor claim snapshots. **Not an independently audited competitor ranking.**

Each additional adapter invokes domain logic and a negative test. An invalid or unavailable implementation returns FAILED_OR_BLOCKED; missing budget returns NOT_EXECUTED_BUDGET, not PASS. The 14/14 result means 14 distinct Python test pathways actually executed, **not** 14 hosted services, separately staffed labs, externally audited vendors, or genuine bank evidence.

## Experiment Director

`lab_phase4_experiments.py`:

- Reads original 26 OPEN_UNVERIFIED research findings.
- Chooses a limited number of high-priority, distinct root-cause clusters.
- Invokes actual bounded Python research execution.
- Independently validates the run receipt, including exclusion of runtime measurements from content digests.
- Appends research records to the existing hash-linked SQLite ExperimentLedger.
- Explicitly returns INCONCLUSIVE for previous findings, because a new comparable module-level negative test is *not* independent proof that the original historical implementation was repaired.
- Measures actual experiment wall time locally, not a model estimate.

## Durable provider replay experiment

`lab_phase4_mock_provider.py` uses file-backed SQLite with BEGIN IMMEDIATE, uniqueness constraints, append-only event tables, event-time normalization and a bounded busy timeout. Threaded tests check that 30 concurrent duplicate mock callbacks produce one persisted event, and retry after a lost acknowledgment does not create another effect. Conflicting reference/payload/actor replays fail. OUTCOME_UNKNOWN is held without automatic resubmission.

This is **isolated Python mock-provider concurrency**, not a demonstration of actual Floot Postgres atomicity, the hosted payment event handler, external bank identity, or provider reconciliation. Do not copy it into production without a separate migration and integration review.

## Simulated founders and economics

Phase 3's three fictional founding engagements remain the source of illustrative customer outcomes. No case represents a real enrolled customer. Actual RETALLY revenue and customer recoveries are zero. The existing contingency model correctly preserves negative modeled margins. No new generated million-row population was added.

## Isolated staging gap

The connected Floot account currently exposes a published RecoveryOS project; its preview code and three selected pure spec suites were inspected/read-only verified. Its resource separation from production was **not** demonstrated. Preview code is not a separate database. Do not exercise destructive or unauthorized tests against the published project, do not expose any production secrets, and do not claim hosted staging certification.

To close this gap, provision a fully segregated Floot project and independently provisioned database under a reviewed resource/cost/credential plan. Keep external providers mocked and prohibit production endpoint access. Test actual session/tenant/API/database behavior, concurrent payment callbacks, cross-tenant attempts, restore and migrations before marking HOSTED_ISOLATED_STAGING.

## Release gates and remaining business evidence

1. Never merge or deploy these drafts automatically.
2. Keep all 26 historical finding IDs unchanged until each exact failing original has before/after verification.
3. Validate real legal contract and buyer-source control through independent authorities before real recovery claims.
4. Do not treat self-signed fixture evidence as authentic carrier/bank remittance.
5. Do not infer customer conversion, freight overpayment frequency, or real margins from fictional examples.
6. Use the generated HTML/JSON control center as a **research-only** operator view.

The most valuable next work is an externally controlled isolated Floot environment, true buyer/carrier proof admission, and a genuine customer-approved pilot.
