# Hunt 13 R12 — ACH transfer finality / return lineage

Discovery date: 2026-09-20
Lane: Revenue Leverage / Partner & Commission Payout Assurance / EXP-003
Baseline ledger head read immediately before write: `a781b553d4b581e4a0d742a14e67fb303306de7f`

## BEST NEW FIND — Increase ACH transfer lifecycle

- Repository: `Increase/increase-python`
- Exact revision: `8ddc546dadd41bc010b57981692965c22f01f54d` (release 0.544.0, 2026-09-17)
- Public license: Apache-2.0. Commercial Increase API/service access and banking-service terms remain separately governed; repository authorization does not grant them.
- Score: **27/30 — A4 B5 C5 D5 E4 F4**.
- Classification: **STRONG / MASTER referral candidate; provider-specific component, not a full bank-independent finality oracle.**

### Concrete capability verified
Increase exposes a unusually complete ACH money-state chain on one transfer resource:

1. `ACHTransfer.id` provides stable provider transfer identity.
2. `idempotency_key` is persisted and documented as globally unique within Increase for ensuring a request is processed once.
3. `submission.trace_number` is the 15-digit trace recorded in the Nacha file and transmitted to the receiving bank; the model explicitly says amount/date/originating routing number plus trace can identify the transfer at the receiving bank and that the trace is used to correlate returns.
4. `settlement.settled_at` records when funds settled at the destination bank at the Federal Reserve.
5. Critically, settlement does **not** turn the lifecycle into an irreversible success bit: the transfer status remains `submitted` when the settlement sub-object is populated, and later may become `returned`.
6. The `return` sub-object carries the return `raw_return_reason_code`, normalized return reason, the return's own (different) 15-digit trace number, the return transaction ID, and the original `transfer_id`.
7. First-party documentation says Increase automatically reconciles ACH returns and originating ACH transfers; returns can be correlated with date, amount, account, routing number and trace, and trace number alone is not unique enough for large institutions.
8. First-party lifecycle documentation shows one ACH Transfer object producing the original debit Transaction at settlement and a second credit Transaction if the receiving bank later returns it.

### Verification beyond README
Inspected exact-revision generated source:
- `src/increase/types/ach_transfer.py`: Return, Settlement, Submission and ACHTransfer models, including original trace, return trace, return reason codes, idempotency key, settlement timestamp and `returned` state.
- `src/increase/resources/simulations/ach_transfers.py`: sandbox endpoints to submit, acknowledge, settle and explicitly simulate an ACH return with a chosen Nacha return reason; the return simulator states that it also creates the Transaction that accounts for returned funds.
- `tests/api_resources/simulations/test_ach_transfers.py`: generated contract tests exercise `return_()` with a return reason and `settle()` paths and assert typed ACHTransfer responses.
- `tests/api_resources/test_ach_transfers.py`: create/retrieve/list/approve/cancel resource tests, including client idempotency-key/list surface.
- `LICENSE`: Apache-2.0.

External first-party docs checked 2026-09-20:
- Increase ACH returns: explicitly says return correlation must use multiple fields because ACH trace numbers are not globally unique; Increase automatically reconciles returns and transfers; late returns can occur.
- Increase transactions/transfers: shows the same transfer settling, creating a debit transaction, and later creating a second credit transaction when returned.
- Increase sending ACH transfers: documents sandbox return simulation and notifications-of-change after settlement.

### Strongest objection / red-team
- This is **provider-origin evidence**, not an independently imported beneficiary-bank statement. Increase is the bank/API layer observing its own originated ACH, so it materially strengthens finality semantics but does not by itself prove a separate recipient-bank statement contains the expected deposit.
- ACH is USD-only in this model; it does not solve final FX-settled amount/currency for cross-border rails.
- Generated SDK tests are API-contract/mock tests rather than an independent FedACH execution. Production semantics are supported by Increase's current first-party documentation, but a real customer-authorized closed-period comparison remains needed.
- The model explicitly warns that trace numbers are not unique; any external readback join must use the composite economic identity, not trace alone.

