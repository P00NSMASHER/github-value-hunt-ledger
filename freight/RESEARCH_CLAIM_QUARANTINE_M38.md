# RETALLY Research Lab 14 — Mission 38: quarantine affected historical claim values

**October 13, 2026 · DRAFT / INTERNAL RESEARCH ONLY · stacked on M37 PR #431.** No merger, production deployment, scheduled task, private customer data, outreach, cash activity or authorized marketing.

## Problem and control improvement

Mission 37 established five exact date-bound local source-report families and a 16-claim source dependency graph. It previously flagged an unverified changed fingerprint but still emitted the prior historical values in candidate scenario JSON. That created a foreseeable reuse hazard: a stale internal number might be copied while the source revision was under review.

**Mission 38 now redacts affected values, not merely flags them.** It adds a new, safe purpose-scoped claim-lookup interface, typed source-specific revalidation queues and integrated Lab 14 operator panels. Mission 37's own candidate-scenario JSON also withholds the affected prior values. Unaffected attributed figures remain *prior-source-qualified internal research with mandatory caveats*, never fresh publisher certification.

## Exact source-to-claim impact

| Hypothetical changed local report receipt | Internal M35 values held | Original-source validation needed |
| --- | --- | --- |
| BEA | 01, 03, 04, 05, 08 | Original GrossOutput.xlsx, NAICS 484 TGO105-A / price concepts; replay M33/M34 |
| Census | 02, 03, 04, 07 | Original 2017–2024 SAS/AIES employer receipts, 2022 survey revision bridge; replay M25/M34 |
| BLS producer prices | 07, 08 | Original PCU484---484--- annual PPI observations, scopes/years; replay M29/M34 |
| BLS sectoral output | 06 | Original real NAICS 484 sectoral-output release, not BEA gross; replay M31 |
| M11 independent pilot-control report | 0 internal statistical values | Reassess the original 18 buyer/legal/security/evidence/adjudication/economics human controls; all 16 external claim releases remain blocked |

Changing all four statistical report fingerprints holds **all 8 historical internal values**; changing multiple sources deduplicates the affected claim IDs. A PILOT candidate fingerprint never claims a newly signed contract or rewrites government statistics. In all scenarios the eight unsupported customer, real refunds, accuracy and recoverable-TAM inferences remain blocked.

## Important safeguards

- **No false source authentication:** original report SHA receipts are date-bound, derived local research checks, not stable source-byte fingerprints. A matching digest is *not* a new original-source replay. A different digest is only a hypothetical candidate for independent rechecking; no government series is downloaded in M38.
- **No forged approval:** the candidate input schema forbids human/replay/marketing permission. Unknown source roots, arbitrary fields and dates are rejected before creating output. A rehashed, altered upstream M37 report that leaks withheld numbers or attempts to clear a held claim is rejected by the new value gate.
- **No direct public publishing:** the M38 INTERNAL_RESEARCH purpose returns a historical figure only if its tracked source roots have not been flagged as changed; EXTERNAL_COMMERCIAL returns no figure under any conditions. The source registry's fixed original caveats are carried forward.
- **No customer rights:** all 18/18 independently required P11 human customer-pilot controls remain unmet. No private invoice, carrier bill, signed customer permission, actual recovered cash or serviceable market has been authenticated.
- **No automatic cross-system guard:** this read-only module does not intercept websites, social, chatbot, sales emails or any caller that directly bypasses the M38 safe-lookup interface. Separate actual mainline Cloudflare guard work remains in PR #430.

## Changed and added existing-lab components

- Module: freight/research_claim_quarantine_m38.py — exact claim access, source replay queue and safe JSON/HTML.
- Original source-impact module: freight/research_source_lineage_m37.py — additionally redacts impacted prior values in candidate scenario JSON.
- Adversarial regression: freight/test_research_claim_quarantine_m38.py — exact four source scenarios, all-root union, pilot candidate, an external purpose hard veto, forged approvals, modified upstream report receipts, unknown sources and HTML escaping.
- Control Center: freight/lab_phase4_control_center.py — a new M38 panel plus claim_quarantine.json and claim_quarantine.html.
- Original Lab 14: freight/lab_phase4_director.py — negative source mutation and safe public/internal lookup probes; total lab count remains **14**.
- PR/manual-only CI: .github/workflows/retally-claim-quarantine-m38.yml — source-policy regression, synthetic local report, real 14-lab gate checks, independent source-challenge proof, short-lived derived receipts. **No schedule or deployment**.

### Run

    PYTHONPATH=. python -m pytest -q freight/test_research_claim_quarantine_m38.py freight/test_research_source_lineage_m37.py
    PYTHONPATH=. python -m freight.research_claim_quarantine_m38 --as-of-date 2026-10-13 --out /tmp/retally-m38
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m38-control

For **hypothetical** source mutation only, create a same-as-of metadata-only candidate input such as:

    {
      "schema_version": 1,
      "scope": "LAB14_M37_UNTRUSTED_LOCAL_CANDIDATE_DIGESTS_NOT_PUBLISHER_VERIFICATION",
      "as_of": "2026-10-13",
      "source_receipts": {"CENSUS": "0000000000000000000000000000000000000000000000000000000000000000"},
      "original_publisher_replay_verified": false,
      "real_customer_evidence_verified": false,
      "external_publication_authorized": false
    }

The zero digest is **invented for testing**. Run the M38 CLI with --candidate /tmp/candidate.json and --out /tmp/retally-m38-scenario. In that scenario, M35-02, M35-03, M35-04 and M35-07 return a NULL safe_internal_value and are displayed as WITHHELD, even while their fixed M35 original values remain historically recorded upstream.

The default Control Center runs without a hypothetical candidate. This is intentionally separate from scenario-mode output: earlier non-quarantine reports and upstream source snapshots should not be mistaken for a scenario-cleared release bundle.

## Remaining external work

Original publisher bytes and any newer edition/release must be independently acquired and checked for a true revision before a refreshed M35 source report could replace prior values. Independently granted real buyer, legal, data, privacy, finance and publication approvals are prerequisites for any real customer-outcome claims. Neither CI nor a valid local SHA confers external release rights.
