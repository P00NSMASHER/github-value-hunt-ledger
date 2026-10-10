# RETALLY Public-Source Intelligence — Mission 3

**Status:** Draft branch stacked on PR #363 (which is stacked on PR #297). Read-only research. **No deployment, auto-monitor, customer authorization, carrier outreach, or legal determination.**

## What was executed in this mission

- A dated October 10, 2026 public-source research review covering all eight existing intelligence lanes.
- Twelve explicitly identified source URLs across BTS/FAF6, NMFTA, federal law/rule material, Estes, X12, SEC-hosted Cass disclosures and vendor public pages.
- Eighteen new source-linked observations, plus the existing Phase 3 competitive snapshot and internal RecoveryOS opposition records.
- An **actual oppositional question** against RETALLY: the public offer specifies a rate agreed before engagement, while a competing provider publicly advertises a 20% rate. This is an unresolved buyer-choice question, **not proof that one offer wins**.
- A manually triggered, bounded candidate-only source collector. It is never used by CI to access the network; CI tests use mock HTTP responses.
- Integration into **existing Lab 14** and the Phase 4 offline control center; original 14-lab census and 26 historical open findings remain unchanged.

## Eight lanes and evidence boundaries

| Lane | First sourced observation | Important unanswered question |
| --- | --- | --- |
| Market | BTS 2022 CFS and FAF6 data | How many shippers have economically actionable LTL invoice overpayments? |
| Competitive | RecoverAudit and Loop's own public marketing | What do real competing signed offers and blinded product tests show? |
| Opposition | Compare RETALLY's offer clarity to named public offers | Would qualified buyers prefer a posted price or a negotiated fee? |
| Buyers | BTS establishes surveyed manufacturing/wholesale and selected retail sectors | Who has authority and an unmet second-look problem? |
| Carrier/regulatory | House codification, NMFTA, 2018 Federal Register, Estes | What contract and applicable dated legal authority controls each case? |
| Technology | X12 210, Loop's claimed split benchmark | Can RETALLY run a truly blinded real-invoice comparison? |
| Economics | SEC-hosted Cass issuer-reported scale, one vendor fee example | What is RETALLY's realized contribution per actual claim? |
| Strategy | NMFTA 2026-2 future effective date, BTS segmentation | Which auditable pilot beats generic enterprise-feature parity work? |

These are **attributed research observations**, not customer outcomes or audit-performance certifications. Source records contain analyst summaries plus SHA-256 of the summary; the hash does not authenticate the page or publisher. A failed current-site retrieval must not be replaced with invented text.

## Working commands

From repository root:

~~~bash
# Run both legacy research and the new public campaign with no network.
PYTHONPATH=. python -m freight.research_intelligence \
  --include-public-campaign --as-of-date 2026-10-10 \
  --out /tmp/retally-public-research

# View research.html and research_intelligence.json.
# Existing Lab 14 and control center also include this research:
PYTHONPATH=. python -m freight.lab_phase4_control_center \
  --out /tmp/retally-phase4

# Negative tests run fully offline:
PYTHONPATH=. python -m pytest -q \
  freight/test_research_intelligence.py \
  freight/test_research_public_campaign.py \
  freight/test_research_source_acquisition.py \
  freight/test_lab_phase4_director.py
~~~

To capture a *new candidate* from a small, preapproved public source list, an operator may explicitly execute the following **one time**:

~~~bash
PYTHONPATH=. python -m freight.research_source_acquisition \
  --manifest freight/research/PUBLIC_SOURCE_MANIFEST_20261010.json \
  --source-id nmfta.timeline.2026 \
  --execute --out /tmp/retally-nmfta-candidate.json
~~~

**That command was not run against live endpoints by this PR or CI.** It does not create an approved claim or silently update the research database. It only creates an unreviewed candidate receipt, with bounded text preview, source/body hash, URL, time, MIME type, explicit failure state and no stored full-page copy. It does not retain PDF/binary source documents. It requires explicit invocation. The fixed source manifest contains 12 URLs; maximum requests/run is 12; maximum response size is 256,000 bytes; timeout is 8 seconds per request; unexpected redirects, unapproved hosts, disallowed MIME, private/nonpublic DNS results and embedded credentials are rejected. This is defense-in-depth on an approved host list, not a general arbitrary-URL safe browsing service.

## Verification and admission procedure

1. **Select a source from the version-controlled approved manifest.** Review access terms and current use rights. Do not use private documents, authenticated pages, bypass controls, or store customer/competitor personal information.
2. **Capture** a page only with human authorization using the one-shot CLI, or review a page through authorized public research tools. Do not classify it as verified merely because HTTP 200 was returned.
3. **Inspect** the original publication date, applicability, cited documents, contracting exceptions and contradictory evidence. Preserve an exact source URL and appropriately narrow analyst summary. Attach actual timestamp and checksum where collection was performed.
4. **Formulate** a narrow, source-supported observation in the registry and name a test that would falsify or limit its importance. Vendor reports remain vendor claims. Internal rubric results remain internal.
5. **Review** claims and counterclaims by issue key. Conflicts become CONTESTED_REQUIRES_REVIEW. Expired source content becomes STALE_SOURCE_HOLD. No automatic truth promotion.
6. **Release a finding** for internal review only. Separate legal review, commercial acceptance, and actual customer proof are needed for outward claims or financial decisions.

## Important legal and classification distinction

NMFTA's disposition bulletin was published October 9, 2026. Its 2026-2 supplement was scheduled effective **December 12, 2026** (future as of the campaign). RETALLY must **not** apply scheduled rules to shipments where they did not yet govern.

The earlier report treated 49 CFR 378.8 as current without a reliable first-party page capture. A source URL to the current eCFR text was not reliably retrievable through the available research interface. The campaign therefore links the **2018 Federal Register** amendment text instead and explicitly requests a present-day applicability check with qualified counsel. It does not misrepresent 2018 publication as an October 2026 official validation.

Section 13710(a)(3)(B)'s 180-day billing contest concept and Part 378's 60-day written claim disposition are **distinct**; neither is a universal claim deadline or automatically approved recovery.

## Artifact lineage

- Public capture allowlist: [PUBLIC_SOURCE_MANIFEST_20261010.json](research/PUBLIC_SOURCE_MANIFEST_20261010.json)
- Reproducible source-linked campaign: [research_public_campaign.py](research_public_campaign.py)
- Capture engine: [research_source_acquisition.py](research_source_acquisition.py)
- Existing engine / dashboard: [research_intelligence.py](research_intelligence.py) and [lab_phase4_control_center.py](lab_phase4_control_center.py)
- Regression coverage: [test_research_public_campaign.py](test_research_public_campaign.py), [test_research_source_acquisition.py](test_research_source_acquisition.py)

The dated evidence seed is reproducible from its versioned source summaries, not a cryptographically signed third-party archive. Confidence cannot be upgraded by rehashing. No evidence source is permission to contact carriers, spend funds, accept confidential invoices, publish recovery percentages, file claims, process settlements or merge/deploy.

## Next commercially meaningful validation

A controlled **real-customer, buyer-authorized pilot** is still the missing independent evidence. Before it is allowed, complete the existing security, legal, buyer authority and private-document intake release gates. Measure false positives, source completeness, claim acceptance, credit realization and actual analyst labor. Use those results to determine where RETALLY can reliably make money, instead of extrapolating from CFS totals, vendor contingency percentages or synthetic data.
