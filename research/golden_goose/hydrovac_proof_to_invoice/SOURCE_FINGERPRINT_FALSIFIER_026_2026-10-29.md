# Golden Goose independent iteration #026: source-byte identity falsifier (2026-10-29 EDT)

**Disposition:** Generic hydrovac reconciliation **NO-GO**; independent contract-specific second-look **WATCH / commercially unvalidated**. Research-only on existing draft PR #870 and ledger #863. No worker leases, priority changes or protected-main release.

## Fresh official evidence and competition

- [Peppol PINT invoice line specification (2026)](https://docs.peppol.eu/poac/pint/pint/trn-invoice/semantic-model/ibg-25/) says a line identifier is unique *within an invoice*. [Invoice semantic model](https://docs.peppol.eu/poac/pint/pint/trn-invoice/semantic-model/) separately defines seller, document number and previous-invoice references. These are format comparisons, not binding U.S. hydrovac contract terms.
- [NIST hash-function guidance](https://csrc.nist.gov/projects/hash-functions) defines SHA-256 as a supplied-message digest. [NIST FIPS 186-5](https://www.nist.gov/publications/digital-signature-standard-dss-3) describes signatures for signatory authentication. A locally matching SHA-256 claimed beside user-supplied bytes does **not** establish who issued the bytes or whether they were authorized.
- [FortressTicket](https://fortressticket.com/), [Aimsio](https://aimsio.com/industries/hydrovac/) and [TicketClerks](https://ticketclerks.com/) advertise overlapping capture and invoice controls. These are vendor claims, not independently validated performance or willingness to pay us.
- A distinct public-bid-change alert opportunity remains **NO-GO** until buyer demand is independently supported. [Worcester 2026 vacuum excavation bid](https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6) identifies a procurement comparison, not any customer's collectible balance.

## Testable hypothesis and actual build

Can an offline diagnostic flag: repeated locally numbered lines under the *same* asserted invoice, distinct invoice versions with conflicting source bytes, and identical source bytes relabeled under different invoice IDs, **without declaring a payment or source authenticity**?

**Built in existing draft branch:** [source_fingerprint_026.js](./source_fingerprint_026.js) computes SHA-256 over supplied entirely synthetic document bytes, checks claimed digest matches, validates strict schemas and complete expected-job coverage, and emits review-only flags. [test_source_fingerprint_026.js](./test_source_fingerprint_026.js) contains **28 adversarial synthetic cases across 100 jobs**, covering split documents, case-sensitive refs, same-document reuse, version conflicts, digest/byte tampering, duplicate/foreign jobs, invalid base64, oversized evidence, unknown verification claims and forged money fields. [CI gate](../../../tests/test_ti_golden_goose_hydrovac_integration_022.py) now runs the new Node test.

**Actually tested:** Node 22.16.0 local **28/28 passed**. The locally tested files match GitHub-readback Git blob hashes: module 7b58defa2d69cb8462f3a694c65a6038c6033dd3 and test 3405533036a30b27e4975a1b3de417870d255b49. The existing global REVIEW bridge has not been changed or cleared. Final exact-head CI completion must be checked separately.

**Adversarial limitation:** Forged bytes with an attacker-computed matching hash pass the integrity comparison. The tool therefore always reports document_authenticity_verified=false, signatory_verified=false, financial_clearance_allowed=false, verified_collectible_usd=null and verified_owner_revenue_usd=0.00. A repeated hash is only a review lead and not proof of double billing.

## Economics and rejection criteria

Under deliberately arbitrary assumptions, 100 jobs x 5 reviewer minutes x $35/hour = **$291.67** review labor. A hypothetical $100 report fee less $10 overhead leaves a **2.571-hour** labor budget at that wage, before acquisition and taxes. Zero actual labor savings or willing buyers have been established.

The earlier **fictional $4,940 variance**, lawsuit settlement pools, published contract totals and overall markets are NOT collectible revenue. No independently verified signed terms, invoice provenance, post-bill credits, incumbent comparison, real review-time study or buyer authorization exists.

**Exact status:** owner revenue **$0**; verified collectible **$0**; paying customers **0**; authorized real invoices **0**; real incumbent comparisons **0**. No spending, outreach, filings, trades, customer data, production deployment, protected-main merge, other automation change, worker lease or Work credits.

**Next:** Check final-head CI; add a synthetic co-forgery test demonstrating matching hashes cannot prove origin, then, only after fresh express approval, blinded customer-authorized incumbent comparison. Stop this niche if source authority or incremental legitimate savings do not survive independent review.
