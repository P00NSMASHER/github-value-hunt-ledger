# RETALLY | Competitor-code adoption: source-gated detention review

**Reviewed:** 2026-10-12. **Scope:** development-only, read-only Python decision support. This is not proof of being the best product, a real customer recovery, or permission to deploy unreviewed source.

## Source inventory and rights decision

| Repository | Observed code reuse basis | Disposition |
| --- | --- | --- |
| [cmiedema25-rgb/freight-audit](https://github.com/cmiedema25-rgb/freight-audit/tree/f46a98d11ce559b0ecb483f256d8efeb3163a0f) | MIT license, copyright Charles Miedema (2026) | **Adopted only** the exact portable 'rounded_minutes' function from 'src/freight_audit/money.py'. Full copyright/permission text is at 'freight/third_party/LICENSE.cmiedema25-freight-audit.txt'. No samples or third-party data copied. |
| [tritaptheduc/Freight_Audit_Project](https://github.com/tritaptheduc/Freight_Audit_Project/tree/781d2fdc6851eb8f53e7573f6c19def410809ebe) | MIT license, verified | Analytics reference, no source integrated in this increment. |
| [TienXuanLam/ocean-container dispute evidence agent](https://github.com/TienXuanLam/agentic-star-logistics-ocean-container-demurrage-detention-invoice-audit-dispute-evidence-agent/tree/6fee849be91daef3a42d652cd8ed40786136a71e) | MIT license, verified | Advisory agent reference only; not a drop-in production recovery workflow. |
| [Jacob-Met/workflow-checks](https://github.com/Jacob-Met/workflow-checks) | MIT license, verified | Cross-shipment duplicate research is already handled independently by [RETALLY PR #343](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/343). Avoid duplicate work. |
| [vokrix-products/freightauditor-freight-invoice-audit](https://github.com/vokrix-products/freightauditor-freight-invoice-audit) | No declared repository license in current review | **Do not copy.** Directional-rate and unsupported-input cases are generic requirements reimplemented independently. |
| [hackfest-dev/HF26-48](https://github.com/hackfest-dev/HF26-48) | No declared repository license | **Do not copy.** Public documentation does not establish code-reuse permission. |
| [sayedRaheel/freight-audit-engine](https://github.com/sayedRaheel/freight-audit-engine) | No LICENSE file in inspected root | **Do not copy.** Conceptual comparator only. |

Core proprietary implementation for commercial incumbents (Trax, Cass, Loop, Intelligent Audit and nVision Global) was **not** available through their public GitHub sources. Do not infer private code access or vendor ownership from similarly named public repositories. Respect third-party marks, sample/customer data and transitive dependencies.

## What RETALLY gains in this PR

'freight/detention_review.py' implements opt-in, source-linked **detention / demurrage / layover** charge review against an existing canonical freight record.

1. Revalidates the immutable record and a hash-bound, effective-dated, human-approved contract policy with exact buyer/BU/customer/carrier/currency/transportation-mode and **directional origin/destination scope**.
2. Uses independent physical-event source hashes from the canonical record. The invoice itself cannot masquerade as a verified gate or ELD event, including if a duplicate SHA carries conflicting kinds.
3. Parses timestamps only with explicit UTC offsets, handles daylight-saving fall-back correctly, and uses conservative integer-minute and integer-cent rounding.
4. Applies contractual free/grace minutes, the selected MIT-licensed increment rounding mode, and **separately evidenced prior payment**. Ambiguous, missing, stale, duplicate, mismatched or overflowing evidence fails closed.
5. Produces only 'REVIEW' or 'NEED_EVIDENCE'. 'validated_cents', 'recovered_cents', and 'fee_eligible_cents' remain **zero**.
6. Exposes 'detention_to_review_case()' to create a hash-verified candidate in RETALLY's **existing** human reviewer cockpit. It does not promote a candidate to a finding, direct a carrier, post money or open a live API.

**Synthetic illustration:** 07:50–12:35 is 285 minutes. Free=60, grace=15, billable=210. At $15 per 15 minutes, supported gross=$210; $60 prior independently evidenced payment leaves $150 remaining. A $210 invoice produces a **$60 human-review candidate, not a realized recovery**.

## Tests and evidence

Run 'python -m pytest freight/test_detention_review.py -q' against a checked-out repository. Tests cover DST, rounding thresholds, lane reversal, contract term/date/currency scope, invoice-only event refusal, missing credit evidence, duplicate allocations, stale/forged hash rejection, time/money bounds and an intact $0 recovery/fee boundary.

The current proof is synthetic. GitHub CI must pass before the PR is considered technically ready; a real pilot requires independent buyer evidence.

## Non-goals and outstanding blockers

- **Not yet integrated** into the deployed RecoveryOS evidence-extraction endpoint: that connection requires a separate authorized document-to-canonical-artifact bridge and negative tenant/lineage tests.
- A 'verified_controlling_authority' argument is a caller assertion, not a cryptographic approval signature. Real onboarding must prove who verified the source, contract scope, terms and document.
- This review cannot infer entitlement, external collection, a posted credit or money movement. Existing independent payment-provider attestation and human-approval gates remain in effect.
- Confidential customer files, credentials, production datastore writes, external notices and marketing claims remain out of scope. Do not enable online intake or change production release gates.
- Future integration from public competitors requires fresh exact-revision license verification and preserved attribution for each adopted component.

**Release classification: source review + synthetic test only; production/customer-data rollout NO-GO.**
