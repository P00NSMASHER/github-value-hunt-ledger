# EXPERIMENTS

Canonical stage-gate queue converting research into falsifiable technical/economic evidence. Repository quality is not an outcome; commercial validation exists only when a result is recorded in `OUTCOMES.md` with direct evidence.

## States
- READY — lawful/synthetic inputs available.
- BLOCKED_EXTERNAL — requires customer-authorized/external data or access.
- RUNNING — execution evidence is being produced.
- PASSED / FAILED / PARTIAL / INVALID — record under `OUTCOMES.md` when the experiment itself completes.
- SUPERSEDED — replaced by a better test.

## Priority queue — 2026-09-20

### EXP-001 — Freight blind audit to realized settlement
- Opportunity: Freight Recovery v15.3.
- Capabilities: CAP-001, 003, 004, 005, 006, 007, 016.
- Status: **BLOCKED_EXTERNAL**.
- Hypothesis: on one buyer-authorized frozen population, the stack can find at least one unique incumbent-missed freight overcharge with zero unsupported dollars and carry it through actual externally observed settlement.
- Internal technical substage: **substantially exercised, not commercial validation.** The planted 210/812/820 corpus covers exact unique auto-allocation, reviewed partial/split edges, duplicate/orphan/excess/wrong-currency/pre-authority cases, full reversal, ambiguous partial reversal and 2,000 deterministic fuzz ledgers. A persistent SQLite reference now adds immutable claims/events, integer-cents allocation edges, one-use event capacity, review-only persistence, append-only counter-events, SQL capacity/immutability triggers, `BEGIN IMMEDIATE` write serialization and lock retry. Hunter verification reports **21/21 persistence tests passed** plus **200 repeated two-writer/one-claim races** with exactly one realized allocation; exact-revision CI also passed.
- External inputs: fixed entity/BU/date/population; controlling contracts/rates/RateCons/addenda/tariff authority; shipment evidence; sealed incumbent output; later credit/refund/remittance/bank evidence; customer authorization/retention/read-only boundaries.
- Procedure: readiness gate -> freeze/hash population -> freeze independent truth -> open/hash incumbent output -> score unique findings -> buyer adjudication -> authorized dispute/action -> independently observe settlement -> one-use allocation -> recovery certificate -> later counter-event/reversal.
- Success: unsupported asserted/realized dollars = 0; deterministic replay = 100%; every accepted finding has authority/expected/actual/evidence lineage; at least one challenger-only validated finding unless genuinely clean; `recovery proven` requires issued adjustment plus unambiguous external settlement allocation.
- Failure: truth circularity, population drift, unsupported authority/identity/evidence, duplicate/preexisting credit, ambiguous allocation counted as realized, returned money left fee-eligible, race over-consumption, or false-positive dollars beyond buyer ceiling.
- Next action: obtain one explicitly authorized closed buyer population. Do not resume broad freight discovery. Production DB/tenancy/security hardening is secondary unless the external connector exposes a concrete defect.

### EXP-002 — AP source-authority + reversible receipt-policy audit
- Opportunity: AP Leakage Assurance.
- Capabilities: CAP-002, 007, 008, 016, 019.
- Status: **READY**.
- Hypothesis: explicit source observation, reviewed identity, policy-specific receipt authority and reversible line-level authority consumption can distinguish recoverable AP leakage from unresolved exceptions without false missing-receipt/PO dollars.
- Authority model: `ReceiptAuthorityPolicy(system, PO-line type, buyer config, supplier override, verification mode)` resolves to `GoodsReceipt`, `ServiceEntrySheet`, explicit `DirectInvoiceAllowed`, or REVIEW; source health is separately `PRESENT / VERIFIED_EMPTY / UNAVAILABLE`.
- Evidence challengers: Business Central exact invoice↔PO-line↔receipt-line conservation; ERPNext partial-receipt semantics; `odoo/odoo@c55c82dac6283a77ee747e1e672a29e85180980f` counter-event semantics; MiniGraf bitemporal replay; Nomenklatura negative/reversible identity plus Canon pinned registry.
- Required cases: one PO line across partial receipts; mixed direct and PO-level billing; rejected quantity; service-entry-sheet required vs legitimately not required; source outage/partial load; identity reject/merge/split correction; physical return that **does not** reopen commercial authority; refunding return that does; vendor credit note; bill cancellation; re-receipt; two same-SKU PO lines; UoM/precision adversary; later correction/settlement.
- Conservation rule: every accepted invoice/receipt edge consumes exact amount/quantity capacity on a specific source line; every counter-event must reference the original edge, restore/reduce only the policy-authorized capacity, preserve the original event and replay deterministically. Product/SKU equality alone cannot establish line ownership.
- Success: all planted cases detected; unsupported recovery = 0; explicit non-match blocks false merge; unavailable source cannot create missing-receipt/PO money; amount+quantity capacity is conserved through returns/credits/cancellation/re-receipt; bitemporal replay reproduces what was known then and what became valid later.
- Failure: universal `has_receipt`, any-return-means-authority-restored, source outage becomes negative evidence, ERP header/status copied as truth, same-product auto-assignment establishes ownership, implicit float/UoM rounding creates/destroys authority, or exception dollars are labeled recovered.
- Next action: implement the ERP-neutral reversible-authority ledger corpus. Do not search another generic three-way-match product unless this corpus exposes a concrete missing semantic.

