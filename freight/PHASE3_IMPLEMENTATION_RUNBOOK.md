# RecoveryOS — Enterprise Pilot Implementation Runbook

Version: 1.0  
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

## Phase D — freeze

1. Build source/data-room manifest.
2. Freeze exact population.
3. Seal incumbent output hash against buyer/BU/population.
4. Freeze buyer-owned truth before opening incumbent output.
5. Verify package ordering/hash chain.

Any material change creates a new version. No quiet row substitution.

## Phase E — audit/review

1. Rate against controlling authority.
2. Route missing/ambiguous cases to review.
3. Compare against frozen incumbent source.
4. Review challenger-only findings.
5. Report:
   - reviewed discrepancy;
   - validated finding;
   - challenger-only validated;
   - unresolved;
   - false-positive dollars;
   - reviewer touches/time.

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
