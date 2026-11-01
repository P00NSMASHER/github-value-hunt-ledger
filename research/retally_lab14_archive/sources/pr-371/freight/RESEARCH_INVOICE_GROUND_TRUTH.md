# RETALLY Existing Lab 14 — Mission 10: Synthetic Invoice Evidence & Adjudication

**Status:** Draft, research-only, stacked on unmerged Missions 9 → 8 → 7 → 6 → 5 → 4 → 3 → Phase 4. No production merge or hosted execution. No external study, real customer, data-acquisition or financial authority is created.

## Purpose

A motor-carrier invoice, dated rate authority, bill of lading/shipment record, payment proof, refund, independent evaluation and customer authorization are different evidence objects. These must be linked before a second-look freight audit can credibly claim a substantive result. Earlier Lab 14 missions surveyed public sources, then defined and rehearsed six studies. None supplied an authentic paid invoice with independently verified charge error. Mission 10 builds **one synthetic-only document and reviewer integrity instrument**, grounded to Mission 7 studies M7-01 (blind alerts) and M7-06 (cash economics).

This module deliberately **cannot receive or approve real invoices**. All ten shipments, invoices, dollars, contracts, cash events and reviewer identities were invented by code authors. The document SHA-256 fields validate the generated fictional text only: they are not signatures, copies of original invoices, contract authentication, bank proof or carrier acknowledgments.

## Statutory and technical source boundaries

- [49 CFR Part 378](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-378) concerns processing overcharge, duplicate-payment and overcollection claims for covered entities. Whether a rule controls a particular freight transaction, invoice, jurisdiction, negotiated contract or authorized claimant **cannot be decided from a general webpage**.
- [49 CFR §378.2](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-378/section-378.2) provides definitions of overcharge, duplicate payment and claimant, including the authorized-agent concept. A synthetic identity is not a legally authorized agent.
- [49 CFR §378.3](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-378/section-378.3) addresses written overcharge-type claims and collecting-carrier processing; this module does not file or adjudicate any claim.
- [49 U.S.C. §13710](https://www.govinfo.gov/content/pkg/USCODE-2024-title49/html/USCODE-2024-title49-subtitleIV-partB-chap137-sec13710.htm) describes particular billing dispute processes and timelines; applicability, waiver, other statutory deadlines and governing agreements require qualified counsel review. A 60-day response provision is not a guaranteed refund and must not be used in place of a claim-filing analysis.
- [X12 official 210 description](https://x12.org/node/4210) identifies an invoice/charge transaction format, not an automatically licensed rate contract, payment evidence, correctness oracle or real freight test corpus. No restricted X12 transaction structure or EDI sample was copied.

The code deliberately rejects loss/damage categories masquerading as overcharge cases. No legal filing deadline is calculated by the simulation.

## Fictional controlled scenario matrix

| Case | Simulated situation | Expected machine outcome |
| --- | --- | --- |
| SYN-GT-01 | Invoice $150; expected $120; paid $150 | Synthetic paid numeric difference **candidate**, not an actual overcharge |
| SYN-GT-02 | Invoice/rate/paid all $120 | Synthetic no-discrepancy control |
| SYN-GT-03 | Invoice $100 paid twice | Synthetic duplicate-payment candidate |
| SYN-GT-04 | Invoice paid, no dated rate authority | **Hold:** missing authority |
| SYN-GT-05 | Authority starts after shipment | **Hold:** rate ineffective on shipment date |
| SYN-GT-06 | Two blinded fictional reviewers disagree | **Hold:** contradictory labels |
| SYN-GT-07 | Historical invoice difference already refunded in fictional cash | No remaining cash excess |
| SYN-GT-08 | Invoice exceeds fictional rate but never paid | Unpaid billing difference; **zero recovered cash** |
| SYN-GT-09 | Rate record refers to a different carrier | **Hold:** authority scope mismatch |
| SYN-GT-10 | A carrier credit exists but has not been shown as refunded cash | **Hold:** credit reconciliation |

Amounts are fictional integers in cents, with explicitly pinned USD currency. An invoice difference is **not** necessarily a paid overcharge; a carrier credit is **not** cash returned to the customer; a historical refund cannot be counted again as new recovery.

## Structural admission controls

The evidence-chain validator enforces:

- Exactly ten fixed synthetic case identities, unique shipment/invoice IDs, and case-bound document and payment IDs, with no unknown/customer fields.
- Invoice and shipment record text bound to package IDs, dates and cents; separate fictional rate note with effective date, expiration and carrier; fictional payment/refund/credit events and their source text.
- SHA-256 internal document checksums plus exact source binding; a changed body with a recomputed checksum still fails when it contradicts the frozen case contract.
- USD currency across invoice, authority and payment events; exact integer cents, positive money events, no refund beyond actual simulated receipts, and causal event dates.
- Exactly two separately identified fictional blinded votes with explicit evidence document references and disagreement/abstention holds.
- No claimant authority, real-data access, external carrier action, legal approval, payment instruction, independent commercial benchmark or realized customer recovery. These flags are all explicitly false.
- The original held Mission 7 protocol report and checksum remain required. Mutated source documents and unsupported truth/approval promotions fail closed.

A signed buyer agreement, third-party chain-of-custody attestations, verified invoice originals, independently effective governing contracts, bank statements and actual adjudicators are **missing** by design. The process must not infer them from the existence of a JSON field or a passed synthetic test.

## Run and inspect

From repository root using Python 3.11+:

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_ground_truth.py
PYTHONPATH=. python -m freight.research_ground_truth --as-of-date 2026-10-10 --out /tmp/retally-ground-truth
# Open /tmp/retally-ground-truth/invoice_ground_truth.html
# Check /tmp/retally-ground-truth/invoice_ground_truth.json
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control
```

CI runs these tests, invokes the existing Lab 14 negative probe, generates an offline read-only report and uploads the HTML/JSON with the existing Research Intelligence artifacts. It **never** fetches or posts source material. SHA receipts are deterministic integrity checks, not external verification.

## Acceptance / next step

An authentic reference corpus must be developed in a **separately approved** process: data owner consent and scope, secure governed storage, original invoices and contract/rate versions, shipment evidence, bank/credit records, independent adjudicator blind labels, disputes and abstentions, and preapproved denominator/missingness rules. The independent real-data protocol requires privacy, commercial, legal and security review first. M10 has **ten simulated cases, zero admitted real invoices, zero real human adjudications, zero customer refunds, and zero approved public benchmarks**.

Existing 14-lab census, original 26 historical open findings, production safeguards and scheduled tasks remain unchanged. **DO NOT MERGE OR DEPLOY.**