### EXP-003 — Commission plan-to-bank acceptance test
- Opportunity: Partner / Commission Payout Assurance.
- Capabilities: CAP-002, 006, 007, 016, 018, 019.
- Status: **READY**.
- Hypothesis: frozen entitlement plus provider state and independently observed bank/payroll state can detect payout errors without duplicate-send or false-finality risk, while ambiguous linkage and unavailable source windows remain non-final.
- Evidence architecture: `Modern-Treasury/modern-treasury-python@406f354a06a98060df0c9f4c242fe56cc65e1526` provides Payment Order/reference -> bank-derived Transaction/Transaction Line Item -> later Return/Reversal shape; `szapata85/ACHInterbank@395a359230eff35e49cc196b49995ed4c49509b9` is a fail-closed Exact/Ambiguous/NotFound correlation oracle. Hosted treasury/bank services, account authority and feed coverage remain external.
- Observation contract: every settlement lookup = `EXACT_UNIQUE / AMBIGUOUS / NOT_FOUND / UNAVAILABLE`. `EXACT_UNIQUE` requires deterministic identity/reference/amount/currency/time compatibility against an independently observed transaction inside a verified source window. Trace/reference alone is evidence, not unique economic identity.
- Required negatives: duplicate ACH/original-trace candidates; substring/fuzzy reference collision; equal totals/swapped identities; first-unmatched-row trap; unparseable amount; stale cursor; provider-completed/bank-absent; bank-posted-then-returned; duplicate semantic return; ambiguous return; unavailable source during return window; concurrent payout sweep.
- Success: unknown provider result stays pending and cannot retry; definite refusal alone releases; duplicate send impossible; provider success and final settlement distinct; only exact unique mapping inside verified coverage may establish settlement; later return/reversal exactly unwinds prior finality without deleting history.
- Failure: provider status establishes entitlement/finality; trace alone is finality; substring/fuzzy/amount-only/first-match becomes exact; cursor continuity is treated as completeness; ambiguous/unavailable bank evidence mutates realized money; return leaves prior payout economically final.
- Next action: execute the provider-neutral matrix. Resume search only if it exposes a concrete provider/reference->independent-bank/payroll or coverage gap.

