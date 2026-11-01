# RETALLY — red-team round 2 financial/evidence repair acceptance

**2026-10-22, strictly synthetic/source-only.** This corrective batch implements the
four validated fixes from RETALLY issue #323 (red-team round 2). It does not
activate a customer pilot, carrier communication, payment rails, actual
settlement, externally adjudicated freight labels, pricing, credentials,
licenses or spending. Protected main is not changed until guarded CI passes.

## Source baseline and ownership

- Original reproduced defects on protected `main` `c2e1230098c29651db31de4511fd5577279f0bdb`; newest repair base is `5a349d3d0836c68224bff6507f998c09b081ac0a` (unrelated website updates, not affected engine files).
- Exact source repair scope: `freight/settlement_store.py`, `freight/priority4_adversarial_lab.py`, `freight/payment_orchestration.py`, `freight/recovery_resilience.py`; and new fixture-only regression suite `freight/test_redteam_round2_repairs.py`.
- Four source changes have a dedicated fail-before/passing-after set of 10 explicit scenario tests + 20 parametrized concurrency/forgery subtests.
- **All test buyers, carrier claims, counter events, bank credits, reviewer roles, amounts and payee identities are SYNTHETIC.** Original private/customer documents are excluded from Git and CI.

## Fix 1 — Prevent returned-credit reuse and partial-return retry misstatement

**Observed before:** Counter for 100% of a fictional credit could reverse an
original partial allocation, and then a new allocation could reuse the remaining
gross credit. The return-status endpoint said `ALREADY_REVERSED` even when some
counter evidence remained outstanding.

**Technical repair:**
- Preserve the original immutable settlement and counter events. Validate that
  all counters against one event never sum to more than the originating credit.
- Within the existing SQLite `BEGIN IMMEDIATE` transaction, derive net credit
  capacity, currently live allocated amount and the amount of unapplied return
  evidence. Block new reviewed allocations while the return remains unresolved;
  route auto-allocation to REVIEW rather than silently consuming a returned credit.
- New allocations cannot exceed the original source's amount **minus all
  returns**, after considering live allocated balance.
- `auto_apply_counter` now distinguishes a *fully* applied counter from a
  partially applied counter. A pending residual returns REVIEW, and a subsequent
  retry can apply any defensible remaining live reversal without duplicate
  reversal-edge IDs.
- Keep valid partial returns fully applied when the remaining original credit
  is genuinely not returned; do not block unrelated carrier funds.

**Prove:** `test_01`–`test_05` use two claims sharing one source event,
full/partial return, return-before-first-allocation, multiple counter sources,
and an already fully reversed control. Global accounting and fee cents must
remain source-declared, not authenticated bank money.

## Fix 2 — Receipts fail closed against fake financial claims

**Observed before:** A forged synthetic result asserted customer approval,
contact, money movement, authenticated cash and billable fees, but the exported
receipt printed zero/clean fields and verified when freshly generated.

**Repair:** Both `case_receipt` and standalone `verify_receipt` independently
reject altered money, authorization, action, bank and customer-request flags.
Do not generate clean receipts based on hardcoded fictional-zero fields when
the underlying supplied result asserts the opposite. Preserve immutable
case, event, financial snapshot and input-fingerprint matches.

**Prove:** `test_06` and `test_07` exhaust the original eight poison
variations plus a mutated customer-request permission. Additional existing
Priority-4 mutation and immutable receipt tests remain required.

## Fix 3 — Atomic per-instruction payment transitions

**Observed before:** Two concurrent SUBMITTED events could both observe the
AUTHORIZED state, produce competing predecessor-NULL hashes and append two
events. The resulting history failed the engine's own replay verification.

**Repair:** Serialize authorization, provider-event admission/append, current
state and immutable snapshot with one **per-orchestrator reentrant lock**. The
lock does not prove independent provider authentication, is not a global
multiprocess transaction, and grants no financial authority. Provider replays,
timestamps, valid transitions, recipient/amount hashes and independent
approval requirements remain enforced.

**Prove:** `test_08` forces 12 independent two-thread first-event races by
releasing the GIL during event hashing. Exactly one event is allowed and the
full immutable history must replay successfully. Regress original payment
stage, approval and reversal tests unchanged.

## Fix 4 — No double-counting shared event-level pending returns

**Observed before:** A single $20 pending counter associated with an event
funding two claims appeared as $20 pending *for each claim*, incorrectly
suggesting $40 of returns when summing per-claim summaries.

**Repair:** A source event split across multiple claims has no defensible
automatic per-claim return attribution. The claim-level numeric
`outstanding_return_cents` remains zero for such *unapplied* event-wide
returns; a stable opaque list of unattributed event-return IDs is used to
retain the hold/review requirement. The existing currency-partitioned report
continues to show the original exact event-wide return once. Single-claim
pending returns remain exact. Synthetic cash and billable fee remain zero.

**Prove:** `test_09` and `test_10` assert two-claim non-additive review
and one-claim exact-cents continuity. Frozen Priority-4 source-free scenario
digests must not change when no new shared-return evidence is present.

## Release and evidence boundaries

- The GitHub PR head must pass the existing repository release gate, Freight
  Commercial Contracts, Real Customer Evidence Truth Gate, and regression
  suites; optional dedicated cross-platform tests remain source-only.
- Protected main integration requires GitHub-native guarded merge, no force
  pushes or independent financial approval waivers, then exact-main CI readback.
- Any live payment, true buyer/contract authorization, commercial recovery,
  adjudicated freight error and customer launch requires independent evidence
  and permissions. Those gates are not implied by an internal test pass.
- **Real freight-error accuracy remains NOT ESTIMABLE** on the original
  unadjudicated 110 invoice faces. This repair does not alter that census.
