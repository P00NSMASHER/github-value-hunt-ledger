# RETALLY second-look claim — engineering audit and release gate

Date: 2026-10-16. Status: **INTERNAL ENGINEERING / CUSTOMER-CLAIM EVIDENCE NO-GO**.
Scope: GitHub freight rerating/attribution and observed published Floot RecoveryOS import boundary.
No customer data, external claims, settlements, outreach, deployments, production permissions,
or commercial acceptance were changed by this review.

## Verified current strengths

- Deterministic freight rerating exists in `freight/rating_engine.py` with explicit,
  effective-dated authority selection and fail-closed review states.
- Frozen incumbent output can be compared with candidate issues via
  `freight/incumbent_challenge.py`.
- A hash-bound internal gold fixture has 42 synthetic scenarios (20 rating, 4
  authority, 8 incumbent attribution, 10 payment). All expected outcomes matched
  when the October 7 baseline was collected.
- The prospective independent customer-audit gate exists as
  `freight/AUDIT_ACCEPTANCE_POLICY_V2.json` and `freight/audit_acceptance.py`.

## Unresolved gaps preventing an asserted detection advantage

1. **External comparative evidence is absent.** The October 7 benchmark expressly
   says external blind customer validation is PENDING. A 42-case synthetic,
   code-adjacent corpus does not support production precision/recall or comparison
   with any named incumbent.
2. **The live audit pipeline is incomplete.** Published Floot RecoveryOS contains
   evidence upload/review and imports precomputed challenge findings; a documented,
   deployed, independently verified invoice/contract-to-rating-to-import end-to-end
   integration was not established by this audit.
3. **Real customer outcome is not measured.** The published application's queried
   tables for populations, records, challenge findings, incumbent snapshots and
   reviewer decisions all returned zero rows at the time of inspection. This is
   not proof of future yield and does not measure external workflows.
4. **Partial-incumbent residual detection needed hardening.** Previously an exact
   incumbent economic-key match suppressed an overcharge candidate even when an
   incumbent credit/claim was smaller. This draft conservatively routes such
   cases to REVIEW with no net-new dollars or automatic action.
5. **Provenance is weaker than commercial truth.** Candidate/snapshot hashes
   establish integrity of supplied fields, not independent authenticity of
   governing terms or source documents. The published Floot import boundary
   received unpublished source hardening (canonical identities, distinct
   evidence hashes, canonical-record bound source reference, buyer/BU duplicate
   attribution lock). That work is not published or an independent security audit.
6. **Category breadth is not production coverage.** Parcel, LTL, TL, intermodal,
   air and ocean synthetic coverage does not establish support for every
   carrier tariff, fuel schedule, accessorial, effective-date rule, currency,
   tariff exception, credit posting, dispute window or mixed invoice format.

## Acceptance plan to support a concrete, defensible second-look outcome claim

1. Obtain buyer authorization and freeze a representative historical population,
   invoices, contracts/amendments, proofs of delivery, payment and credit logs,
   and incumbent findings before reviewing or revealing RETALLY's outputs.
2. Run an independent invoice-to-canonical extraction and rerating pipeline with
   signed/documented authority review, complete error accounting and evidence
   locators. Preserve unknown fields as REVIEW, not zero-dollar certainty.
3. Independently adjudicate truth blind to RETALLY and incumbent decisions under
   `AUDIT_ACCEPTANCE_PROTOCOL_V2`: use at least 200 adjudicated cases, at least
   30 positives and 30 negatives, measure Wilson intervals, stratified false
   negatives, false-positive dollars, precision and abstention burden.
4. Match incumbent outputs on **economic issue identity**, not text alone.
   Reconcile partial existing credits, open disputes, late auto-credits and
   reversals; never automatically fee-charge an incumbent-known amount.
5. Compare detection on the **same frozen source population** and publish
   per-category net-new validated discrepancies, unresolved reviews, duplicate
   suppressions, reviewer effort, false positives and later *actual settled*
   recovery, always separating potential/validated/authorized/settled dollars.
6. Make customer-facing comparative performance claims only for specifically
   validated buyer/mode/sample contexts, with reviewer sign-off. Do not
   extrapolate synthetic precision or claim universal superiority.
7. Preserve customer authorization, external claim and financial release gates
   independently; no automatic carrier correspondence, settlement posting,
   collections, fees or production deploy based on these changes.

## Permissible messaging now

"Already audit your freight? RETALLY independently checks the available
invoices, controlling rates, shipment evidence, and prior findings for
potential discrepancies that your existing process may have missed.
No findings or recovery are guaranteed."

**Not yet substantiated:** "We will find errors your current auditor missed,"
"we outperform incumbent X," "100% accurate," or any specific savings amount.

## Change review

- Branch regression tests: partial credit, overlapping matters, fully covered
  known issue, unmatched issue, and Unicode/whitespace identity aliases.
- GitHub fix is conservative: matched residuals require **human review** and
  always contribute **zero net-new or fee-eligible cents** until independently
  verified through the existing authorization and settlement controls.
- Source-only Floot changes are in checkpoint
  `d6fbd9a0-9764-4042-a005-4c01aa5983dc`; the published app remains
  unchanged pending approved release/testing.
- This report is a software/evidence-readiness audit, not a claim that a full
  penetration test, external benchmark, customer pilot or paid recovery occurred.