### EXP-004 — Recovery Proof scoped-coverage + adversarial verifier matrix
- Opportunity: Recovery Proof SLA.
- Capabilities: CAP-007, 010.
- Status: **READY**.
- Hypothesis: a recovery proof system can restore valid state, reject wrong-but-restorable state, prove expected workload coverage and remain non-green when the verifier, proof sink, cleanup or semantic assertion path is broken.
- Strong challengers: `kirilurbonas/FireDrill@1e532b17e49e4424f988b29dd338ae6c48dc20f3` (29/30 hunter score) for multi-engine isolated restore, semantic checks, RTO/RPO, signed DSSE evidence and expected-subject coverage gates; `snapetech/DuneAwakeningSelfHost@8d3bac1df38f45fb13e2c1427216bf5dc384687b` for PostgreSQL+RabbitMQ/Mnesia dual-plane recovery; Mukuroji for DynamoDB/S3 semantic history; existing Postgres negative controls and SiVa trust validation.
- Inputs: isolated PostgreSQL plus non-Postgres/object/broker workload; wrong PITR target; missing history; corrupt object; service-up/data-wrong; stale proof; trust/revocation failure; total-host/credential-boundary; deliberately damaged assertion helper; proof-sink outage after restore; expected subject missing entirely; one failing sibling masked by aggregate control; semantic SQL/query that exits 0 but returns wrong value; cleanup failure.
- Coverage contract: customer assurance must supply a versioned/fresh expected workload/subject inventory. Evidence-directory discovery alone cannot prove absence of a vanished drill. Gate per workload/subject; a control-level aggregate cannot hide a failing sibling.
- Procedure: freeze expected inventory -> restore isolated workload -> independently measure structural/content/application/relationship/broker invariants -> RTO/RPO -> trust validation -> persist proof -> verify expected-subject coverage -> cleanup receipt -> inject negatives -> mutate verifier -> rerun.
- Success: every planted bad state fails for the intended reason; missing expected subject is non-green; successful restore with unavailable proof sink is non-green; semantic assertion checks returned value not merely process exit; cleanup failure remains non-green; damaged verifier cannot stay green.
- Failure: missing workload disappears from evaluation, aggregate control masks a failed workload, query rc=0 is accepted as semantic truth, wrong state or broken assertion yields PASS, or proof persistence/cleanup failure is hidden.
- Next action: execute the scoped expected-subject matrix on PostgreSQL plus one rights-clean dual-plane workload. Keep FireDrill as a strong component/challenger until the integrated matrix runs; do not add another generic restore framework.

### EXP-005 — ScopeSignal authority-to-paid benchmark
- Opportunity: Construction Change Leakage Recovery.
- Capabilities: CAP-001, 006, 007.
- Status: **READY** synthetic; **BLOCKED_EXTERNAL** for commercial proof.
- Hypothesis: design/field changes can be traced through measurement, contract/work-order authority, notice, bill/certification, retention and independently cleared cash without inventing entitlement.
- Inputs: synthetic project with 20–50 changes; wrong work-order ownership; over-measurement; draft/rejected/approved measurement; wrong billing period; concurrent quantity claim; superseded baseline; retention error; internal payment/bank-reconciliation divergence; later reversal.
- Comparator pattern: Nirman approved-measurement-derived billing vs `mradul010/construction_management@ce345579...` server-reloaded work-order/PO quantity/rate bounds. Neither is complete truth by itself.
- Success: unsupported/draft/rejected/over-limit states remain nonbillable/REVIEW; authoritative ownership and cumulative quantity hold; internal `Approved/Paid/Reconciled` never substitutes for independent cleared-cash evidence.
- Failure: caller-entered quantity creates authority, internal accounting status becomes bank finality, or design delta becomes entitlement.
- Next action: run the cross-implementation adversarial corpus; search again only if a concrete measurement/certification or cash-finality gap remains.

### EXP-006 — CaptureBrief 10-solicitation packet/authority benchmark
- Opportunity: CaptureBrief FAR-Deviation Readiness.
- Capabilities: CAP-002, 007, 011, 019.
- Status: **READY**.
- Hypothesis: separate deterministic planes for notice/action history, deletion-inclusive attachment observations, immutable artifacts, current rule/deviation authority and entity/award lineage materially improve packet completeness over latest-row ingestion.
- Architecture: official SAM/Data Services notice/action lineage; per-action public resource-manifest observations; immutable public-artifact hashes; FAR/supplement/deviation authority; entity/award lineage. `chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636` remains a useful current-manifest reference but is revised to **26/30 component** because it does not pin `excludeDeleted=false` and does not create a complete absence/disappearance history across successful rechecks.
- Manifest contract: where supported, request `excludeDeleted=false` explicitly; every check gets immutable observation identity carrying action/notice, exact URL/query semantics, observed time, source/HTTP state, full-body hash, parser/schema version and completeness flag; every entry is bound to that observation; newer observations never delete prior evidence; explicit tombstones and disappeared IDs are typed separately; source failure/429/5xx/shape drift cannot emit disappearance.
- Required cases: explicit `deletedFlag=1`; resource present in action A but absent in successor action B after deletion semantics; absent after transient failure (must not create deletion/disappearance); legitimate 200/no-attachments; restricted/export-controlled resource; off-site PIEE/external dependency; same business Notice ID across multiple action UUIDs; version change forces new manifest observation.
- Success: exact packet completeness for frozen rubric; correct amendment/action ordering; lossless append-only manifest history; byte/event-stable rerun; every relevant action has deletion-inclusive successful observation or explicit blocker; source failure cannot become no-change; rule/deviation currentness and entity joins are correct.
- Failure: latest manifest or bulk history assumed attachment-complete; undocumented endpoint default decides tombstone visibility; disappeared/deleted attachment silently lost; source failure emits disappearance; stale authority applied; unresolved join becomes confident.
- Next action: for the ten frozen opportunity families, query each historical action UUID with explicit deletion inclusion where supported and determine whether the union reconstructs every previously public attachment or whether independent polling snapshots are still required.

