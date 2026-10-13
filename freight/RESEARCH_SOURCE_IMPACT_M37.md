# RETALLY Research Lab 14 — Mission 37: source-change blast radius

**Internal research only · October 12, 2026 · draft stacked on M35 PR #426 · no merge, deployment, outreach, new lab, or scheduled-task changes.**

## Why this exists

The existing M35 source-to-commercial firebreak correctly classifies eight attributed public economic observations for **internal-only** research and blocks eight unjustified customer/invoice/recovery/TAM assertions. Source reports from BEA, Census, and BLS are not interchangeable. Previously, if a source family were superseded, no single Research Lab report showed *which* claim cases needed renewed investigation. This module fills that narrow gap without inventing a live source refresh or real customer approvals.

## Typed source lineage and affected observations

| Source family with prior local derived receipt | Qualified M35 internal observations affected by a *hypothetical* revision |
| --- | --- |
| BEA original truck gross-output reports | 01 gross output, 03 BEA–Census dollar gap, 04 denominator ratio, 05 real gross-output growth, 08 BEA/BLS price-scope contrast |
| Census original employer trucking revenue reports | 02 employer revenue, 03 dollar gap, 04 ratio, 07 illustrative Census/BLS-PPI proxy |
| BLS producer-price reports | 07 illustrative proxy, 08 price-scope contrast |
| BLS real sectoral-output report | 06 real sectoral-output growth |
| Original M11 human-pilot gate report | All 16 claims require external-readiness review; source measurements themselves are **not** changed by a pilot receipt |

Five prior **date-bound local derived report receipts** are mapped to eight source-qualified M35 observations; the remaining eight prohibited commercial inferences remain **blocked under every scenario**. Multiple altered sources produce the deduplicated union of affected claims.

## Crucial epistemic boundaries

- An external candidate JSON supplies *untrusted metadata digests only*. It is not a publisher source, a downloaded government table, a research approval, or an attested original-byte replay. The scanner never fetches the internet.
- **Derived report receipts incorporate the as-of date**, so comparisons are meaningful only against a baseline generated for the *same date*. A different digest flags a **hypothesis for revalidation**, not a confirmed publisher revision. Matching digests do not prove freshness.
- Revalidation requires independently fetching the controlling original publication, checking publisher/file identity, scope, historical revision status and arithmetic, then regenerating and reviewing M34 and M35. This implementation deliberately does not claim to complete those steps.
- No statistical statement gains external marketing rights from a changed/matching hash or passing CI; no actual invoices, signed buyer authority, independent human reviewers, collected cash, customer demand, market recoverability, or advertising approvals are supplied.
- All **18 preexisting P11 pilot gates remain unmet**. Their catalog is reused, never silently cloned or approved. No production Cloudflare or social/chatbot integration is modified here.

## Safeguards and usage

- Module: freight/research_source_lineage_m37.py composes original M34 source-family receipts and the M35 16-claim policy, strictly validates a narrow candidate schema, and generates metadata-only JSON/HTML receipts with **zero publication permissions**.
- Tests: freight/test_research_source_lineage_m37.py exercises all five roots, exact cross-source claim effects, union/deduplication, false human approvals, malformed metadata/unknown source families, same-day receipt comparison, HTML escaping and read-only CLI output.
- CI: .github/workflows/retally-source-impact-m37.yml runs offline inherited source policy tests, the original 14-lab report, a separate source-revision negative proof, and retains only derived receipts for 14 days. No recurring schedule or deployment.

Run locally with Python 3.11 and the existing research dependencies:

    PYTHONPATH=. python -m pytest -q freight/test_research_source_lineage_m37.py
    PYTHONPATH=. python -m freight.research_source_lineage_m37 --as-of-date 2026-10-12 --out /tmp/retally-m37
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m37-control

**What-if sample input** (use only with the same --as-of-date; never include customer identifiers or document contents):

    {
      "schema_version": 1,
      "scope": "LAB14_M37_UNTRUSTED_LOCAL_CANDIDATE_DIGESTS_NOT_PUBLISHER_VERIFICATION",
      "as_of": "2026-10-12",
      "source_receipts": {"CENSUS": "0000000000000000000000000000000000000000000000000000000000000000"},
      "original_publisher_replay_verified": false,
      "real_customer_evidence_verified": false,
      "external_publication_authorized": false
    }

Pass it via --candidate /tmp/metadata-only.json. The zero checksum is **fabricated for testing**. The expected *hypothetical* impact is M35-02, 03, 04 and 07, with every public/customer claim still blocked.

## Still required

A genuine publication revision must be verified separately against original government bytes. A genuine buyer pilot requires its own buyer authorization, secure data-rights setup, pre-registered frame, independent case truth/review, verified settlements and human legal/commercial publication signoff. Until then, these remain research preparation, not external claims.
