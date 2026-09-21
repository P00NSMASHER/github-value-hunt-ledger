# Hunt 09 Referral — Phase-Qualified Negative Outcome Receipts

## To
- AP / finance assurance lane
- Money-state / settlement lane
- MASTER Integrator
- Freight Recovery lane (SAP TM sub-referral)

## Finding
Run 23 found a stronger rule for external financial writeback: **provider `FAILED` is not enough for `NOT_APPLIED`; negative proof must be phase-qualified and effect-scoped.**

Two independent ERP families support the distinction:

1. **Microsoft Dynamics 365 Finance & Operations recurring integrations** expose `PreProcessingError` (failure in preprocessing stage) separately from `Processing`, `ProcessedWithErrors`, and `PostProcessingFailed`, with durable `messageId -> executionId` lookup and execution errors. Current Microsoft docs and official `microsoft/Dynamics-AX-Integration@fef1173a479968dcf79bce5a5f7e93dc74c2d0d1` sample verify the execution-ID/status workflow. Microsoft also documents partial imports and per-record failure artifacts, proving job-level failure is not sufficient by itself.

2. **SAP S/4HANA Supplier Invoice async inbound** separates posting success/error, AIF request cancellation, and outbound status/error notifications. Current status models distinguish Processing / Reconciled / Rejected / Canceled and structured log messages. SAP documentation also distinguishes invoices saved with errors/not posted from posted/reconciled invoices.

## Recommended graph / capability update
Add these provider-registry fields:
- `provider_phase`
- `effect_scope` (whole operation vs item/record)
- `partial_effect_possible`
- `negative_proof_rule`

Require adapters to emit a `ProviderOutcomeReceipt` carrying exact operation identity, phase, terminal state, scope, provenance and APPLIED / proven NOT_APPLIED / UNKNOWN classification.

## EXP-002 tests to add
1. `PreProcessingError` with exact operation/message identity => may classify `NOT_APPLIED` only when provider contract proves target/apply phase was never entered.
2. `ProcessedWithErrors` => must remain UNKNOWN until every target record/effect is reconciled.
3. `PostProcessingFailed` => must not free authority automatically.
4. Generic `Failed` with possible partial effects => UNKNOWN.
5. `Canceled` without evidence that the original request was canceled before posting => UNKNOWN.
6. Exact pre-posting rejection/cancellation receipt => release reserved reverse capacity only for the exact correlated effect.

## Freight Recovery sub-referral
SAP Transportation Management documents carrier-invoice states that separate `Rejected` before MM posting / `Invoice Posting Failed` from `Carrier invoice posted`. Investigate whether an API or status-notification path exposes these states with durable identity suitable for controlled freight writeback or settlement proof.

## Exact unanswered question
**Which real vendor-credit or financial-reversal endpoint exposes a durable queryable operation identity and a terminal provider state that explicitly proves the exact mutation was rejected before posting, with no possible partial financial effect?**

## Source run
`hunters/16-run23-2026-09-20.md`