### EXP-007 — Installed-base sequencing/lab handoff acceptance
- Opportunity: Installed-Base Lab Automation.
- Capabilities: CAP-013, CAP-017 plus governance/provenance components.
- Status: **READY** for rights-clean synthetic tests.
- Hypothesis: Clarity -> sample-sheet/run identity -> InterOp -> provenance can improve workflow evidence without sequence-content/PHI dependence, while consequential physical actions remain single-identity, fail-closed and non-redispatchable under ambiguous outcomes.
- Evidence challengers: `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` preserves one action identity across an immediate lost response, re-queries that same action ID, converts repeated unresolved readback to `UNKNOWN`, and fails the workflow; generic workflow retry can nevertheless create a fresh `ActionRequest`/ULID without mandatory reconciliation. Official `Opentrons/opentrons@03b991fb263b97b6bb767ce311ca56e103d635e4` supplies a materially stronger external recovery plane: stable vendor `run_id`, persisted run-control actions/commands/state, and explicit Robot Server restart-persistence tests. Its boundary is equally important: `RunActionCreate` exposes no client idempotency/action ID, and `RunController.create_action()` initiates play/resume before persisting the `RunAction`, so absence of an action record cannot alone prove the side effect never began.
- Inputs: synthetic Clarity QC/pooling/run-prep state, generated sample sheet, lawful InterOp fixtures, stable run identity, invalid transition, missing/mismatched identity, missing metric artifact, run-metric exception, and fault-injected physical-action cases at three seams: request never reaches play; play/effect begins but response is lost; Robot Server/process dies after effect initiation but before action persistence. Preserve both orchestration attempt ID and vendor/device `run_id` across restart.
- Ambiguity contract: `intent/attempt ID -> vendor run_id -> same-run action/status/command readback -> APPLIED / NOT_APPLIED / UNKNOWN -> recovery gate`. Persisted action/status may prove APPLIED strongly enough to block duplication. Missing action alone is not NOT_APPLIED. `UNKNOWN` is terminal for normal progression and may not be converted into a fresh physical action by a generic retry surface. A replacement is legal only after independent device/state evidence proves the original action did not apply.
- Success: deterministic workflow/run linkage, independent sample-sheet validation, rejection of bad identities/transitions, explicit unknowns and replayable provenance; response-loss recovery uses the original run/action identities; restart preserves the same decision; APPLIED causes no reissue; unresolved remains blocked; an explicitly linked replacement is permitted only after independent NOT_APPLIED evidence.
- Failure: wrong run joined, missing evidence turns green, PHI becomes required, command-mutated local state is accepted as physical proof, standards facade is mistaken for safe control, process restart loses original identity, generic retry creates a new physical action while the old effect remains unresolved, or no persisted action is treated as proof that redispatch is safe.
- Next action: execute the exact Opentrons `run_id` ambiguity matrix on the pinned Robot Server/dev-server first, including a kill in the side-effect-before-action-insert window; then connect the MADSci-shaped retry/restart path and finally use an authorized non-destructive OT-2/Flex fixture if available. `AD-SDL/ot2_module` remains an adapter/harness, not the recovery authority. Do not resume broad lab-device discovery before this fixture runs.