### Commercial implication
This materially upgrades the Partner / Commission Payout Acceptance Test from `provider says paid` to a state model closer to:

`expected commission -> idempotent ACH transfer -> Nacha trace -> FedACH settlement timestamp -> later receiving-bank return -> explicit offsetting transaction`.

A paid diagnostic can now classify dollars into `not submitted / submitted-unsettled / settled / returned` instead of collapsing them into paid/unpaid, and can measure unsafe duplicate reissues, post-success returns and finance-review labor.

### Capability / graph / experiment handoff
- **CAPABILITY DELTA:** CAP-018 gains a provider-native `original transfer ID + original Nacha trace + settlement timestamp + later return + return trace + offsetting transaction` primitive.
- **GRAPH EDGE:** `Increase/increase-python@8ddc546d...` -> STRENGTHENS CAP-018 -> ENABLES Partner / Commission Payout Assurance -> TESTED_BY EXP-003.
- **RADAR SIGNAL:** Strengthens RAD-006 Authority-aware money assurance and the emerging "revocable money finality" pattern.
- **EXPERIMENT IMPACT:** EXP-003 should add: submitted-but-not-yet-settled; settled-at-FedACH then returned next day; late return; duplicate-return reason; trace-number-error (R27); equal trace with wrong amount/date; and return replay/idempotency cases. Success must never treat `settled_at` as permanently final.
- **COMMERCIAL IMPACT:** Adds measurable post-success loss/recovery exposure and reduces ambiguity around whether a payout actually entered/left the ACH network.
- **NEGATIVE KNOWLEDGE:** ACH trace number alone is not a unique settlement key; a `settled_at` timestamp alone is not permanent finality; provider-native evidence still requires independent readback for a buyer-grade acceptance proof.

## OTHER STRONG CANDIDATE — Adyen transfer tracing + returned lifecycle

- Repository: `Adyen/adyen-go-api-library`
- Exact revision: `91a97e53ca75e4df4a7e3db346bd27d982e08965` (2026-09-09)
- Corroborating official spec: `Adyen/adyen-openapi@da8325981e81e122d15036c36c00f395488d3131` (2026-09-16)
- Public SDK license: MIT. Adyen API/service access and terms are separately governed.
- Score: **26/30 — A4 B5 C5 D4 E4 F4**.

### Verified capability
- Exact SDK source defines `USAchTracingData.traceNumber` as a unique 15-digit ACH identifier and types it as `usAch`.
- `TransferData` contains stable transfer `id`, `events`, `sequenceNumber`, `status`, `tracing`, `networkReason`, amount/category/direction and references.
- The source documentation for `sequenceNumber` says it increases with each webhook for a transfer and can be used to restore correct event order when webhooks arrive out of order.
- The exact SDK source documents `failed` as rejection by the counterparty bank and `returned` as funds returned by the counterparty bank.
- Current first-party Adyen documentation says outbound bank transfers emit a `tracing` event when funds leave Adyen, with US ACH `traceNumber`; `booked` is explicitly non-final; and a transfer may later become `returned`, at which point funds are credited back and a separate accounting-report entry is recorded.

### Why it matters
This independently validates the same semantic pattern in a second production payment platform: network trace data is a first-class event, booked is not final, and later return is a distinct state/counter-event. It also adds explicit webhook event sequencing, which is useful for out-of-order callback acceptance tests.

### Strongest objection
Still provider-origin evidence; does not independently import beneficiary-bank truth. No semantic return/tracing tests were found in the generated SDK during this pass, so evidence quality is one point below fully independently replayed behavior.

## WATCH / NEGATIVE ORACLES

### purposestack/givernance@2567603f9549a47cfe58903f67c75be733e8c77a
Useful architecture but not promoted. The repository contains a detailed CAMT.053 design, schema/migration foundation and explicit idempotency key using statement ID + `AcctSvcrRef` (+ EndToEndId), raw-statement retention and an unmatched queue. However, the searched tree did not surface the promised `camt-import.ts` implementation; much of the strongest behavior remains ADR/design text. Treat as **PLANNED/FOUNDATION**, not as proof that independent statement ingestion already works.

