# Seven-branch private workbench

RETALLY now has a browser workbench and reproducible synthetic customer journey for Freight, AP, Warranty/Credit, Procurement, Rebate, Parcel and Utility.

This release completes the **implemented-scope simulation**, not real customer validation or a claim to be best in any market. Simulation is an environment boundary, not a substitute for authentic approvals, deployment assurance or bank evidence. The application binds only to 127.0.0.1 and has no outbound claim transport.

## Run a clean demo

From the repository root, choose a new private directory outside the repository:

```sh
python -m recoveryworks.seven_branch_simulation --workspace /private/retally-demo
python -m recoveryworks.workbench_server --workspace /private/retally-demo --port 8765
```

Open `http://127.0.0.1:8765`. Use a role key from the private `credentials.json`. Keys are not printed, placed in URLs, or saved in browser storage. Lock the workspace before changing roles. Do not publish that file or expose the loopback server through a public tunnel.

To execute the complete simulated customer journey automatically, use a separate new directory:

```sh
python -m recoveryworks.seven_branch_simulation --workspace /private/retally-rehearsal --exercise
```

The resulting `simulation-acceptance.json` explicitly records zero real customers, zero real recovered dollars, zero external actions, and no commercial certification. It exercises actual adapters, access checks, ledger transitions and restore logic; it does not mock successful results.

## Product workflow

1. **Customer/operator:** upload CSV or JSON, map CSV headers, and inspect row counts. Original bytes and normalized bytes are separately hashed and retained. Unsupported columns are never guessed into financial meaning. Optional reversal, return and procurement conversion columns are preserved.
2. **Reviewer:** inspect the uploaded source and verify the exact current hash with a note. The customer cannot self-verify. Changed evidence invalidates review.
3. **Operator:** set evidence-supported scope dates and utility identity, then scan complete source sets. No arbitrary paths or verification flags are accepted through the HTTP API.
4. **Reviewer and independent reviewer:** examine cases separately. Each role has a different bearer credential. The customer cannot approve evidence or run scans.
5. **Customer:** authorize the reviewed case. Simulation can exercise the full flow directly. In live mode, authorization requires a separately reviewed frozen case bundle and customer authorization document; the document actor must match the signed-in customer.
6. **Operator:** record an externally submitted claim only from reviewed action-envelope and exact artifact evidence; post partial receipts and linked reversals only from reviewed cash-event documents; track net cash, fees and remaining potential. Historical receipts and reversals stay in the hash-chained journal.
7. **Operator:** back up the complete workspace and restore it into a separate temporary location. Source originals, normalized evidence, intake records, role-token hashes and ledger are verified. Plaintext credential keys are excluded from backups; retain them separately. Credential rotation/account recovery is a deployment integration requirement, not an implemented UI feature.

## Live proof documents

The case drawer accepts four JSON document kinds, each bound to a specific case:

- `case_bundle`: existing `case_bundle_to_payload` format, uploaded by a reviewer and verified by a distinct reviewer.
- `authorization`: existing `authorization_to_payload` format, uploaded by the customer and reviewed separately.
- `external_action`: object containing `envelope` (`external_action_to_payload`), exact `artifact_text`, `submitted_at`, and `submission_reference`. The operator records an already-submitted action. The app checks artifact bytes, amounts, case/authorization hashes, actor, dates and expiry. It sends nothing.
- `cash_event`: the `CashEvent` field shape. An operator uploads it and a distinct reviewer verifies the current document hash. The server derives verified status from that reviewed document, not from the uploaded `verified` flag.

Select reviewed documents in the case drawer before live actions. An unreviewed, stale, wrong-case or wrong-kind document fails closed. Seven-figure dossier requirements remain in the existing specialized workflow; the workbench does not bypass them. Document review records do not cryptographically authenticate a bank or counterparty; the reviewer must inspect genuine source evidence.

## Financial lifecycle

