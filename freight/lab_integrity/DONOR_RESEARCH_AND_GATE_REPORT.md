# Freight laboratory audit recovery and hunted-repository donor assessment

**As of 2026-10-08. Research only. Do not market synthetic metrics as customer results.**

## Reconciled issues

- First independent laboratory code audit: **8 labeled observations** (LAB-P0-01..LAB-P2-08). A prior conversational summary called them seven; this report preserves the original eight IDs and does not silently delete the eighth.
- Second independent hidden-bug audit: **18 separately labeled observations** (D-01..D-08, X-01..X-05, Y-01..Y-04, Z-01).
- During reconstruction of the new read-only proof gate, **GATE-001** (failed semantic verdict returned CLI exit 0) and **GATE-002** (negative-only tests failed to catch a broadly overrejecting event handler) were reproduced, fixed **in the experimental gate**, and regression-tested.
- **Cumulative index: 28 observations in 11 common root-cause categories.** Several are different symptoms of the same problem, not 28 distinct exploitable production vulnerabilities.
- **Original lab findings repaired: 0/26.** **Proof-gate self-defects repaired: 2/2.** No code from external donors was imported or merged.

## Most important donor applications

| Rank | Donor and exact-revision license | Immediate adoption target | Test needed before acceptance |
|---|---|---|---|
| 1 | [payops-labs/solana-payment-ops](https://github.com/payops-labs/solana-payment-ops) · Apache-2.0 | Double-spend prevention and one-to-many credit/reversal allocations | Partial credits, duplicate reference, historical reversal and dollar conservation must fail before fix and pass after |
| 2 | [cmdrvl/canon](https://github.com/cmdrvl/canon) · MIT | Qualified invoice/customer identity separated by tenant and origin | Cross-tenant import, same display name, merge/split, different issue on one invoice |
| 3 | [srthck/trustmesh](https://github.com/srthck/trustmesh) · MIT | Proof admission and denial reasons for money-bearing actions | Wrong source, independent reviewer absent, duplicated artifact, stale authority, contradiction |
| 4 | [prathamesh-git9/effect-broker](https://github.com/prathamesh-git9/effect-broker) · MIT | Crash-safe external carrier/payment side effects | Kill worker after provider commit and before receipt; preserve UNKNOWN and no duplicate effect |
| 5 | [kirilurbonas/FireDrill](https://github.com/kirilurbonas/FireDrill) · Apache-2.0 | Exact required-artifact census vs actual restored subjects | Missing archive and zero files restored must fail even if command exits zero |
| 6 | [in-toto/in-toto](https://github.com/in-toto/in-toto) · Apache-2.0 | Evidence bundle signer/material agreement and release provenance | Wrong signer, expired/rolled-back proof, incomplete threshold, altered source release |
| 7 | [project-minigraf/minigraf](https://github.com/project-minigraf/minigraf) · MIT OR Apache-2.0 | Historical contract/fee bitemporal authority | Change a later fee revision and ensure earlier signed claims do not change |
| 8 | [microsoft/BCApps](https://github.com/microsoft/BCApps) · MIT | Contract/receipt/invoice line capacity reconciliation pattern | Two independent allocations cannot exceed the same contracted/accepted value |

Licenses and source paths were inspected at the pinned revisions recorded in `DONOR_SHORTLIST.json`, including direct inspection of effect-broker state machine/crash test, Trustmesh obligation behavior, Canon identity-scope code, FireDrill restore documentation, and the relevant reconciliation-tree source/test structure. **Licensing the repository's code does not license proprietary contracts, real bank/carrier data, third-party APIs, standards, or bundled assets.** The eight are selected source-code candidates, not verified RecoveryOS integrations. BCApps is business-application-specific and should be treated as a test/specification donor rather than a drop-in Python dependency.

## New read-only experimental gate

`proof_gate.py` works against a **copied fictional** Unified Five-Step staging SQLite database. It uses a frozen, separately supplied source SHA, never imports the staging engine, independently replays and validates event state transitions, checks exact debit/credit journal postings, requires source identities and effective consent, flags duplicated invoice usage across cases and tenants, and rejects invented financial states. It also checks missing first events, orphan rows, case-lock version, currency, and source-bound intake payloads.

Tests include an actually clean one-case intake positive control. Otherwise a faulty verifier that declares every case bad would make the negative test suite pass. This exact self-test problem occurred during development and was corrected. The standalone CLI returns exit codes **0 narrow synthetic PASS / 1 FAIL / 2 invalid input**. Each code is tested.

**The original 24-case file remains FAIL**, with nine `NO_INDEPENDENT_SIGNED_FEE_TERMS` and two `EVENT_DERIVED_FINANCE_MISMATCH_FEE_EARNED`. The former is unresolved because there is no trustworthy signed, versioned engagement fee receipt in this historical fictional database. Supplying a caller-controlled integer fee rate is not evidence that a real buyer signed it.

## Additional limitations and next steps

1. The frozen source digest must be pinned by a party independent of the staging writer. This demo allows an operator-supplied SHA-256; the unit test fixture itself cannot be considered externally signed.
2. The old staging database does not have a trustworthy source-owner entitlement table or economic-issue identity. The gate conservatively blocks repeats, which may also block a legitimate second distinct charge on one invoice.
3. Partial payments after a first reconciliation, late reconciliation, retroactive fee write-offs and consent revocation still need an explicit business-state model and actual independent regression tests. The research gate may flag these as invalid rather than accepting business-correct paths.
4. Proper blind auditing must separate the candidate's raw invoice inputs from the frozen expected-charge and truth fields, using another process and independent reference tariff evidence.
5. The deployed RecoveryOS application, SSO, OCR, tenant isolation, bank readback and real customer data have NOT been tested by this research gate.
6. No automatic PR merge, production rollout, actual claims or scheduled task modifications are authorized.

**Commercial release position: BLOCKED until upstream staging data integrity, signed terms and real buyer proof are separately established.**