### EXP-008 — Industrial virtual pre-FAT differential benchmark
- Opportunity: Industrial Pre-FAT / Virtual Commissioning.
- Capabilities: CAP-014.
- Status: **READY**.
- Hypothesis: customer/profile-derived virtual endpoints can catch binding/type/state/error/liveness defects before hardware when independently differential-tested.
- Inputs: synthetic L5K/PLC namespace with planted drift; frozen SECS/GEM dialogue/error profile; Dreamine.Gem and unrelated `bparzella/secsgem`; exact duplicate-ECID W-bit S2F15 probe `[ECID x -> valid A, ECID x -> valid B]`.
- Current source/test-backed prediction, **duplicate-specific runtime NOT_RUN**: Dreamine rejects duplicate ECID during decode, emits correlated S9F7, leaves EC state unchanged and the original request later expires T3 because S9F7 is not the normal S2F16 secondary; secsgem has no duplicate-ECID constraint and is source-predicted to return S2F16 EAC=0 with second-value-wins.
- Measurement contract: record normal secondary vs F0 vs Stream-9 error, correlated System Bytes/header, requester T3/liveness outcome and post-state. Do not collapse a protocol error that leaves the original request pending into a generic `rejected` state.
- Success: all PLC defects detected; valid bindings preserved; duplicate fixture is actually executed against both pinned packages; every SECS/GEM disagreement classified as profile ambiguity, implementation defect or unresolved standards/vendor-authority question; error and liveness states cannot silently pass.
- Failure: same-family agreement used as proof, implementation agreement labeled formal conformance, source prediction mislabeled runtime-tested, or error reply assumed to close the original transaction without tracing transaction semantics.
- Next action: execute this exact duplicate fixture against both pinned engines before searching a third implementation. A third engine is justified only to adjudicate an observed disagreement.

### EXP-009 — Permit intelligence multi-jurisdiction benchmark
- Opportunity: Permit-to-Development Opportunity Intelligence / PermitPlate.
- Capabilities: CAP-002, 012, 019.
- Status: **READY**.
- Hypothesis: canonical versioned permit events plus explicit source observation and parcel/economic context outperform raw lead lists on reliability/actionability.
- Inputs: three heterogeneous jurisdictions, 30–100 held-out permit events and source-run completeness/freshness metadata.
- Success: source completeness established; correct field semantics; stable identity/versioning; source outage never becomes verified-empty; useful buyer features carry source dates.
- Failure: semantic mapping error, duplicate/version confusion, empty-success or unsupported economic inference.
- Next action: freeze source-field truth for three jurisdictions.

### EXP-010 — Money-state integrity common month
- Opportunity: Money-State Integrity / Close Assurance.
- Capabilities: CAP-006, 016, 018, 019.
- Status: **READY**.
- Hypothesis: a generalized operational-event -> accounting -> provider -> independently observed settlement/counter-event boundary can underpin multiple assurance verticals.
- Strong implementation references: `NotAbdelrahmanelsayed/paymob_integration@8999a6799c5673ad49471224ad0f8012a447495d` (**28/30**) preserves `Pending` on timeout/5xx ambiguity, recovers lost webhooks through provider inquiry, writes a durable refund-request marker before the one-shot side effect, requires a signed/independently fetched child refund delta before posting the ERP reversal, and holds inconsistent cumulative refund evidence for human review. `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` (**27/30 shadow evidence**) adds a stronger provider-accounting application fixture: Stripe test-mode worker SIGKILL after a real customer-balance credit POST, genuinely new-process recovery, exactly one surviving approved credit, and later Stripe Billing application of that credit to a paid renewal invoice that reduces amount due by exactly $10. Its published careful handwritten baseline ties every money outcome, so Interlock's differentiator is reusable recovery/evidence machinery and tamper-evident receipts, not unique economic correctness. `mymi14s/frappe_paystack@546aa26...` remains an independent refund/reversal comparator. Bank readback remains a separate plane.
- Inputs: synthetic month of contracts/orders/usage/invoices/credits/payments/journals with duplicate charge, lost success webhook, unknown provider result, post-effect worker death, transport-level response loss, refund request response-loss, cumulative refund resend without signed child, partial then full refund, outbox failure, period-lock fault, provider-native invoice/application evidence, bank-observed payment and later external return/chargeback.
- Success: provider timeout remains UNKNOWN/PENDING; one-shot side effect cannot be blindly retried; process restart preserves one effect identity; provider inquiry/counter-event can repair missed webhook state; only confirmed amount/currency delta can post the compensating ledger entry; the correction is applied exactly once by provider accounting when applicable; operational/accounting/provider/bank states remain separately replayable; later bank return can reopen/offset canonical money state without erasing original authority.
- Failure: outbound refund/credit request becomes accounting truth, timeout becomes safe failure/retry, cumulative provider total creates money without a confirmed child event, provider object existence is mistaken for economic application, provider invoice application is mislabeled bank settlement, one system grades its own settlement as external truth, or later return cannot invalidate prior success.
- Next action: run the Paymob/OpenPartner/Summae/Interlock/bank-observation patterns against one canonical synthetic month. Reproduce the Interlock after-send crash/application fixture independently or author an equivalent golden, then extend it past provider accounting to an independently observed bank/processor return/finality plane. Provider qualification harnesses count only when retained successful exact-revision provider evidence exists; `NOT_EXERCISED` remains unqualified.

