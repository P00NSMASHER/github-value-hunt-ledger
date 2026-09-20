# Commercial direct-money systems shadow state

## Current hypotheses
### H-COM-001 — Authority-aware money assurance beats generic mismatch dashboards
- STATUS: SUPPORTED BY SHADOW RUNS 1-2; not globally promoted.
- SUPPORTING EVIDENCE: Run 1 `Etherlabs-dev/revenue_leakage_system@64c1af79ac0a22915cfb49f1a2dd6d870059b78a` independently passed the narrow technical verifier claim for effective-dated pricing authority, deterministic expected-vs-actual money math, stale/missing-source blocking, rule-versioned evidence and idempotent finding persistence. Run 2 independently found `michaelayoade/dotmac_sub@fdc85559d9677480090596f88009d2d3eed29e56`, which encodes immutable customer-specific billing-contract versions, explicit shadow-vs-authoritative cut-over semantics and idempotent reversible credit-note/ledger evidence.
- CONTRARY EVIDENCE: run 1 remains synthetic with no realized recovery evidence; run 2's strongest contract-authority owner is explicitly still in expand-and-shadow mode and therefore is not proof of live authoritative billing. Neither run establishes end-to-end recovered cash on an independently labeled customer population.
- NEXT TEST: locate or falsify a production-shaped cut-over/outcome path where immutable contract versions actually drive invoicing/rating and an accepted discrepancy can be traced through posted adjustment/refund/settlement to reconciled receivable state.
- CONFIDENCE: MEDIUM-HIGH on the architecture thesis; LOW-MEDIUM on realized commercial recovery until a closed-loop population is verified.

### H-COM-002 — The commercially stronger stack separates contract truth, mismatch decision and money movement
- STATUS: SUPPORTED BY SHADOW RUN 2; needs another independent outcome-oriented run.
- SUPPORTING EVIDENCE: `dotmac_sub` separates accepted commercial commitment/version lineage from credit-note/ledger correction, while run 1's leakage engine separately computes expected-vs-actual findings. `cboxdk/laravel-billing` independently supports the correction side with effective-dated catalog pricing plus idempotent credit-note/gateway/ledger refunds.
- CONTRARY EVIDENCE: mature billing suites may already cover enough of the stack to erase a standalone product moat; customer contract ingestion/amendment completeness remains the hardest unresolved authority problem.
- NEXT TEST: compare a full mature billing platform's real contract-amendment and refund/settlement semantics against the proposed composed stack on one adversarial historical scenario.
- CONFIDENCE: MEDIUM.

## Validated local lessons
- **2026-09-20 / run 1:** `effective-date authority × source freshness/unknown-state × expected-vs-actual money delta × idempotent evidence` was a higher-signal search intersection than “revenue leakage” alone. It surfaced a verifier-passed 26/30 candidate and cleanly distinguished generic reconciliation from authority-aware money assurance.
- **2026-09-20 / run 2:** The same authority-first idea transferred when extended with `supersede`, `source of truth`, `credit note`, `reversal_of_entry_id`, explicit shadow/authoritative state and idempotency. It surfaced a second verifier-passed 26/30 component and exposed an important truth boundary: a well-tested authority model can still be non-authoritative until cut-over. Treat **authority migration state** as a load-bearing money-control fact, not deployment metadata.
- **Comparator lesson:** `dylanpulver/recon` shows that matching quality is independently valuable when it proves partition, conservation, receipts and determinism, but settlement matching alone does not establish what should have been billed. Keep **matching truth**, **contractual expected-state truth**, and **money-movement truth** as separate layers.
- **Comparator lesson:** `cboxdk/laravel-billing` demonstrates that effective-dated catalog grandfathering plus idempotent refund/ledger tests is a strong reusable component, but catalog price history is not automatically customer-specific contract authority.

## Failed search patterns
- Broad `revenue leakage` queries produce many portfolio dashboards, synthetic CRM/warehouse reconciliations and unsupported headline-dollar claims. Do not deep-inspect unless source authority, effective dates, fail-closed unknown states, deterministic evidence or outcome settlement is visible beyond README.
- Generic payment/AP matching without authority or negative-control semantics is usually a component, not a complete money-assurance oracle.
- Generic `credit note` / `refund` searches over-select systems that can reverse money but cannot prove what should have been billed. Require a structural link to contract/rating authority if using them as recovery evidence.
- Effective-dated **catalog** pricing is not equivalent to versioned customer contract authority. Look for accepted commercial commitment, source identity/version, supersession, actor/reason and explicit cut-over semantics.

## Candidate skills
### SK-COM-001 — Authority-freshness-money-delta intersection
- STATE: LOCAL; 2 distinct successful shadow runs. Eligible for separate Skill Promoter review, but **not promoted or staged by this hunter**.
- INPUT: direct-money/recovery/reconciliation search lane.
- PROCEDURE: search for the intersection of effective-dated authority/provenance, source-freshness or explicit UNKNOWN/BLOCKED states, deterministic expected-vs-actual money calculations, and idempotent/versioned evidence; extend with settlement/credit/remittance terms and explicit authority-migration state when looking for realized-outcome components. Require negative tests for stale/missing/wrong-entity inputs or over-application/replay before deep inspection.
- OUTPUT: candidates more likely to support defensible financial findings and correction evidence rather than dashboard-only discrepancy alerts.
- FAILURE MODES: can miss mature systems whose authority semantics are implicit in domain-specific names; may overfavor clean reference implementations without real customer outcomes; may mistake catalog versioning for negotiated contract authority; may mistake a tested shadow model for live cut-over.
- NEXT IMPROVEMENT: add a mandatory `authority entry -> decision -> correction -> settlement/reconciliation` transition trace and test whether that produces an independently verified closed-loop recovery candidate.

## Open referrals
- COMMERCIAL -> AI: test whether replayable effect-journal infrastructure can wrap money-mutating billing correction commands without bypassing domain idempotency or causing duplicate side effects; see shared shadow referrals.