### ForwardFinancing/ach_client@7c8dca104f2299e6edad4013fb9c475d9b93e99f
Useful legacy/multi-provider negative oracle. It formalizes `external_ach_id` persistence and later provider polling, and even special-cases a provider that returns an immediate ACH rejection before assigning an external ID. This supports the thesis that send-success and later provider response are separate states, but it does not close network-trace/bank-readback identity and depends on provider-specific adapters. Do not promote over Increase/Adyen.

## COMBINATION

Strongest current EXP-003 settlement chain:

`historical commission authority/entitlement` -> `claim/idempotency & ambiguous-send protection (Spree/chase-sets)` -> `provider transfer identity` -> `Increase or Adyen network ACH trace` -> `provider-reported FedACH settlement / booked lifecycle` -> `independent statement readback (CAMT/MT940/OFX)` -> `later ACH return/reversal (Increase return object / moov-io/ach)` -> `negative carry-forward / receivable if commission already paid`.

The new result does **not** justify collapsing the last two planes. Provider-native settlement evidence and independently sourced bank-statement evidence must stay separate.

## CLAIMS TESTED

1. **"ACH trace alone uniquely identifies a payout" — FALSIFIED.** Increase explicitly warns trace numbers are not unique and recommends combining trace with amount/date/account/routing context.
2. **"FedACH settlement is irreversible finality" — FALSIFIED.** Increase models `settlement.settled_at` while keeping the transfer capable of later becoming `returned`; current docs show a later offsetting transaction.
3. **"Booked/provider-paid is final" — FALSIFIED independently by Adyen.** Current Adyen docs explicitly say booked is non-final and regular/wire transfers may later be returned.
4. **"Provider can expose an exact ACH network identifier before a later return" — VERIFIED in two independent first-party API families (Increase and Adyen).**
5. **"We now have independent beneficiary-bank proof" — NOT VERIFIED.** That remains the missing edge.

## EMERGING TECHNOLOGY SIGNAL

Independent providers are converging on a richer money lifecycle than `pending -> paid`: stable transfer ID -> network trace -> settlement/booked observation -> later returned/counter-event. This materially strengthens the "revocable money finality" subpattern within RAD-006 without changing its score absent customer outcome evidence.

## SEARCH POLICY UPDATE / REUSABLE SKILL CANDIDATE

**SKILL NAME:** First-party rail-lifecycle triangulation

**WHEN TO USE:** A provider/payment repository appears to expose a success/settlement state that may not be economically final.

**PROCEDURE:**
1. Start from the money-bearing state transition, not product terms (`settled`, `booked`, `returned`, `traceNumber`, `OriginalTrace`).
2. Inspect the provider's generated SDK model at an exact revision.
3. Cross-check the official OpenAPI/schema if available.
4. Cross-check current first-party operational docs for what the state means in the banking network.
5. Search sandbox/simulation endpoints and tests for negative transitions (settle -> return, failure, duplicate, late event).
6. Preserve provider-native evidence separately from independently imported bank evidence.

**WHY IT WORKED:** It surfaced semantics hidden behind generic "payout complete" language: real rail identifiers, non-final booked/settled states and later counter-events.

**FAILURE MODES:** Generated SDK tests may only validate HTTP/schema contracts; provider documentation may not prove a beneficiary-bank observation; trace values may not be globally unique.

**NEXT IMPROVEMENT:** Search receiving-bank/ERP connectors for a deterministic composite join consuming the provider's trace plus amount/date/routing and explicitly proving feed freshness/completeness.

## NEXT HIGHEST-VALUE QUESTION

Can we find a production implementation that consumes an Increase/Adyen/Stripe ACH trace plus amount/date/routing and joins it to an independently sourced bank statement/return feed with explicit freshness/completeness, while rejecting ambiguous duplicate matches rather than declaring success?
