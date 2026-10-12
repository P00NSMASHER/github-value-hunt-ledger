# Recovery action authorization
One defined action and approved payload. Report receipt is not authorization.

| Required field | Entry |
| --- | --- |
| Customer legal name / engagement | [Verified names and ID] |
| Customer signer / authority | [Verified person, title and authority] |
| Findings / invoices / shipments | [Exact independently reviewed IDs] |
| Report / controlling sources | [Version, references and SHA-256] |
| Carrier / customer account | [Verified entity and account] |
| Action | [Defined dispute, credit review, documentation or status request] |
| Maximum amount / currency | [Exact USD amount] |
| Recipient | [Independently verified destination] |
| Payload / attachments | [Approved version and SHA-256] |
| Incumbent and prior-claim check | [Existing claim IDs, exclusions and coordination] |
| Valid from / expires | [Dates; modeled validity no more than 30 days] |
| Executor / independent reviewer | [Named identities and approval receipts] |

I authorize only this action, recipient, scope and payload. This grants no bank access, money movement, account change, settlement compromise, legal representation, automated execution or unrelated carrier contact.

Customer signature/date/verification receipt: [Fields].
Reviewer confirmation/date: [Fields].
Execution reference: [After action].
Delivery confirmation: [Actual recipient/provider evidence; sent is not received].

Reverify validity, unchanged payload and recipient immediately before action. Record revocation and stop unsent actions. Expired, revoked, changed-amount or changed-payload approvals must be replaced.

This authorization permits one recorded transmission, not recurring contact. Record its unique action ID, exact time and timezone, and revocation contact. If delivery is unknown, freeze retries and reconcile provider evidence; do not resend merely because no response arrived. New payload, recipient or further contact requires renewed approval. Revocation stops unsent work; record and notify the customer of anything already sent without promising recall. Escalate offers requiring releases, waivers or settlement compromise to the customer; this form grants no power to accept them. Carrier claim deadlines are separate from authorization expiry and must be recorded and reviewed before action.
