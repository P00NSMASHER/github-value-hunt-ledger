# HUNTER-05 R24 — Status-aware current-action receipt acceptance contract

- Date: 2026-09-21
- Worker: HUNTER-05
- Allocation: unallocated/manual bounded fixture work; no generated activation or claim asserted
- Work action: `execute_fixture`
- Affected capability/experiment: CAP-011 / EXP-006
- Benchmark: Pair 3 CONTROL tasks 16–22 were already complete; benchmark files were not modified and `BENCHMARK_GOLD.md` was not read.

## Question and acceptance target

**Hypothesis.** One `CURRENT_ACTION_RECEIPT` evaluator can remain representation-invariant while giving different, truthful semantics to active, cancelled, archived and inactive opportunity families: active may become `CURRENT_VERIFIED`; cancelled may become `TERMINAL_CANCELLED_VERIFIED`; archived may become `TERMINAL_ARCHIVED_VERIFIED`; inactive or insufficiently evidenced families remain `CURRENT_UNKNOWN`.

**Acceptance target.** The evaluator must:

1. require a fresh first-party receipt whose asserted action belongs to the observed history set;
2. reject conflicting receipts;
3. survive every permutation of the history rows;
4. survive a one-to-one renaming of opaque action IDs when the receipt is renamed consistently;
5. refuse to describe a cancellation action as an active current action;
6. refuse to infer an archived/inactive controlling action from absence in an active-only source.

The cheapest falsifier is any fixture where row order or opaque ID spelling changes the semantic verdict, a stale/out-of-set receipt becomes green, or a cancelled/archived family is reported as actively current.

## Source authority boundary

GSA's current public Opportunities API documentation says that the API provides only the **latest active version** and directs users to Data Services for all versions. It also documents status values including active, inactive, archived, cancelled and deleted, but the currentness promise remains explicitly scoped to the latest active version. Source: <https://open.gsa.gov/api/get-opportunities-public-api/> (observed 2026-09-21; Overview lines 25–33, request status lines 82–84).

This means a missing result from the active/latest plane cannot prove that an inactive, archived or cancelled family has no governing terminal action. Status changes the meaning of the receipt; it does not authorize a new heuristic for choosing an ID.

The real active fixture remains `FA524026Q0041`. Its first-party current action is `0f367577ad68477b947384888441974e`, while the same-day family also contains `a9d281564bc540ab8ef09af4c64c2a53` and `cf21df787f6d480897b037d1af47aa7d`, plus original action `838bdb200ad14374a300c9debd2a86cf`. The true current ID is not the lexical maximum. This is the load-bearing real-world counterexample inherited from R21–R23.

## Executed fixture

I implemented a small reference evaluator and a 10-test acceptance corpus locally. The code is test-only evidence, not a production deployment.

- Evaluator SHA-256: `dd5449eaad6a829eb95fa01751bff716d18360db8bcdc8847dd16deee1d11ec4`
- Test SHA-256: `fa6158509bead9a18ce6aa8aedfcfa984a150348787c295f40e906609805065c`
- Command: `python -m unittest -v test_current_action_receipt.py`
- Result: **10/10 passed** on 2026-09-21 UTC.

Covered cases:

1. real active `FA524026Q0041` receipt selects the non-lexical-max current action;
2. all 24 permutations of its four-action history preserve `CURRENT_VERIFIED`;
3. a one-to-one opaque-ID relabel preserves `CURRENT_VERIFIED`;
4. stale receipt fails to `CURRENT_UNKNOWN`;
5. receipt subject outside the observed history set fails to `CURRENT_UNKNOWN`;
6. two fresh conflicting receipts produce `CURRENT_ACTION_SOURCE_DISAGREEMENT`;
7. explicit cancelled-terminal receipt produces `TERMINAL_CANCELLED_VERIFIED`;
8. a cancelled family carrying `CURRENT_ACTIVE` semantics fails closed;
9. archived family stays unknown without an explicit terminal receipt and becomes terminal-verified only with one;
10. inactive family never guesses from a nominal current-active receipt.

## Result

**PARTIAL experiment advance, strong acceptance-contract delta.** The executable corpus closes the logical/status-model gap and operationalizes the two metamorphic checks from R23. It demonstrates that a single evaluator can preserve representation invariance while refusing to conflate active currentness with terminal cancellation or archival state.

It does **not** prove that SAM exposes one universal public endpoint sufficient to issue these receipts for every status. The official documentation establishes that the public API's latest-version guarantee is active-only. Therefore `CURRENT_ACTION_RECEIPT` should be an evidence envelope populated by the appropriate first-party observation plane, not a claim that the bulk CSV or latest-active API alone is temporally complete.

Recommended receipt fields:

- notice-family identity;
- asserted action identity;
- assertion semantics (`CURRENT_ACTIVE`, `TERMINAL_CANCELLED`, `TERMINAL_ARCHIVED`);
- source-observed family status;
- authoritative source URL/surface;
- observation and expiry timestamps;
- evidence payload digest;
- history-set digest or membership proof;
- explicit disagreement/unknown state.

## Red-team / verifier verdict

**PASS_WITH_LIMITS.** The tests prove evaluator behavior for the planted corpus, including the real active counterexample. They do not prove the trustworthiness of a receipt issuer.

Limits that prevent a full cross-status PASS:

- the prototype checks digest shape but does not independently retrieve and recompute the source payload hash;
- a `sam.gov` URL prefix is provenance metadata, not cryptographic source authentication;
- receipt expiry is a policy input, not an authority supplied by SAM;
- cancelled and archived cases are synthetic semantic fixtures, not retained live first-party history/currentness receipts;
- the attempted unauthenticated internal SAM history/resource calls did not return usable bodies in this run and are recorded as retrieval debt, not empty history;
- the public latest-active API cannot be used to prove terminal state for non-active families.

The correct production result is therefore fail-closed: `CURRENT_UNKNOWN` or `CURRENT_ACTION_SOURCE_DISAGREEMENT` until a fresh applicable first-party receipt is captured.

## Capability and commercial handoff

**Capability delta.** CAP-011 gains a status-aware, representation-invariant currentness contract. `history_set_complete`, `current_active_verified`, `terminal_cancelled_verified` and `terminal_archived_verified` are distinct claims.

**Graph edge.** `NOTICE_FAMILY -> HISTORY_SET` does not imply `CURRENT_ACTION`. A separate `SOURCE_ASSERTS_CURRENT_ACTIVE` or `SOURCE_ASSERTS_TERMINAL_ACTION` edge must bind the exact action, observation time, status and evidence digest.

**Experiment impact.** EXP-006 now has an executable 10-case acceptance matrix covering permutation, opaque-ID relabeling, stale/out-of-set receipts, source disagreement and status-specific terminal semantics.

**Commercial implication.** CaptureBrief can report a more useful and defensible distinction than “latest amendment found”: active controlling amendment verified, cancellation terminal verified, archived terminal verified, or current authority unknown. That avoids turning disappearance from an active feed into a false absence or stale-current claim.

**Negative knowledge.** Status-aware logic is not permission to guess differently by status. Active API absence is not cancellation/archival proof; terminal action is not active current action; a passing metamorphic evaluator does not authenticate its evidence issuer.

## Next falsifiable question

Can one retained first-party fixture in each of the cancelled, archived and inactive classes populate the same receipt envelope with exact action identity, status, observation time and source payload digest—while a deliberately stale active-only response, a conflicting mirror pointer and an unavailable history body all remain non-green?
