# RETALLY Research Intelligence Workbench — Lab 14

**Status:** review-only implementation on the existing unmerged 14-lab Phase 4 research chain. This is **not a new app, a 15th laboratory, autonomous browsing, commercial launch proof, or a production claim**.

## Purpose

RETALLY needs a repeatable intelligence process for freight recovery decisions. The workbench distinguishes research questions, attributed source summaries, adversarial challenges and independently tested decision evidence. Every material observation must identify the next test that could falsify it.

It extends **existing Lab 14** (competitor evidence freshness) and feeds the **Phase 4 Experiment Director and Control Center**. The original 14-lab census, 26 historical open findings, financial boundaries and competitor matrix remain unchanged.

## Eight research disciplines

| Lane | Main question | Evidence work |
| --- | --- | --- |
| market | Where is a realistically serviceable U.S. second-look LTL recovery opportunity? | Official freight statistics, data-backed segmentation, sampled invoices |
| competitive | Who competes directly, and how do they substantiate capabilities? | Direct specialists vs. FAP platforms, public pricing claims, original pages |
| opposition | What would a skeptical buyer or incumbent find wrong with RETALLY? | Documented blockers, falsifiable threats, independent negative testing |
| buyers | Who can authorize adoption, and why might they decline? | Public procurement terms and permissioned buyer evidence |
| carrier_regulatory | Which rules and rates actually control a dated dispute? | Tariffs, NMFC revisions, statutes, contract carve-outs |
| technology | Which competitor/open-source capabilities demonstrably work? | Public code licenses, tests, CI and execution proof |
| economics | Which recovery types produce positive realized contribution? | Net settlement, reversal, labor, attribution and collection evidence |
| strategy | What should RETALLY change first, and why? | Confidence, impact, falsification, dependencies, decision record |

**Current seeded coverage:** competitive and opposition contain dated observations. The other six lanes contain explicitly labeled **unanswered questions**, not fabricated market findings. Source collection is a next step, not a completed automatic scan.

## How to run

From repository root using Python 3.11+:

~~~bash
PYTHONPATH=. python -m unittest -v freight.test_research_intelligence
PYTHONPATH=. python -m freight.research_intelligence \
  --as-of-date 2026-10-10 --out /tmp/retally-market-intelligence
# View /tmp/retally-market-intelligence/research.html
# Machine report: /tmp/retally-market-intelligence/research_intelligence.json

PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-phase4
# View /tmp/retally-phase4/index.html, then open Research Intelligence.
~~~

The module reads repository evidence snapshots and exports local reports; **no network requests are performed**. Passing tests does not mean that vendor websites were recently checked.

### Reused evidence, not duplicated

- **freight/PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json:** dated first-party vendor public-claim *summaries*, five established FAP products. The importer does not claim newly downloaded pages.
- **freight/PHASE3_COMPETITIVE_MATRIX_2026-10-07.json:** internal engineering scoring rubric with unfavorable RETALLY dimensions. Not an independent product ranking.
- **freight/competitive_matrix.py:** original strict source-date and evidence-type validation.
- **freight/lab_phase4_director.py:** executes research as **Lab 14** and tests altered-hash rejection.
- **freight/lab_phase4_control_center.py:** adds eight-lane results and links to the operator report.

These vendor summaries were captured October 7, 2026 and expire January 5, 2027. Future analysis dates yield STALE_SOURCE_HOLD rather than silently extending their relevance. Missing website claims are not evidence that a competitor lacks a capability.

## Research registry input contract

A reviewed, externally gathered public-source registry can be processed using:

~~~bash
PYTHONPATH=. python -m freight.research_intelligence \
  --registry /path/to/reviewed_public_research.json \
  --as-of-date 2026-10-10 --out /tmp/retally-reviewed
~~~

**Illustrative schema only; the example is not an observed source:**

~~~json
{
  "schema_version": 1,
  "scope": "PUBLIC_RESEARCH_ONLY",
  "created_at": "2026-10-10",
  "sources": [
    {
      "id": "public.source.001",
      "type": "PUBLIC_PRIMARY",
      "url": "https://example.org/official-source",
      "publisher": "Example publisher",
      "captured_at": "2026-10-10",
      "valid_until": "2026-11-10",
      "excerpt": "Precisely scoped operator-collected source excerpt.",
      "excerpt_sha256": "SHA256_OF_EXACT_UTF8_EXCERPT"
    }
  ],
  "claims": [
    {
      "id": "review.claim.001",
      "lane": "market",
      "issue_key": "ltl-sample-scope",
      "subject": "Market sampling",
      "stance": "SUPPORT",
      "statement": "An attributed observation, not an established market-wide fact.",
      "classification": "PUBLIC_REPORT",
      "source_ids": ["public.source.001"],
      "importance": 3,
      "next_test": "Retrieve raw data and independently replicate its methodology."
    }
  ]
}
~~~

Calculate the hash with Python: **hashlib.sha256(excerpt.encode("utf-8")).hexdigest()**. This checks content integrity; it does **not** authenticate a publisher.

Source types: VENDOR_CLAIM_SNAPSHOT, INTERNAL_RESEARCH_SNAPSHOT, PUBLIC_PRIMARY, INDEPENDENT_REPORT. Claims can be VENDOR_CLAIM, INTERNAL_GAP, or PUBLIC_REPORT. Unsupported hypotheses belong in the open-question queue, not in the sourced-claim table.

Before admission, research operators should examine the original page or document, publisher, scope, effective date, licensing and applicable access terms. Public information obtained through appropriate connected research tools may be added only after independent operator review. This workbench does not automatically connect to those providers.

## Mandatory adversarial controls

- Reject unsafe source URLs, embedded credentials, duplicate IDs, future captures, missing or mutated source summaries, malformed sources, and unknown source IDs.
- Do not accept an input classification that claims VERIFIED or independent fact-checking. Vendor summaries remain VENDOR_CLAIM_UNVERIFIED.
- Opposing support and challenge records for the same issue result in CONTESTED_REQUIRES_REVIEW without an algorithmic winner.
- Expired source material results in STALE_SOURCE_HOLD.
- Every claim retains its source, source type, dated capture, expiry, risk/importance, counterevidence review status, and falsification step.
- RETALLY's own deficits are legitimate opposition findings. An unfavorable internal score must never be transformed into a favorable marketing claim.
- Escape research text in HTML and generate deterministic, offline JSON/HTML reports with content-digest receipts.
- Do not access customer invoices, private competitor data or code, carrier claims, payment authority, production secrets or external systems.
- Content hashes and receipts are **not** digital signatures, third-party attestation, source-truth guarantees or authorization to act.

## Follow-on research and acceptance

This release deliberately implements no autonomous web monitoring or unsupervised acquisition adapters. Current market, legal, pricing, buyer and technology observations must be acquired from authorized public providers and attached to reviewable, time-stamped evidence records.

Priority source campaigns:
1. Independent second-look LTL customer qualification and disclosed sampling.
2. Direct contingency recovery specialists (distinct from enterprise FAPs), with verified public pricing and contract limitations.
3. Carrier tariff/NMFC chronology and applicable legal deadlines with qualified review.
4. Blind, buyer-controlled product comparison using authorized historical invoices only after commercial/security gates.

**Hard gate:** no real freight data, carrier submissions, customer outreach, release, billing, fee collection, or public performance claim can be authorized from this research lab. Preserve all existing active tasks and release controls.
