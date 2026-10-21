# RETALLY seven-branch engineering delivery

Scope: Freight, AP, Warranty/Credit, Procurement, Rebate, Parcel, Utility.

**Follow-up:** [WORKBENCH.md](WORKBENCH.md) documents the subsequent implementation:
private role-scoped UI, mapped intake, case revision/hold release, partial cash and fee
reversals, full workspace backup/replay, dimensional parcel rating, procurement unit
conversion, and seven simulated customer journeys. The remaining-work list below
records the earlier delivery baseline; the follow-up acceptance table is current.

This delivery hardens existing ingestion and calculations and adds an evidence-bound launch review. It does **not** establish seven customer-ready businesses. No authorized customer records, production operating evidence, or independent competitive benchmark were supplied for this change.

## Implemented

| Branch | Change | Supported boundary / next requirement |
|---|---|---|
| Freight | Shared economic-case protection; preserve shipment and business-unit identity | Existing freight proof and authorization workflow retained. Multiple charge components on the same shipment/invoice need explicit economic identity reconciliation. |
| AP | Preserve invoice suffix identity; suppress conflicting statement groups; net explicitly linked refunds against payments | No fuzzy suffix matching as proof. Refunds require original payments in the same invoice scope. |
| Warranty/Credit | Signed reversal lineage; restricted settlement kinds; aggregate reversal bounds | Credit memo evidence is entitlement settlement, not proof of cash received. Final cash remains separately reconciled in the recovery ledger. |
| Procurement | Preserve decimal unit price through quantity extension; reject nonfinite values | Same-unit price/quantity scope only. UOM conversions, taxes, freight allocation and cumulative receipts need explicit contract models. |
| Rebate | Explicit return restatement policy; original purchase lineage; signed settlements; optional due-date/as-of gate | Due date absent preserves legacy behavior, so a launch reviewer must establish timing. Other return policies are unsupported. |
| Parcel | Reject nonfinite weights and money | Still uses independently reviewed rate assessments. Automated carrier contract rating, dimensions, fuel and surcharges remain future work. |
| Utility | Quarantine repeated bill identities before calculation; finite quantities | Supported tariff components only. Corrected bills need reconciliation; duplicates are not silently selected. |

Shared economic identity excludes evidence hashes. A changed proof cannot silently add another case with the same scoped identity. Explicit `economic_loss_id` metadata can identify a loss across branches; this requires reviewed mapping and is not inferred. A conflict places the existing case on a durable reconciliation hold. Approvals, authorizations, claims and recovery posting are blocked while held, and future scans continue to report the hold. Historical records and their hashes are preserved. Hold release and reviewed case revision are not implemented; do not bypass holds by editing stored state. Reported historical dollar totals remain historical, not an assertion that a held case is currently actionable.

The guard is deliberately conservative: components sharing a reference may require reconciliation. Before upgrading an existing private ledger, back it up and replay a copy with the new version. Historical journals containing economic duplicates will fail closed; do not delete journal entries or rewrite hashes to bypass the check. Reconcile through a reviewed migration before deployment. Even rejected cases reserve their identity.

## Private launch review dashboard

```
python -m recoveryworks.portfolio_readiness init --client CLIENT --manifest /private/client/launch.json
python -m recoveryworks.portfolio_readiness check --manifest /private/client/launch.json --report /private/client/readiness.json --html /private/client/readiness.html
```

The check exits 2 when any branch is blocked. Open the HTML locally. It has no scripts, external resources, or outbound requests. Outputs use the existing private atomic writer.

Each branch needs evidence for authorized scope, source completeness, rule review, unseen-case benchmark, overlap review, customer workflow, security/restore, realized recovery, and unit economics. Reviews bind an exact local evidence file by SHA-256, record scope and review time, and require distinct reviewer identifiers. A changed file invalidates the recorded check. Identifiers are self-reported, not authenticated signatures; the checker verifies records and integrity, not the truth or independence of assertions. It never grants claim authority or commercial certification.

For source completeness, attach a signed-off reconciliation containing source system, account/period/currency coverage, row counts, control totals, exclusions, reversal coverage and the original export hashes. Benchmark evidence must include held-out customer cases with independently labeled correct results, false positive/negative counts, dollar-weighted errors and every unsupported case. Do not use synthetic unit tests as customer proof.

## Input additions

- AP payments: optional `Reverses_ID`; a negative amount requires its original positive payment and dates.
- Warranty/Credit settlements: optional `Reverses_ID`; negative rows require `Settlement_Kind=REVERSAL`. Supported kinds: CREDIT_MEMO, APPLIED_CREDIT, CASH_REFUND, REVERSAL, ZERO_CONFIRMED. ZERO_CONFIRMED must be zero.
- Rebate purchases: optional `Return_Of_Purchase_ID`; return quantity and spend are nonpositive and cannot exceed the original totals.
- Rebate programs: optional `return_policy="restates_original_purchase"`, `payment_due_date="YYYY-MM-DD"`.
- Rebate settlements: optional `Reverses_ID`; scan rebate job accepts `as_of_date` for the due-date gate.
- Procurement: `Contracted_Unit_Price` retains decimal precision; final extended amount is rounded to cents.

## Remaining launch work

1. Implement durable reviewed case revision and hold releases, post-recovery reversals, partial settlements, fee reversals, and explicit cross-branch allocation.
2. Add authenticated customer onboarding, upload/column mapping, account scope, review queue, approval UX, and reconciliation UX. Existing operator CLI and this read-only dashboard do not fulfill that product surface.
3. Complete each branch's unsupported calculation scope above; add authoritative integrations only against actual contracted customer systems.
4. Test tenant isolation, restore drills, deletion/retention, monitoring, support operations and production deployment evidence.
5. Run authorized pilots, independently review held-out results and reconcile real recovered funds and delivery costs. Release branches separately when their evidence supports release.

Industry leadership is an empirical target: compare net realized recovery, false claim rate, time to first verified finding, time to cash and operator minutes per recovery against the customer's incumbent on the same unseen population. No superiority claim is made here.
