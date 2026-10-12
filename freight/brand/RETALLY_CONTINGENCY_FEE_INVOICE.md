# Contingency-fee invoice
NOT ISSUED. Verify legal identity, tax treatment, signed terms, posting and independent billing approval before sending.

| Invoice field | Required entry |
| --- | --- |
| Provider legal identity / correspondence | [Verified fields] |
| Customer / billing recipient | [Verified fields] |
| Unique invoice ID / issue / due date | [Engagement-scoped ID and signed terms] |
| Engagement / agreement / rate | [References and verified signature] |
| Currency / cutoff / snapshot | USD / [Timestamp and hash] |
| Eligible net actual recovery | [Posting, exclusions and reversals] |
| Cumulative 30% fee | [Half-up integer-cent calculation] |
| Prior invoices / fee credits | [Verified ledger balance] |
| Current fee subtotal | [Cumulative fee less prior balance] |
| Taxes / final total | [Qualified treatment and approved amount] |
| Remittance route | [Privately verified company route] |

Attach the reconciliation. A second reviewer checks invoice uniqueness, recipient, current snapshot, signed fee base and prior-billed balance. A calculated fee record alone does not authorize invoicing.

## Fictional invoice example
Northstar Industrial Supply / SYNTHETIC:NIS:2026-09. SAMPLE ONLY - NOT PAYABLE.

| Line | Amount |
| --- | --- |
| Gross posted credits | $300.00 |
| Carrier reversal | ($25.00) |
| Observed net benefits | $275.00 |
| Incumbent-known exclusion | ($200.00) |
| Eligible net recovery | $75.00 |
| 30% cumulative fee | $22.50 |
| Sample subtotal, before real tax determination | $22.50 |

If an earlier $30.00 fee was already invoiced, issue a $7.50 fee credit to reach the $22.50 cumulative fee. Do not add another $22.50 invoice to the earlier $30.00. No live receivable, tax determination, payment or money movement is established.
