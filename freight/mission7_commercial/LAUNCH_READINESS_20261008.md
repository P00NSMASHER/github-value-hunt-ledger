# RETALLY Mission 7: Commercial launch and customer acceptance

**Evidence date:** 2026-10-08. **Status:** Review only. **Decision:** NOT READY for unrestricted customer intake, hosted financial processing, provider/bank actions, or automated recovery.

This release register is a commercial acceptance **layer**, not another freestanding freight audit engine. Existing owner and evidence protocols remain authoritative. Do not merge or deploy any production financial repair merely because this document is merged.

## Initial controlled offer

- Target: U.S. multi-site industrial distributors with **domestic USD LTL** invoices, a real finance decision owner, auditable contracts, a reliable incumbent/known-credit export, and carrier claims still within applicable time windows.
- Proposed first pilot cap: one legal entity/business unit, up to **25 already-paid invoices**, **two carriers**, and approved labor-hour budget. Numbers are starting hypotheses, not contractual promises; determine actual scope with the buyer.
- Initial qualification: non-sensitive business metadata and at most 60 minutes of pre-engagement review. Never accept confidential freight documents through the public marketing contact path.
- The free review does not authorize carrier contact. Every claim or explicit bounded claim batch needs customer approval and approved correspondence. No success fee on candidate, validated, submitted, accepted, or merely asserted settlement values.
- Primary deliverable: source-bound correct-charge calculation, independent review, suppression of incumbent/automatic/previously recovered matters, precise customer authority, and **customer-ledger-confirmed** posted cash/usable credit net of reversals.
- Use a specifically approved **single-tenant manual data path** until production financial integrity and hosted acceptance are independently established. Avoid automatic payment/provider calls and any funds custody.

## Reconciled cross-mission evidence (P0-P3)

