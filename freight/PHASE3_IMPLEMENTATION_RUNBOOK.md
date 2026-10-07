# RecoveryOS — Enterprise Pilot Implementation Runbook

Version: 2.0  
Prepared: 2026-10-07

## Goal

Launch one bounded, blind, buyer-authorized second-look pilot without replacing
the incumbent freight stack or exaggerating RecoveryOS maturity.

## Phase A — qualification

1. Confirm buyer entity and business unit.
2. Confirm historical period, modes, approximate invoice count and currencies.
3. Confirm the buyer has:
   - invoices/actuals;
   - controlling rate/contract authority;
   - shipment evidence where needed;
   - incumbent audit output;
   - a later settlement/credit source.
4. Name:
   - buyer sponsor/truth owner;
   - buyer IT/workspace owner;
   - buyer action approver;
   - Freight engagement lead;
   - qualified freight reviewer.
5. If controlling authority cannot be reconstructed or later outcome evidence
   cannot be observed, stop.

## Phase B — security/workspace

1. Agree whether the pilot runs in:
   - buyer-controlled single-tenant workspace; or
   - separately approved RecoveryOS environment.
2. Freeze:
   - named users;
   - roles;
   - retention period;
   - allowed transfer mechanism;
   - data classes;
   - local download/screenshot/recording rules.
3. Complete buyer security questionnaire.
4. Record all external gaps honestly.
5. Do not accept confidential records through marketing/contact forms.

## Phase C — integration

### Preferred first pilot
Use the least complex path the buyer can support:

1. canonical API;
2. SFTP manifest;
3. explicit X12 profile;
4. controlled manual/canonical upload.

Do not promise a named ERP/TMS connector that has not been built.

## Phase D — pre-register, sample and freeze

Use `freight/AUDIT_ACCEPTANCE_PROTOCOL_V2.md`.

1. Build source/data-room manifest.
2. Freeze exact full population and SHA-256.
3. Pre-register census or stratified-random sampling.
4. For stratified sampling, freeze the random seed before RecoveryOS output.
5. Freeze stratum population counts and sample targets.
6. Assign distinct truth owner, reviewer A, reviewer B and RecoveryOS operator.
7. Freeze selected case IDs and sample hash before RecoveryOS output exists.
8. Run and freeze RecoveryOS output without access to truth.
9. Freeze incumbent output independently.
10. Independently adjudicate and freeze truth without access to RecoveryOS.
11. Freeze the truth-manifest hash.
12. Jointly unseal only after both RecoveryOS and truth artifacts are sealed.
13. Verify sample/truth/RecoveryOS/incumbent hashes and timing contract.

Any material change creates a new version. No quiet row substitution. A blindness
or hash-ordering violation makes the study INVALID_METHOD.

## Phase E — audit/review and acceptance scoring

1. Rate against controlling authority.
2. Route missing/ambiguous/incomplete cases to REVIEW.
3. Never auto-decide unresolved truth, unresolved authority or incomplete source evidence.
4. Compare against frozen incumbent source.
5. Dual-review at least the greater of 50 cases or 20% of adjudicated cases.
6. Document adjudication of every reviewer disagreement.
7. Execute `freight/audit_acceptance.py` against the frozen pilot package.
8. Report:
   - reviewed discrepancy;
   - validated finding;
   - challenger-only validated;
   - unresolved truth;
   - auto coverage and review rate;
   - precision with 95% interval;
   - false-positive and false-negative rates with 95% intervals;
   - false-positive and false-negative dollars/shares;
   - mean absolute dollar error and net dollar bias;
   - confidence calibration;
   - reviewer agreement / Cohen's kappa;
   - incumbent-known leakage;
   - duplicate economic-issue leakage;
   - stratum-level errors;
   - reviewer touches/time.

Do not describe audit quality as proven unless the machine status is
AUDIT_QUALITY_PROVEN.

## Phase F — action

No carrier/vendor contact occurs until the buyer action approver explicitly
authorizes it.

Every authorized action is scoped to exact findings and amount ceilings.

## Phase G — settlement

A result becomes realized only from buyer-controlled credit/refund/remittance
evidence with unambiguous allocation.

Promised credits, submitted disputes and corrected bills are not realized
recovery.

## Phase H — closeout

Deliver:

- population/truth/incumbent hashes;
- finding register;
- exact evidence locators;
- false-positive/unresolved metrics;
- reviewer effort;
- settlement/reversal state;
- realized and fee-eligible totals;
- limitations;
- retention/deletion actions.

## Expansion gate

Do not expand to annual assurance, additional business units, automated
extraction or new integrations merely because the demo looked attractive.

Expand only when a real pilot establishes at least one of:

- real challenger-only validated recovery;
- defensible clean-population audit quality;
- measured reviewer-efficiency improvement;
- a named buyer integration requirement.
