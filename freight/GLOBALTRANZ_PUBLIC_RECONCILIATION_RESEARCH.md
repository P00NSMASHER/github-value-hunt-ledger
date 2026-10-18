# RETALLY — GlobalTranz public invoice reconciliation research

**Research only. No customer data imported, commercial reuse license inferred, overcharge adjudicated, settlement confirmed, or recovery established.**

## Traceable public sources

- [Original GlobalTranz proof of claim and invoice/statement attachments](https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247), claim 10002, July 2025. Filed amount: **$25,954.47**.
- [Alphabetical claims register, July 28, 2026](https://document.epiq11.com/document/getdocumentbycode?docId=4596108&projectCode=MCX&source=DM), shows claim 10002 at **$1,496.52**.
- [Numerical view of same claims register](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM), confirms the register value but is **not independent verification** of a payment or adjudication.

The **$24,457.95** difference between the filed claim and later register remains unexplained. Nothing in these documents establishes that the difference is a customer credit, freight overcharge, refund, recovery, payment, or claim allowance event.

Prior manual research of the public filing reports **102 account-statement entries**, original charges **$26,026.61**, and open statement balances **$25,954.47**, with a **$72.14** opening-vs-face difference requiring evidence. Those 102 records have **not been ingested or independently replayed** by the research comparator. Counting source invoice pages as separate shipments is also unsafe. The filing contains **broker-issued invoices**, not verified originals from every underlying carrier.

## Research-only comparator

The new module freight/research/statement_reconciliation.py accepts only caller-supplied structured metadata. It checks invoice face vs statement original, statement totals, duplicate references, explicit base/adjustment linkage, unknown parents, changed open balances and contradictory external claim snapshots. It never derives recovered cash, an overcharge, source reuse rights, or shipment-family counts.

Run the 15 deterministic **synthetic-only** tests:

    python -m unittest freight.test_globaltranz_reconciliation -v

Existing repository-wide Freight and release CI must run on the PR and all normal branch-protection gates remain intact. This is not a production invoice importer, raw PDF extraction path, or licensed external benchmark.

## Research and release holds

- Verify actual source records and all invoice/statement line counts by independently inspecting the complete public document in a rights-compliant environment.
- Obtain claim amendment/objection/order/settlement ledger explaining the exact later register amount.
- Confirm buyer/document authority before processing original third-party documents commercially; public availability alone is insufficient.
- For a freight error: separately obtain controlling effective rate terms, underlying carrier invoice, BOL/PRO, independent classification/weight evidence, prior auditor results and payment/credit proof.
- Maintain independent adjudication and blind frozen validation; apply existing release and customer-data security controls.
- No customer outreach, payments, private-data extraction, new scheduled actions or changes to protected main were made.