- `CashEvent` records incremental signed amounts and fee deltas. Replaying the same event is idempotent; changing an existing event ID is rejected.
- Receipts cannot exceed the case's supported recovery. Negative postings require the original positive receipt in the same case and cannot over-reverse its money or fee.
- Existing legacy `mark_recovered` receipts can be reversed with the new API without rewriting historical journal hashes.
- A full reversal leaves a historical RECOVERED lifecycle record with zero **net** received; the dashboard displays remaining potential separately. RECOVERED does not mean fully collected.
- Evidence conflicts hold further actions. Two distinct review identities and current record hash are required to retain the proof or replace a pre-claim case. Workbench actions additionally bind the current journal head.
- A replacement gets fresh review/authorization state. The original remains in journal history; active reports count only its successor. Claimed or cash-bearing cases cannot be silently rewritten.
- Exact-reference economic identity remains conservative. Cross-branch `economic_loss_id` mappings still need explicit reviewed source attribution. Partial cross-branch allocation is not inferred.

## Additional calculation scope

**Parcel:** `parcel_rating.py` supports explicit effective contract bands, actual versus dimensional weight, rounding increments, discount, minimum base, a scoped flat surcharge, fuel base selection and tax. It rejects currency, unit, lane/date and measurement mismatches or ambiguous contracts. It does not claim to implement every carrier exception. The scan runner accepts exactly one of `assessments_csv` or `rating_json`; the latter contains `contracts` and `measurements`. Source review controls `assessment_source_verified`.

**Procurement:** authorities accept `Price_Unit`; quantity approvals accept `Quantity_Unit`, `Price_Units_Per_Quantity_Unit`, `Conversion_Basis`, and `Conversion_Reviewer_ID`. Different units require an explicit reviewed factor. Same-unit non-one conversion, missing unit scope and missing conversion authority are blocked. The price stays decimal until quantity extension. No automatic pack-size inference, landed-tax allocation or cumulative-receipt policy is claimed.

Other branches retain their tested domain cores, including AP statement/payment reconciliation, warranty entitlement settlement, rebate tiers/returns, and utility tariff components. Their supported input scope is narrower than an entire industry.

## Acceptance evidence

| Area | Verification |
|---|---|
| All seven branches | Real adapters produce independently specified expected synthetic recoveries |
| Lifecycle | Hold/release, both reviews, customer authorization, claim, two partial receipts, reversal and fee reconciliation |
| Revision | Changed procurement invoice is quarantined, reviewed, replaced and counted once |
| Access | Missing/wrong/other-client credentials, customer self-review and stale state rejected |
| HTTP boundary | Host and Origin checks, no static credential access, no-store, CSP and no external asset dependencies |
| Evidence | Ambiguous mapping, duplicate columns, changed files and invalid snapshot paths rejected |
| Recovery | Full snapshot restore plus durable journal replay and source-hash verification |
| Browser | Seven cases, desktop and mobile layout, source reading, role switch and backup action; zero JavaScript errors |
| Domain additions | Independent parcel arithmetic, unit-conversion arithmetic, negative/unsupported cases |

Reproduce Python checks with `python -m unittest discover -s recoveryworks -p 'test_*.py'` and freight checks with `python -m pytest -q freight`. The RecoveryWorks workflow also runs the synthetic journey and a pinned isolated Playwright browser smoke test. Browser test packages are development-only.

## Actual deployment boundaries

The workbench is an operator-controlled local application, not a publicly deployed multitenant SaaS. Production SSO/MFA, hosted transport/TLS, credential rotation and account recovery, signed reviewer identity, production retention/deletion scheduling, live bank/carrier/accounting connectors, operational monitoring and customer support ownership still require deployment-specific implementation and verification. Local token role separation is not a claim of enterprise identity assurance.

The restore hash checks detect accidental corruption and mismatched bytes; they do not establish third-party authenticity against an attacker able to rewrite both files and hashes. Protect the private volume and backup location with the deployment's access controls and encryption.

Real-world accuracy/recall, recovery yield, time to cash, unit economics, retention and competitive superiority cannot be established by synthetic customer journeys. Keep those gates open until genuine authorized evidence exists. Simulated records must never be uploaded as real customer evidence or used to remove production release holds.
