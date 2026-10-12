# Recovery reconciliation statement
Customer / engagement: [Fields]. Currency: USD. As of: [Timestamp]. Reviewer: [Name]. Version / snapshot: [Fields]. Missing values mean unknown, not zero.

| State | Amount | Required proof |
| --- | --- | --- |
| Candidate difference | [Amount] | Unverified items separated |
| Supported findings | [Amount] | Controlling source, calculation and review |
| Authorized actions | [Amount] | Signed exact scope and payload |
| Carrier-approved claims | [Amount] | Carrier response; not posting |
| Gross posted benefits | [Amount] | Unique recovery and customer posting |
| Reversals | [Amount] | Original event link and dated allocation |
| Observed net benefits | [Gross less reversals] | Includes excluded recovery |
| Incumbent / other exclusions | [Amount] | Item-level contractual classification |
| Attributable eligible net | [Amount] | Posting and signed definition |
| Cumulative fee | [30%, half-up cents] | Signed rate and current snapshot |
| Prior fee invoices/credits | [Amount] | Unique billing ledger |
| Current invoice/fee credit | [Cumulative less prior invoiced] | Independent billing sign-off |

Every item links finding, invoice/shipment, claim, authorization, response, posting, reversal, exclusion and reviewer. Allocate each source event once. Do not add currencies.

Keep ambiguous matches, missing posting and pending recoveries separate. A new reversal invalidates the old report; recompute and notify the customer. Restarts replay immutable events or stop on conflict, never create another recovery or invoice.
