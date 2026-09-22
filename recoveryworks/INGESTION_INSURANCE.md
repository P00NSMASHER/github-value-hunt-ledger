# InsuranceRecovery ingestion contract

InsuranceRecovery detects commercial/property claim underpayments by comparing a
claim line against a separately reviewed expected net policy payment and actual
insurer settlement evidence.

It does **not** autonomously determine coverage, causation, valuation, policy
interpretation, bad faith, or legal entitlement.

## Claim line CSV

Default columns:

- `Claim_Line_ID`
- `Claimant_ID`
- `Insurer_ID`
- `Policy_ID`
- `Loss_Date`
- `Coverage_Category`
- `Claimed_Amount`

The claim line is evidence of the supplied claim population. `Claimant_ID` must
match the Scan 360 client. Mixed-client files are rejected before recovery math.

## Reviewed coverage assessment CSV

Default columns:

- `Assessment_ID`
- `Claim_Line_ID`
- `Policy_ID`
- `Loss_Date`
- `Coverage_Category`
- `Expected_Net_Payment`
- `Coverage_Basis`
- `Policy_Effective_From`
- `Policy_Effective_To`
- `Policy_Snapshot_Date`
- `Qualified_Reviewer_ID`
- `Qualification_Basis`

A verified assessment requires:

- the loss date to fall inside the reviewed policy effective period;
- a named qualified reviewer;
- a reviewer qualification basis;
- a policy snapshot date.

The expected amount should already be the reviewer's **net expected payment**
after the policy terms they considered relevant, such as deductible, limits, and
covered-loss valuation. RecoveryWorks stores that reviewed conclusion; it does
not independently make it.

The reviewed expected payment cannot exceed the supplied claimed amount. If it
does, the line fails closed for human reconciliation.

## Settlement CSV

Default columns:

- `Settlement_ID`
- `Claim_Line_ID`
- `Amount_Paid`
- `Payment_Date`

Multiple legitimate payments can be summed for one claim line. Duplicate
`Settlement_ID` values block the affected claim rather than being
heuristically deduplicated.

A zero-dollar settlement row is valid evidence of a denial/no-payment outcome.
The payment date cannot precede the loss date.

## Identity binding

The reviewed assessment must match the claim line on:

- policy ID
- loss date
- coverage category

Mismatches create an exception and no recovery finding.

## Recovery calculation

`potential recovery = reviewed expected net payment - actual insurer payments`

Only positive differences become candidates.

For a finding to become VALIDATED, the controlling reviewed assessment, claim
evidence, and settlement evidence must all be verified.

## Important exception states

- `DUPLICATE_INSURANCE_CLAIM_LINE_ID`
- `INSURANCE_CLAIMANT_SCOPE_MISMATCH`
- `NO_REVIEWED_COVERAGE_ASSESSMENT`
- `CONFLICTING_COVERAGE_ASSESSMENTS`
- `COVERAGE_ASSESSMENT_IDENTITY_MISMATCH`
- `EXPECTED_PAYMENT_EXCEEDS_CLAIMED`
- `NO_INSURANCE_SETTLEMENT_EVIDENCE`
- `DUPLICATE_INSURANCE_SETTLEMENT_ID`
- `CLAIM_BLOCKED_BY_DUPLICATE_SETTLEMENT`
- `SETTLEMENT_PRECEDES_LOSS`
- `ASSESSMENT_WITHOUT_CLAIM_LINE`

Exceptions do not create validated dollars.

## Scan 360 config

```json
{
  "insurance": {
    "claim_lines_csv": "claims.csv",
    "assessments_csv": "coverage_assessments.csv",
    "settlements_csv": "insurance_settlements.csv",
    "claim_source_verified": true,
    "assessment_source_verified": true,
    "settlement_source_verified": true
  }
}
```

## External action control

A validated InsuranceRecovery finding is not authority to submit a supplemental
claim, dispute a coverage decision, allege bad faith, contact the insurer, or
make a legal demand.

Recovery action remains behind:

1. qualified claims/coverage review
2. RecoveryWorks human finding approval
3. explicit customer authorization
4. appropriate professional/legal review for the chosen recovery path
5. outcome recording in the common Recovery Ledger
