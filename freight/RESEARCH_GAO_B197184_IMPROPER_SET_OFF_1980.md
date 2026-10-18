# Original GAO B-197184: $475.36 executed deduction later admitted improper

**RETALLY Lab 14 · October 18, 2026 · Research-only · No actual customer or financial activity**

## Primary document and dated chronology

Original U.S. General Accounting Office, Office of General Counsel, **two-page correspondence and internal memorandum**, both dated **March 26, 1980**:

https://www.gao.gov/assets/b-197184.pdf

The source states that GSA had **already collected $475.36 by deduction from money owed to Yellow Freight System**, concerning freight alleged to have been overcharged by Braswell Motor Freight Lines. The government bill of lading is **K-5405056**, dated **November 15, 1976**. Braswell filed for an arrangement under the Bankruptcy Act on **December 2, 1976**.

Yellow Freight challenged the deduction. The March 26 GAO letter explains that GSA subsequently **agreed the setoff against Yellow was improper** because the original shipment preceded Braswell's petition and Yellow was not liable on the record. GAO **dismissed the request for review as moot** and stated that Yellow's claim could be allowed **if otherwise proper**. GAO's contemporaneous internal memorandum repeats the agency's concession and procedural disposition.

This original document gives three different states that MUST NOT be combined:

| Evidence state | What the source establishes | What it does not establish |
|---|---|---|
| Executed deduction | GSA had already deducted **$475.36** | That the deduction was legally proper or permanently retained |
| Subsequent GAO/GSA correction | GSA agreed the earlier deduction was improper; GAO dismissed review as moot | That a check, wire, credit or Treasury disbursement was actually made |
| Allowable carrier claim | Yellow's claim could be allowed, subject to propriety | That Yellow ultimately received **$475.36**, or any other amount |

The record is separate from [GAO B-192974](https://www.gao.gov/products/b-192974), which described a **different** historical carrier bankruptcy/setoff dispute involving **$5,141.05** in post-petition payables. Both cases illustrate that an **executed setoff can later be disallowed**. Neither is counted as an approved, final or independently bank-verified collection, nor as RETALLY customer savings.

## Reproduction and evidence boundaries

The exact first-party facts are preserved in
`freight/fixtures/public_gao_b197184_improper_deduction_1980.json`.

The offline validator and negative tests:
```bash
PYTHONPATH=. python -m unittest -v freight.test_public_gao_b197184_reversal_v1
PYTHONPATH=. python -m freight.public_gao_b197184_reversal_v1
```

They reject changes to the $475.36 sum, original GBL/date, admission of error, review disposition, conditional repayment, bank receipt, legal finality and RETALLY recoveries.

**Source tier:** Public original federal document *text reviewed*. The original complete PDF bytes were **not independently downloaded and hashed** in this tranche. The underlying actual 1976 bill of lading, carrier invoices, original contract, accounting entries and any later Treasury or bank reimbursement were **not** examined. The source's legal reasoning is specific to a historic government/bankruptcy circumstance; do not apply it as private-carrier setoff authority in 2026.

**Commercial status:** `NO_GO`. This is a second historical GAO wrongful-offset counterexample, **outside the seven original GAO refund/setoff collection cases**, and outside the 307 market-reference rows. No new customer was contacted, no invoice or banking record was accessed, no production case was changed, and no payment was initiated.
