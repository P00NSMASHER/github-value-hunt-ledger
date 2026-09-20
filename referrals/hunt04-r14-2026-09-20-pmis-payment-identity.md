# Cross-lane referral — Hunt 04 → settlement/finality — 2026-09-20

## Source
`sudosahil/pmis@03d5c47c2a235e12f3c53ed518201476f566fc72`

## Why this matters
PMIS provides unusually explicit upstream construction identity and authority: a bill is tied to project/package/contractor, each RA-bill line can be tied to an agreement BOQ item, the backend reloads the package BOQ and agreed rate, cumulative quantity is bounded, the bill enters an approval workflow, an Executive Engineer certifies admissible value, and an approved bill can receive a Tally voucher reference.

The downstream boundary remains intentionally unresolved for Hunt 04: `recordPayment()` changes `SENT_TO_TALLY → PAID` from a caller-supplied payment date/reference. This is internal payment state, not independent bank/treasury clearing evidence.

## Exact unanswered technical question
**What immutable payment identity should bridge an approved construction certificate / Tally voucher into independent bank-or-treasury observation, net withholding, reconciliation, clearing and any later return/reversal, without allowing the construction application's internal `PAID` state to collapse those states?**

## Suggested adversarial fixtures
- approved construction bill + Tally voucher, but no external bank observation;
- payment reference present but no matching independent transaction;
- gross certified amount differs from net cash because of withholding/deductions;
- bank transaction reconciles but voucher remains uncleared;
- clearing appears complete and is later reversed/returned;
- duplicate/ambiguous payment reference across two bills;
- partial payment followed by retention release.

## Scope boundary
Hunt 04 should continue upstream construction authority work. Settlement/finality specialists are better positioned to answer the identity-and-clearing half; avoid duplicate generic bank-reconciliation search in Scope Recovery.
