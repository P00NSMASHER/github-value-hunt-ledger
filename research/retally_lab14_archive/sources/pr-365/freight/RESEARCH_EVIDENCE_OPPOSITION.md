# RETALLY Lab 14 — Evidence Fidelity & Opposition War Room (Mission 4)

**Status:** Draft-only, offline research, stacked on existing unmerged PRs #364, #363 and #297. No production launch or external operations are authorized.

## Purpose

The Phase 3/4 intelligence ledger records source-attributed **claims**, not independently certified market facts. Hashes of analyst summaries cannot prove that original pages contain, fully support or still agree with their assertions. This Mission adds short independent-to-the-summary source excerpts, coverage/age warnings and a falsifiable internal decision register.

This integrates inside **existing Lab 14**. The fourteen lab IDs, 26 historical open findings, review boundaries and commercial/security gates stay unchanged.

## Deliverables

- freight/research/SOURCE_ANCHORS_20261010.json: 13 short quote observations linked to 12 source URLs and 18 October campaign claims. Excerpts include exact URL, claim IDs, date, literal-number markers, quote hashes, method and limitation.
- freight/research_evidence_gate.py: quote integrity and citation binding, future-effective rule holds, manual context status, candidate decision prioritization, JSON + static HTML.
- freight/test_research_evidence_gate.py: adversarial checks for tampering, forged truth, cross-source citation laundering, future rules, wrong URLs, stale citations and malicious HTML.
- Existing Phase 4 Lab 14 and Control Center: source quality and six ranked research decisions, clearly separated from live customer outcomes.

## Distinctions the lab must preserve

- **BTS commodity shipments are NOT freight audit market size**. Missing invoice-level recovery rates and customer acquisition data cannot be inferred from trillions in cargo value.
- **RecoverAudit's 20% is a vendor-advertised offer**, not a market rate distribution or proof of conversion advantage.
- **Loop's accuracy percentages are vendor-published**, not independently validated RETALLY numbers.
- **RETALLY website rate wording and 49 USC 13710 search excerpts are search-index observations**, not directly authenticated live pages in this snapshot.
- **The 2018 Federal Register text for 49 CFR 378.8 is historical publication evidence**, not a current legal opinion or an engagement-specific rule.
- **NMFTA December 12, 2026 remains a future supplement effective date as of October 10, 2026**. Publication and legal/commercial effectiveness cannot be conflated.

## Six falsifiable research decisions

1. Independent pilot: buyer approval, secure intake, blind audit adjudication and reviewer-cost measurements.
2. Versioned legal/tariff/NMFC effective-date boundaries before rerating historical shipments.
3. Test whether a posted fee increases buyer comprehension relative to negotiated pricing, not by assuming it does.
4. Build a serviceable second-look market estimate from permitted invoice samples and evidence, not BTS commodity value.
5. Independently test competitor capabilities and RETALLY ingestion/enterprise security gaps.
6. Measure net fee-eligible recovery with actual approvals, reversals, refunds/credits, labor and attribution.

The decision ranking uses a transparent **internal ordinal heuristic** (three times impact, plus twice uncertainty, plus testability, minus effort). It is not a forecast, ROI, guaranteed margin, or spend authorization.

## Offline operating commands

From repository root with Python 3.11 or later:

    PYTHONPATH=. python -m pytest -q freight/test_research_evidence_gate.py
    PYTHONPATH=. python -m freight.research_evidence_gate --as-of-date 2026-10-10 --out /tmp/retally-mission4
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-phase4

The evidence gate exports evidence_fidelity.json, opposition_decisions.json, and opposition.html. The Phase 4 control center includes an additional link and summary. CI tests remain offline and read-only.

## Review limitations

A matching quote hash only proves the stored excerpt did not change, **not that the publisher signed, vouched for or maintains it**. Short excerpts cannot replace full context, governing contracts, independently verified customer data, licensing review or current law analysis. The recorded quote-support level is not a legal conclusion. Source presence and commercial validity remain separate decisions.

Pricing support and pricing objections may describe an unresolved buyer hypothesis rather than a literal factual contradiction. Missing contrary evidence cannot prove a competitor lacks a feature. Synthetic pilot and internal scorecards are not customer outcomes.

**Hard boundary:** no source fetch schedules, customer contact, carrier action, real invoice intake, contingent fee calculation, financial processing, external spending, production release, public marketing claim promotion or existing task changes are authorized by this research. Keep the draft unmerged until independently reviewed.
