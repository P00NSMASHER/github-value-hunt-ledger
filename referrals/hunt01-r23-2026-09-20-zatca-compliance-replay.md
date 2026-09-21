# Cross-lane referral — Hunt 01 Run 23 — Saudi ZATCA compliance replay

## Candidate
`suhailhijry/modular-erp@31524f3e9339d411fa85f4bd657668d6ec2aed02`

## Why this matters to another lane
This zero-star/full-ERP candidate combines several pieces that were previously split across the South Africa and Indonesia compliance-domain-pack findings:

- event-time taxpayer registration and tenant configuration;
- deterministic Saudi ZATCA UBL/XML generation from immutable sales history;
- invoice hash / ICV / previous-hash / QR / signing semantics;
- regulator clearance/reporting verdicts recorded as external legal facts;
- transport ambiguity kept pending rather than silently converted to refused/success;
- VAT filing preserved as filed;
- substantive integration tests plus an optional live ZATCA sandbox path.

It is therefore a strong reference for CAP-008/CAP-019 and RAD-008, and a near-complete implementation of the proposed Compliance Domain Pack Control Plane.

## Important limitation
The repository freezes the selected rate/configuration and historical registration into the issued event, but I did **not** verify a complete legal-source authority object carrying ZATCA spec/rule version, source URI/content digest, statutory `effective_from`/`effective_to`, and supersession lineage.

This distinction is material: event-time freezing prevents later configuration drift, but can faithfully preserve a rule that was already wrong when selected.

The live ZATCA sandbox tests are intentionally ignored by default and require authorized credentials, so exact-head green CI should not be interpreted as current remote ZATCA qualification.

## Exact unanswered technical question
**Can the compliance layer bind each issued/cleared artifact to an immutable authority receipt containing ZATCA spec/rule-set version, official-source digest, effective interval, taxpayer-registration event identity, artifact hash and returned-clearance hash, then replay the old artifact after both business configuration and ZATCA rules change?**

## Suggested experiment
Create a synthetic authority registry with statutory/spec versions A and B:

1. establish taxpayer registration R1 and authority A;
2. issue an invoice and persist the artifact/hash/ICV plus authority receipt;
3. record external acceptance/refusal evidence;
4. change taxpayer registration to R2 and authority to B;
5. replay the old history and require byte/hash-equivalent A artifact with R1/A receipt;
6. issue a new invoice and require R2/B;
7. inject timeout/503 so no regulator verdict is minted;
8. later resolve to acceptance and require one immutable returned-authority receipt;
9. issue a correction as a new legal event instead of mutating the original;
10. reject any compliance claim whose source/spec digest or effective interval cannot be proven.

## Commercial relevance
If that final authority-receipt edge can be proven, the stack supports a regulator-neutral **Compliance Artifact Replay & Authority Reconciliation** product: deterministic acceptance testing and historical proof for ERP implementers operating in jurisdictions where digital filings/invoices are validated by external authorities.
