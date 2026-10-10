# RETALLY Lab 14 — Mission 6: Current Regulatory Source Verification

**Research date:** October 10, 2026. **Scope:** Read-only source research; not individualized legal advice, a carrier claim or a production release.

## Concrete source correction

Prior lab materials documented the April 16, 2018 Federal Register rule text for 49 CFR §378.8. That historical publication remains useful, but it alone cannot establish the regulation's current text.

A direct review of the eCFR page on October 10, 2026 found the following:

- URL: https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-378/section-378.8
- The page displays **Title 49 up to date as of October 1, 2026**. It describes the eCFR as authoritative but unofficial.
- Section 378.8 displays the carrier's **60-day written-claim disposition** provision, with an exception for a qualifying written extension based on extenuating circumstances.
- The same provision requires a written explanation of denials or different settlements, referring to tariff authority or other pertinent information.
- This observation does **not** establish that §378.8 governs a particular RETALLY customer's billing dispute, overrides a negotiated contract, guarantees a refund, or authorizes a third-party representative to act. Claim type, jurisdiction, contractual terms and statutory interactions need qualified review.

The lab now retains **both sources** under separate identifiers:

| Source ID | Date/scope | Research classification |
| --- | --- | --- |
| `20261010.govinfo.3788` | Federal Register, April 16, 2018 | Historical rule publication |
| `20261010.ecfr.current.3788` | eCFR Title 49 display through October 1, 2026 | Current published regulatory text observed; legal applicability not decided |

The claim `campaign.carrier.response` is linked to both records. Its quote anchors are separately identified, dates are validated, and any future or fabricated codification date is rejected. Lab 14 emits `CURRENT_ECFR_TEXT_OBSERVED_LEGAL_REVIEW_PENDING`, never a claim-approved or regulatory-clearance state.

## Other current-source checks

- **NMFTA:** The official update calendar records October 9, 2026 for disposition bulletin 2026-2; Supplement 2026-2 is scheduled to be issued November 12 and take effect **December 12, 2026**. Publication and future effectiveness are deliberately separated: https://help.nmfta.org/hc/en-us/articles/45360764355739-Upcoming-Key-Dates-for-the-NMFC-Data-Updates
- **49 U.S.C. §13710:** The original House-hosted source was unavailable during this check. Cornell's statutory transcription was directly accessible at https://www.law.cornell.edu/uscode/text/49/13710, but the existing House-source anchor remains `SEARCH_RESULT_ONLY` until its primary-source record is formally revised and reviewed. No retroactive fabricated primary-page observation is added.
- **RecoverAudit:** Its public pricing page says **20%** on amounts recovered and offers an initial **10-invoice** pilot: https://recover-audit.com/pricing. This remains an attributed vendor offer, not a signed service agreement, an independently established market price, or evidence of a customer preference.
- **BTS:** Its CFS article reports 2022 survey-covered shipment value and volume; it remains inappropriate to substitute commodity shipment value for audit revenue: https://www.bts.gov/newsroom/commodity-flow-survey-2022-data-released.
- **Estes:** Its public rules tariff page states that specific pricing agreements/contracts can contain exceptions to published charges: https://www.estes-express.com/resources/fees-and-surcharges/rules-tariff.

These observations do not create a broader independent competitor audit or freight recovery statistics.

## Implementation and acceptance

1. Added an approved direct eCFR source alongside the original historical Federal Register URL in the existing public-source manifest.
2. Preserved separate current and historical source identities and connected both to the same narrow research claim.
3. Added one short current eCFR excerpt record with an observed codification date and an explicit `regulatory_applicability_established: false` declaration.
4. Enhanced the existing source validator to reject copied/spoofed codification authority, misdated evidence and unsanctioned legal applicability claims.
5. Updated the manual one-shot public capture bound from 12 to **13 approved sources**, consistently in capture and detached-change review code; no schedules, automatic fetching or additional domains.
6. Updated Lab 14, tests and CI to check the current codification evidence and the legal review boundary.

### Operator commands

From the repository root with the appropriate existing Python test dependencies:

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_public_campaign.py freight/test_research_evidence_gate.py freight/test_research_source_acquisition.py freight/test_research_change_impact.py freight/test_lab_phase4_director.py
PYTHONPATH=. python -m freight.research_evidence_gate --as-of-date 2026-10-10 --out /tmp/retally-regulatory-recheck
```

Research outputs are internal-only JSON/HTML and cannot be used as customer authorization, legal advice or advertising proof. The source hash proves that the stored quote has not changed; it does not authenticate the issuing agency.

**Hard gates remain unchanged:** no customer data, filing, carrier communication, fee invoicing, external settlement, live deployment, schedule change, merger, or public marketing promotion from these findings. The entire mission is isolated to an unmerged research draft. 
