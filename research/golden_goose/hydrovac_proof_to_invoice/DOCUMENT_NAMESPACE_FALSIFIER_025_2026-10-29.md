# Golden Goose #025 — invoice-document namespace falsifier (2026-10-29 EDT)

**Disposition:** Generic invoice software **NO-GO**; contract-specific independent proof-to-invoice second-look remains **WATCH / commercially unvalidated**. Unclaimed research on existing **DRAFT PR #870**, not a generated hunter lease or integrator promotion. No protection/main, other automation, billing account, or live customer data changed.

## New official evidence, and the applicability boundary

The [May 2026 Peppol BIS Billing 3.0 UBL invoice structure](https://test-docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/tree/) identifies the invoice number at document level as an identifier within the seller's business context, and the `InvoiceLine/cbc:ID` as an identifier for the individual line **within the invoice**. The [Peppol PINT line-ID binding](https://docs.peppol.eu/poac/pint/pint/trn-invoice/syntax/cac-InvoiceLine/cbc-ID/) likewise says "within the Invoice." That **falsifies assuming global uniqueness of a bare line number** in an e-invoice-format comparator. It does **not** prove this format governs U.S. hydrovac tickets or that a supplied seller, invoice, or line ID is authentic.

The U.S. [FAR 32.905(b)](https://www.acquisition.gov/far/part-32) describes invoice numbers, contract references, quantities, unit prices, and extended prices for covered federal payments. It does **not** establish globally unique line numbers for these state/municipal or private-service documents.

**Competition, not independently verified effectiveness:** [TicketClerks](https://ticketclerks.com/) now advertises vacuum-truck/oilfield field-ticket extraction, invoice math checks, PO validation and QuickBooks export. Together with [FortressTicket](https://fortressticket.com/) and [Aimsio](https://aimsio.com/industries/hydrovac/), this further weakens any claim that generic capture/reconciliation is rare. Vendor sites do **not** establish buyer demand for our separate audit, customer performance, or a valid competitor head-to-head.

## Quantified adversarial holdout

A complete, **entirely synthetic** cohort contains 100 jobs, all referencing separate document IDs from one hypothetical issuer, each with local invoice line ID **"1"**. The unchanged upstream global-ID bridge conservatively returns **100/100 REVIEW** because all line IDs appear to collide. Under **unverified, supplied (issuer, document, line) annotations**, there are **100 distinct document scopes and 0 same-document duplicate-line suspects**, despite 1 globally reused local identifier with 100 document scopes. This disproves the *global-ID collision as a reliable defect explanation*; it does **not** prove invoices are error-free or release any REVIEW holds.

Counterexamples: Same issuer + same document + same line number across two jobs yields **1 suspected scoped collision involving 2 jobs**; same invoice number with a different issuer does **not** collide under the supplied composite annotations. Split invoices and same-job duplicates are tested. Missing, partial, foreign, contradictory, or forged money/verification annotations yield **INDETERMINATE**, not clearance. Document identity remains **UNAUTHENTICATED** and the key is an investigative heuristic, not an invoice adjudicator. Text case, provenance and cross-system mapping remain unresolved.

## Code/tests and actual verification performed

- [`invoice_scope_holdout_025.js`](./invoice_scope_holdout_025.js): a new standalone **diagnostic-only** module that requires upstream #024 identity coherence, exact document annotations, strict annotation schemas and complete positional coverage. It cannot alter `cohort_amount_bridge_019.js`, return money, or claim verified customer evidence.
- [`test_invoice_scope_holdout_025.js`](./test_invoice_scope_holdout_025.js): **18 synthetic adversarial cases**, including namespace aliases, two-job and same-job collisions, split documents, alternative issuer, malformed mappings, spoofed confidence fields and forged money. 
- [required Technology Intelligence test wrapper](../../../tests/test_ti_golden_goose_hydrovac_integration_022.py) additionally invokes the real Node harness and requires the **original** bridge's 100/100 REVIEW.
- **Execution:** 18/18 cases passed in-process V8 on **read-back GitHub source bytes** using a shim for Node assertions; the source-module blob was `8745215bc7c22545b9148c549329b8cd78ae89aa`, the test blob `980ef168ac363d8b03e3fb5160f527e6efc4bb0b`, and the original bridge blob `85c718960a314b2b9e2d4454ff918c2989fbf930`. This is **not** a native Node CLI run or full GitHub CI pass. Verify completed release-gate results at the exact final head separately.

## Economic attack and stop gates

Under **arbitrary assumptions** of 100 cases × 5 minutes per case × $35/h, reviewing all 100 would cost **$291.67** in labor against a **hypothetical** $100 flat fee. A $100 fee minus hypothetical $10 overhead leaves $90 for labor, or **2.571 h** at $35/h before sales acquisition/tax. Namespace annotations might improve triage, but because the authoritative bridge still holds all 100 and no actual review was measured, **verified labor savings = $0** and no positive margin is asserted.

A customer-authorized, read-only *second-look service* could be lawful and charge for documented reconciliation labor, subject to customer contracts, privacy/data-handling obligations and applicable service/legal restrictions. It would require fresh express permission before any customer-facing act. **No verified buyer willingness to pay, independent advantage, bankable invoice, contract entitlement or right to collect has been established.** The older fictional **$4,940** variance, official procurement prices and settlement totals are **not collectible dollars**.

**Exact status:** 0 customers; 0 real customer/competitor comparisons; 0 authorized real invoice records; $0 verified collectible; **$0 verified owner revenue**. No outreach, funds, paid tools, claims, trade, production deployment, main merge, new issue, worker claim, integrator priority edit or Work mode.

**Next cheapest falsifier:** Check latest final CI; test actual locally scoped number mapping *against an independent evidence schema* including source-signed issuer/document identities and immutable image/document hashes, but only with synthetic documents until permissioned records exist. A 100-job blinded comparison against a customer's incumbent reconciliation and review-time audit **requires fresh express buyer/user approval**. Reject commercialization if no incremental legitimate variance survives signed rates/credits or realistic handling time exceeds break-even.
