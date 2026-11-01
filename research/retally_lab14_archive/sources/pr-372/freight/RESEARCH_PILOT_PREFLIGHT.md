# RETALLY Existing Lab 14 — Mission 11: Independent Pilot Preflight

**Research-only draft, October 11, 2026.** Stacked on the unmerged Mission 10 and original Phase 4 research chain. This is not a deployment, an approved study, an external customer onboarding workflow or a new laboratory.

## Decision this work supports

**Can RETALLY safely ask a data owner to authorize a real-world, independently blinded second-look invoice audit and a claim-level realized contribution study?**

The current answer is **no—preparation is possible, but independent evidence and approvals are missing.** Mission 10 built a useful artificial evidence-chain laboratory. Its fictional source documents and two fictional reviewer labels do not establish source rights, actual invoice accuracy, security approval, legal authority, cash collection or independent human agreement. This Mission makes these omissions reviewable in one place rather than mistaking passed software tests for permission to act.

## What is delivered

- **freight/research/PILOT_PREFLIGHT_20261011.json**: 18 explicit, unmet, metadata-only human review requirements assigned to six stages and six responsible role types. Each lists the specific original evidence needed, the harm caused by its absence, intended research study IDs, and a preparatory step that can be done without live data.
- **freight/research_pilot_preflight.py**: deterministic, bounded, read-only validation and report generation. It verifies the original, in-scope Mission 7/8/9/10 report receipts and rejects false upgrades in any upstream report.
- **freight/test_research_pilot_preflight.py**: adversarial tests for fake buyer consent, real-case counters, false source permissions, missing or swapped controls, reviewer independence impersonation, forged original payment proof, cross-study provenance mismatch and unsafe report text.
- Existing **Lab 14** negative test and Control Center: the preflight runs on the current research stack without changing the original lab count or automatically closing 26 historical research findings.
- Read-only GitHub Actions: Python regression suite, an internal \`pilot_preflight.json\` / \`pilot_preflight.html\`, stored with the existing Lab 14 research artifact bundle. No browser, API or customer source fetch.

## 18 evidence requirements

| Phase | Human review / evidence requirements | Current state |
| --- | --- | --- |
| 1. Authority | Buyer signature and scope; representation/claims authority; all third-party license and onward-transfer rights | Not independently evidenced |
| 2. Security and privacy | Field minimization; encrypted access, separation and audit; buyer-specific retention/deletion/incident plan | Not independently evidenced |
| 3. Source documents | Invoice–shipment proof; dated contract/tariff version and carrier scope; independently reconciled payment/credit/refund ledger | Not independently evidenced |
| 4. Sampling | Complete eligible invoice frame and deduplication; prospective sample size/statistical estimand; fair, negative-controlled comparators | Not independently evidenced |
| 5. Blinded adjudication | Two separately accountable human reviewers; independently documented disagreement resolution; source-bound labels and error taxonomy | Not independently evidenced |
| 6. Economics and release | Actually collected, signed-fee-eligible cash; full inception costs and reversals; separate legal/business/security publication and disposition authority | Not independently evidenced |

The framework targets the existing M7-01 and M7-06 protocols. It does not create a license, sign a contract, or accept an actual invoice. **All 18 controls remain blocked** even if all underlying Python tests pass. Only a separately approved, secure, independently reviewed onboarding pathway can consider actual buyer evidence in the future. The current schema has **no permitted field for signatures, original source documents, personal contacts, credentials, customer identifiers, private files or self-declared approval**.

## Independent review is more than apparent agreement

In Mission 10, 9 of 10 artificial case pairs have matching fictional reviewer votes; one pair deliberately disagrees. That is **9/10 in a code-generated synthetic exercise**, not a human inter-rater reliability estimate, validation accuracy, sensitivity, false-positive rate, or real-world endorsement. Both labels originate from the same synthetic fixture generator. The preflight explicitly reports \`actual_independent_reviewer_reliability_established=false\`, requiring actual qualifications, reviewer identity/conflict handling, blinded assignment evidence and an independent tie-break for any real pilot.

## Data minimization and method guidance

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework): voluntary privacy risk identification and management; a framework is not proof that RETALLY has a tested secure environment or that any legal requirement is satisfied.
- [AAPOR Disclosure Standards](https://aapor.org/standards-and-ethics/disclosure-standards/): useful methodological guidance for reporting sampling frames, inclusion criteria, denominator, survey/nonresponse handling, coding and reproducibility. Not a freight-audit performance certification.

All third-party rights and actual controls need direct human review against the specific customer, carrier contract and data owner. There is no generic legal data-retention period imposed in code; the actual permitted period must be defined under the governing agreement and law. No unapproved contact, paid data purchase or data transfer is attempted.

## How to use offline

From repository root under Python 3.11 or newer:

\`\`\`bash
PYTHONPATH=. python -m pytest -q freight/test_research_pilot_preflight.py
PYTHONPATH=. python -m freight.research_pilot_preflight --as-of-date 2026-10-11 --out /tmp/retally-pilot-preflight
# Offline internal reports: /tmp/retally-pilot-preflight/pilot_preflight.html and pilot_preflight.json

PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control
# Open index.html > Pilot Readiness Checklist
\`\`\`

The JSON report includes SHA-256 receipts connecting the same M7 study designs, M8 synthetic study rehearsals, M9 public dataset discovery, M10 entirely fictional invoice evidence chains, and the M11 requirements. **These receipts are neither outside publisher signatures nor legal, financial, privacy, payment, security, or human-research attestations.** They only check that the declared local report payload has not changed since the digest was computed.

## How a real pilot could eventually start

The first actionable work is a manually reviewed **blank evidence rights and owner checklist**; followed by a safe intake/security architecture design; then an independently reviewed, prospective sampling/adjudication method. Real data must remain outside the lab until its actual legal/technical approvals, privacy handling, roles and storage boundaries have been established. Nothing in the M11 workbench represents these human milestones as complete.

Status: **18/18 genuine external evidence requirements unverified; 0 actual buyers consented, 0 real invoices ingested, 0 human blind reviewers appointed, 0 collected recovery revenue and 0 external claims authorized.** Original 14-lab census and 26 historical research findings are unchanged.

**DO NOT MERGE OR DEPLOY. DO NOT CHANGE SCHEDULED TASKS, CONTACT BUYERS/CARRIERS, ACCEPT CUSTOMER DOCUMENTS, OR ISSUE EXTERNAL PERFORMANCE CLAIMS.**