### EXP-011 — Subrogation rule-and-quantum fail-closed benchmark
- Opportunity: Insurance Subrogation Recovery Diagnostic.
- Capabilities: CAP-001, 006, 007.
- Status: **READY** synthetic; **BLOCKED_EXTERNAL** commercial.
- Hypothesis: recovery opportunities can be prioritized safely only when jurisdiction/policy authority is explicit, versioned and fail-closed.
- Inputs: synthetic paid-loss facts, fault regimes, policy limits, made-whole/deductible handling, limitations periods, missing/conflicting/superseded authority and synthetic settlement outcomes.
- Success: exact supported quantum; every unknown/conflicting/missing authority = REVIEW/$0; settlement remains distinct from calculated opportunity.
- Failure: illustrative/default legal rule or model output creates hard-dollar assertion.
- Next action: complete explicit synthetic rule-pack benchmark before any customer claim period.

### EXP-012 — Outcome-priced grid resilience calibration
- Opportunity: Grid/Infrastructure Risk & Inspection.
- Capabilities: CAP-015 plus optimization/routing components.
- Status: **READY with artifact-byte gate**.
- Hypothesis: a resilience policy can demonstrate same-input advantage only when evaluator ancestry, construct, grouping and independence are explicit and predictions are frozen before prospective challenge.
- Historical plane: USECPO v2 is CC BY 4.0. The 2025 IEEE descriptor establishes the event-correlated logical schema and literal `event id` as the associated-event key. Whole-event blocking must use `event id`; all rows sharing an event stay in one split; chronology is preserved. `{STANDARD, LAG_8H, LAG_24H}` are evaluator variants/sensitivity analyses, **not independent evidence**. Record ancestry `EAGLE-I + DOE-417`, county-explicit vs state-generalized geography and restoration provenance/imputation.
- Scope limits: USECPO is conditioned on major/transmission events and is not general distribution-system or asset-causal truth. Early coverage is weaker; prefer **2019–2023** for the first high-confidence historical benchmark. Missing restoration time may be imputed to event start and must never be interpreted as measured instant restoration.
- Artifact gate still open: current v2 ZIP/guideline bytes were rate-limited during hunter inspection, so exact filenames/header casing/order, timezone, null/sentinel values, threshold defaults, any direct quality flags and whether `event id` is globally unique across years remain UNVERIFIED until the official artifact is read.
- Independent/challenge plane: rights-permitted regulator/utility evidence plus post-freeze public-domain prospective feeds. NYC 311 is only a construct-validity negative control; related EAGLE-I descendants cannot count as independent validation.
- Success: model/policy beats simple baselines on frozen same-event outcomes without leakage; evaluator lineage/construct and imputation flags are explicit; variants are sensitivity views only; modeled interruption dollars remain separate from observed outage outcome.
- Failure: row-level/random split leaks one physical event across train/test, lag variants are counted as independent votes, state-generalized geography becomes county-precise truth, imputed restoration becomes observed outcome, or event correlation becomes feeder/component causality.
- Next action: obtain the official v2 ZIP/guideline, byte-confirm headers/timezone/sentinels/thresholds and event-id namespace, then freeze event-level 2019–2023 splits and simple-vs-optimized comparisons. Search another outage dataset only if a genuinely independent rights-clear oracle remains necessary.

## Portfolio rule
Do not start another product build because a repository is exciting. New search/build effort must close a named experiment gap, create a cheaper falsifier, or respond to a recorded outcome. When an experiment completes, mirror it in `OUTCOMES.md` and `intelligence/outcomes.jsonl` with originating search-run/capability links.