| ID | Priority | Verified condition / evidence boundary | Work to close | Accept only with |
|---|---|---|---|---|
| M7-01 | P0 | Floot payment_prepare sums confirmed variances on an unlocked snapshot. [Draft SQL remediation #299](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/299) is isolated staging, **not wired to production**. | Atomic allocation reservation, cross-tenant/currency and economic-identity conservation, full idempotency binding, safe migration. | Reproduced before/after races against a production-representative isolated Postgres clone, concurrency and rollback proof. |
| M7-02 | P0 | Payment event `SETTLED` and self-described sources do not by themselves prove buyer funds; fee-eligibility production verification remains incomplete. | Source-bound buyer AP posting + carrier refund/credit verification, reversal-aware controls. | Independently matched financial postings and fee reconciliation with negative tests. |
| M7-03 | P0 | Legal entity, negotiated recovery rate, DPA, standing and carrier time limitations unconfirmed. | Counsel-reviewed signed agreements; dated claim-specific mandate. | Executed legal terms and actual named approvers. |
| M7-04 | P0 | A September 21 control pack records verified **single-tenant manual** environment through December 20 absent changes; this is not buyer-specific approval. | Fresh workspace/device/access/retention evidence and buyer IT approval. | [Pilot launch gate](../PILOT_LAUNCH_GATE.md) READY for the real buyer and exact transfer route. |
| M7-05 | P0 | Company email inbound receipt and actual custom-domain deployment acceptance have not been independently documented for this mission. | Test public HTTPS + actual inbound contact inbox + safe lead handling. | Recorded verified delivery, no attachments, current source parity. |
| M7-06 | P1 | Independent qualified freight reviewer and available paid hours not established. | Name reviewer, confirm competency and conflict controls. | Dated second-person re-rating of the governing effective rate. |
| M7-07 | P1 | No real externally attested RETALLY customer recovery or contribution result available. | Permissioned small customer pilot with full source and time record. | Buyer-accepted posted recovery, exclusions, and fee/margin evidence. |
| M7-08 | P1 | Website [#298](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/298) and collateral [#300](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/300) have concurrent, unmerged candidate work. | Review actual rendered changes; do not overwrite their branches. | Screenshot QA, documented content semantics and release signoff. |
| M7-09 | P1 | Cloudflare project is configured for domain hostnames; deployment result needs independent production proof. | Check actual deployment, public URL, canonical, redirects and rollback. | Confirmed served release and source hash/commit. |
| M7-10 | P2 | Fee percentage, hours, lead conversion and actual settlement timing unknown. | Measure real service cost; calculate contribution including failed free reviews and acquisition. | Signed commercial rate plus observed accounting/time records. |
| M7-11 | P2 | Google Search Console property recently activated; settled indexed/ranking baseline incomplete. | Measure nonbranded search and qualified inquiry pipeline. | Google/Search Console data mature enough to support trends. |
| M7-12 | P3 | Enterprise FAP, global transport modes and predictive automation remain scope expansion. | Defer. | Positive repeatable LTL engagements and accepted security/financial controls. |

## Existing operating controls and source of truth

- [SECOND_LOOK_RECOVERY_AUDIT.md](../SECOND_LOOK_RECOVERY_AUDIT.md): frozen population, incumbent exclusion, buyer authorization, net-new claim attribution.
- [COMMERCIAL_QUALIFICATION.md](../COMMERCIAL_QUALIFICATION.md): capped free review, customer qualification and fully loaded economics.
- [CUSTOMER_CONTROLLED_PILOT.md](../CUSTOMER_CONTROLLED_PILOT.md): evidence-backed approved single-tenant manual route.
- [PILOT_LAUNCH_GATE.md](../PILOT_LAUNCH_GATE.md): exact customer/environment prerequisites.
- [RETALLY_ENGAGEMENT_COVER_TEMPLATE.md](../brand/RETALLY_ENGAGEMENT_COVER_TEMPLATE.md) and [RETALLY_PRICING_SCOPE_SUMMARY.md](../brand/RETALLY_PRICING_SCOPE_SUMMARY.md): nonbinding working terms and fee disclosure.
- [Production-integrity candidate PR #299](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/299): staging evidence only.
- [14-lab Phase 4 PR #297](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/297): bounded synthetic pathways, not recovery certification; original 26 remain open.
- [Independent business viability audit, October 8](https://retallyrecovery.com/): analyst rating 42/100, not measured production efficacy or actual customer profitability. Separate native report retained outside repository; this homepage link is context, not a hosted audit copy.

## Acceptance sequence and go/no-go

1. Discovery may proceed using **non-sensitive metadata** only; do not ask for actual invoices by regular email or website contact form.
2. Before customer records transfer, confirm the buyer-specific legal authority, secure exact data path, named reviewer, effective contracts, company identity and finite staff-hour cap. Failing any P0 remains NO-GO.
3. Use manual approved controls for pilot cases. Record the dated independent re-rating and signed carrier correspondence authority, not a generic workflow click.
4. A carrier response is **not** cash. Only buyer-ledger-confirmed attributable net posted refunds or usable credits, after reversals and prior/known suppression, enter the signed fee base.
5. Production RecoveryOS payment/settlement flows stay **disabled from live use** until M7-01 and M7-02 have independent real-application acceptance; unrelated Floot or site styling changes do not discharge the gate.
6. General commercial launch requires demonstrated actual positive contribution, signed references or permissioned evidence, measured work hours, safe data handling and reliable lead/contact operations.

**Final status 2026-10-08:** **NOT READY, WITH CLEAR BLOCKING DEFECTS.** This does not prohibit founder-led conversations or preparation for a manually controlled future pilot, but it blocks processing confidential buyer records or presenting production software recovery results until the relevant gates have passed.

**Evidence caution:** Repo plans and synthetic tests establish intent or bounded correctness of those tests. They do not attest external bank/carrier reality, complete staged environment controls, customer outcomes, website deployment, legal advice, or actual profits.
