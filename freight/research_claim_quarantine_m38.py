"""RETALLY Research Lab 14 / M38: fail-closed internal claim quarantine.

M37 detects *hypothetical* source-family receipt differences. M38 turns
that finding into a safe internal value-access and replay queue: an affected
historical number is withheld pending independent original-source review.
Neither a digest nor a test is publisher authentication or authorization to
publish/customer-contact/collect fees. This does not inspect public web copy.
"""
from __future__ import annotations

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path

from freight.research_evidence_gate import canon_hash
from freight import research_source_lineage_m37 as m37
from freight import research_claim_clearance_m35 as m35

SCOPE = "LAB14_M38_INTERNAL_RESEARCH_SOURCE_QUARANTINE_NO_REPLAY_OR_PUBLICATION"
INTERNAL = "INTERNAL_RESEARCH"
EXTERNAL = "EXTERNAL_COMMERCIAL"
PURPOSES = (INTERNAL, EXTERNAL)
STATUSES = {
    "VISIBLE": "PRIOR_DERIVED_SOURCE_WITH_CAVEATS_NOT_FRESH_PUBLISHER_PROOF",
    "WITHHELD": "QUARANTINED_UNVERIFIED_SOURCE_CHANGE_REPLAY_REQUIRED",
    "BLOCKED": "BLOCKED_UNSUPPORTED_CUSTOMER_OR_MARKET_INFERENCE",
}
REPLAY = {
    "BEA": {
        "owner_role": "RESEARCH_LEAD",
        "controlling_original": "BEA GrossOutput.xlsx, annual NAICS 484 TGO105-A and price-index scope",
        "inherited_modules": [
            "freight/research_bea_original_m33.py",
            "freight/research_economic_denominator_m34.py",
        ],
        "independent_replay_steps": [
            "Independently retrieve original BEA publisher workbook and record exact publisher/version identity.",
            "Recheck years, NAICS 484 classification, units, TGO105-A rows, real/nominal and price scope.",
            "Re-run M33 and M34 source/ratio regressions before proposing a revised internal statement.",
        ],
    },
    "CENSUS": {
        "owner_role": "RESEARCH_LEAD",
        "controlling_original": "Census original SAS-to-AIES trucking employer revenue 2017–2024",
        "inherited_modules": [
            "freight/research_sas_aies_bridge.py",
            "freight/research_economic_denominator_m34.py",
        ],
        "independent_replay_steps": [
            "Reacquire original Census publisher datasets with edition and archive hashes.",
            "Check NAICS 484 employer receipts, revised SAS years, AIES transition and suppression flags.",
            "Re-run M25 and M34 revenue/denominator arithmetic without calling it invoiced freight TAM.",
        ],
    },
    "BLS_PPI": {
        "owner_role": "RESEARCH_LEAD",
        "controlling_original": "Original BLS trucking parent PPI PCU484---484--- annual-mean series",
        "inherited_modules": [
            "freight/research_unified_blspci.py",
            "freight/research_economic_denominator_m34.py",
        ],
        "independent_replay_steps": [
            "Reacquire original BLS PCU484---484--- time series with dates and reference period.",
            "Check indexed monthly values, annual averaging, rebasing and producer-price scope.",
            "Re-run M29/M34 proxy and price contrast, preserving their illustrative/noninterchangeable status.",
        ],
    },
    "BLS_SECTORAL": {
        "owner_role": "RESEARCH_LEAD",
        "controlling_original": "BLS NAICS 484 real sectoral-output original release",
        "inherited_modules": ["freight/research_bls_sectoral_output_m31.py"],
        "independent_replay_steps": [
            "Independently retrieve original BLS sectoral-output release with vintage and series ID.",
            "Check 2017–2024 real-output comparability, sectoral exclusions and revisions.",
            "Re-run M31 and do not relabel sectoral output as BEA gross output or freight tonnage.",
        ],
    },
    "PILOT": {
        "owner_role": "DATA_OWNER_LEGAL_COUNSEL_SECURITY_OWNER_RESEARCH_LEAD_ADJUDICATOR_FINANCE",
        "controlling_original": "Original P11 18 independent human customer-pilot evidence controls",
        "inherited_modules": ["freight/research_pilot_preflight.py"],
        "independent_replay_steps": [
            "Recheck independently authenticated buyer, data-rights and privacy/security evidence outside this report.",
            "Independently verify original invoice frame, masked truth, adjudication and final payment evidence.",
            "Obtain distinct legal, security and commercial publication approvals; CI cannot grant them.",
        ],
    },
}
ROOTS = tuple(REPLAY)
MIN_DATE = date(2026, 10, 12)


def _impact(*, as_of: date, candidate: object) -> dict:
    if type(as_of) is not date or as_of < MIN_DATE:
        raise ValueError("M38_AS_OF_BEFORE_EXISTING_PUBLISHER_SOURCE_BASELINE")
    impact = m37.report_shell(as_of=as_of, candidate=candidate)
    if (impact.get("scope") != m37.SCOPE
        or impact.get("lab") != 14
        or impact.get("new_lab_created") is not False
        or impact.get("source_family_count") != len(ROOTS)
        or impact.get("original_pilot_human_signoffs_unmet") != 18
        or impact.get("external_commercial_claims_authorized") != 0
        or impact.get("report_changes_prove_actual_publisher_revisions") is not False
        or impact.get("source_original_publisher_replay_completed_in_this_run") is not False
        or impact.get("candidate_input_is_untrusted_metadata_only") is not True):
        raise ValueError("M38_UPSTREAM_INTERNAL_RESEARCH_BOUNDARY_BROKEN")
    if set(REPLAY) != set(m37.ROOTS):
        raise ValueError("M38_UNMAPPED_SOURCE_FAMILY")
    return impact


def report_shell(*, as_of: date, candidate: object = None) -> dict:
    """Build a usable, never-self-approving quarantine view from M37 + M35.

    A candidate digest is not a verified original publication revision.
    Changed roots require a human original-source check *before* the
    historical value can be supplied through this view.
    """
    impact = _impact(as_of=as_of, candidate=candidate)
    policy = m35._policy()
    changed = impact["candidate_sources_differing_from_prior_receipt"]
    changed_set = set(changed)
    claims = []
    quarantined = []
    for old, entry in zip(impact["claims"], policy["claim_registry"]):
        cid = entry["id"]
        if old.get("claim_id") != cid or cid not in m35.ALL_IDS:
            raise ValueError("M38_CLAIM_ID_OR_ORDER_CORRUPTED")
        metric = entry["metric_key"]
        if old.get("metric_key") != metric or old.get("external_claims_authorized") is not False:
            raise ValueError("M38_FALSE_CLAIM_AUTHORITY_OR_METRIC_CHANGE")
        root_links = list(m37.METRIC_ROOTS[metric]) if metric is not None else ["PILOT"]
        affected = [root for root in root_links if root in changed_set and root != "PILOT"]
        held = bool(affected)
        if bool(old.get("source_revalidation_required")) != held:
            raise ValueError("M38_SOURCE_QUARANTINE_DID_NOT_FOLLOW_ROOT_CHANGE")
        if (old.get("candidate_source_changed") != affected
            or old.get("external_status") != m37.EXTERNAL_VETO):
            raise ValueError("M38_REVALIDATION_LINEAGE_OR_EXTERNAL_VETO_CHANGED")
        if metric is None:
            status, safe_value = STATUSES["BLOCKED"], None
        elif held:
            # M37 must ALSO redact affected historical figures in its own
            # scenario report. Do not permit raw values through a JSON copy.
            if old.get("prior_internal_value") is not None:
                raise ValueError("M38_UPSTREAM_STALE_SOURCE_VALUE_EXPOSED")
            status, safe_value = STATUSES["WITHHELD"], None
            quarantined.append(cid)
        else:
            if old.get("prior_internal_value") != entry["expected_value"]:
                raise ValueError("M38_PRIOR_ATTESTED_VALUE_OR_SOURCE_POLICY_CHANGED")
            status, safe_value = STATUSES["VISIBLE"], entry["expected_value"]
        claims.append({
            "claim_id": cid,
            "source_metric": metric,
            "evidence_grade": entry["evidence_class"],
            "source_families": root_links,
            "changed_untrusted_source_families": affected,
            "internal_access_status": status,
            "safe_internal_value": safe_value,
            "mandatory_internal_caveat": entry["caveat"],
            "source_revalidation_required": held,
            "public_release_status": "BLOCKED_NO_INDEPENDENT_HUMAN_PUBLICATION_AUTHORITY",
            "external_publication_authorized": False,
            "customer_invoice_error_or_cash_recovery_proven": False,
            "original_human_gate_ids": entry["required_pilot_gate_ids"],
        })
    if (len(claims) != 16 or len([x for x in claims if x["source_metric"]]) != 8
        or len(quarantined) != len(impact["affected_internal_source_claim_ids"])
        or quarantined != impact["affected_internal_source_claim_ids"]
        or any(x["external_publication_authorized"] for x in claims)):
        raise ValueError("M38_EIGHT_SOURCE_CLAIMS_OR_BLOCKED_INFERENCES_INVALID")
    queue = []
    for root in m37.ROOTS:
        if root not in changed_set:
            continue
        contract = REPLAY[root]
        # All eight unsupported interpretations stay blocked independent
        # of whether a source or the buyer pilot authorization changes.
        impacted = ([x["claim_id"] for x in claims if root in
                     x["changed_untrusted_source_families"]] if root != "PILOT"
                    else list(m35.ALL_IDS))
        queue.append({
            "root": root,
            "hypothetical_only_not_authenticated_publisher_change": True,
            "state": "AWAITING_INDEPENDENT_ORIGINAL_EVIDENCE_REPLAY",
            "owner_role_not_an_assigned_real_person": contract["owner_role"],
            "original_evidence_description": contract["controlling_original"],
            "already_existing_source_modules": contract["inherited_modules"],
            "necessary_independent_replay_steps": contract["independent_replay_steps"],
            "affected_claim_ids": impacted,
            "human_approval_reported_by_this_module": False,
            "publication_authorized_by_this_module": False,
        })
    # Never include untrusted candidate digests in a human-access report;
    # M37 keeps its separate metadata-only source comparison provenance.
    answer = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of": as_of.isoformat(),
        "existing_lab_number": 14,
        "new_lab_created": False,
        "mode": "READ_ONLY_INTERNAL_RESEARCH_WITH_HYPOTHETICAL_QUARANTINE",
        "source_family_count": len(ROOTS),
        "qualified_historical_source_claims": 8,
        "qualified_values_still_visible_for_internal_research_only": 8 - len(quarantined),
        "qualified_values_withheld_pending_independent_replay": len(quarantined),
        "quarantined_claim_ids": quarantined,
        "prohibited_customer_market_claims_blocked": 8,
        "independently_unverified_human_pilot_controls": 18,
        "external_claims_authorized": 0,
        "actual_customer_invoices_observed": 0,
        "net_cash_recovered_usd": None,
        "recoverable_market_tam_usd": None,
        "candidate_source_deltas_unverified": changed,
        "pending_source_replay_count": len(queue),
        "independent_original_publisher_replays_in_this_run": 0,
        "candidate_digest_matching_cannot_establish_source_freshness": True,
        "source_revision_independently_verified": False,
        "pilot_gate_independently_satisfied_by_this_module": False,
        "no_customer_or_carrier_contact_or_data_import": True,
        "no_new_schedule_or_production_change": True,
        "source_impact_report_receipt_sha256": impact["receipt_sha256"],
        "claims": claims,
        "independent_source_revalidation_queue": queue,
        "scope_caveat": (
            "M38 is a safer internal view of M35 claims when untrusted same-day "
            "M37 source fingerprints differ. Withheld historical values require "
            "a separately authenticated original-publisher replay; this module "
            "does not download or authenticate new original source bytes. "
            "Public economic observations do not establish customer invoices, "
            "freight overcharges, actual refunds, market TAM, buyer consent "
            "or permission to publish. All 18 original human pilot controls "
            "remain unmet; passing CI cannot supply those rights."
        ),
    }
    answer["receipt_sha256"] = canon_hash(answer)
    return answer


def claim_view(*, as_of: date, claim_id: str, purpose: str,
               candidate: object = None) -> dict:
    """Safe query: regenerate original bound evidence; never trust a supplied report.

    EXTERNAL_COMMERCIAL is always blocked, even when the source equals a
    prior digest or there is no hypothetical change.
    """
    if type(claim_id) is not str or claim_id not in m35.ALL_IDS:
        raise ValueError("M38_UNKNOWN_CLAIM_ID")
    if type(purpose) is not str or purpose not in PURPOSES:
        raise ValueError("M38_UNRECOGNIZED_CLAIM_USE")
    fresh = report_shell(as_of=as_of, candidate=candidate)
    row = fresh["claims"][m35.ALL_IDS.index(claim_id)]
    internal = purpose == INTERNAL
    safe_value = row["safe_internal_value"] if internal else None
    status = (row["internal_access_status"] if internal
              else "BLOCKED_ALL_EXTERNAL_CUSTOMER_MARKETING_CLAIMS")
    return {
        "claim_id": claim_id,
        "purpose": purpose,
        "decision": status,
        "safe_value": safe_value,
        "mandatory_caveat": row["mandatory_internal_caveat"],
        "candidate_change_is_publisher_authentication": False,
        "external_publication_authorized": False,
        "real_customer_evidence_or_cash_verified": False,
        "pilot_independent_human_signoffs_unmet": 18,
    }


def render_html(report: dict) -> str:
    cards = []
    for claim in report["claims"]:
        value = ("WITHHELD — original source replay required"
                 if claim["source_revalidation_required"]
                 else str(claim["safe_internal_value"]) if
                 claim["safe_internal_value"] is not None else "BLOCKED")
        cards.append(
            '<tr><th>' + escape(str(claim["claim_id"])) +
            '</th><td>' + escape(str(claim["internal_access_status"])) +
            '</td><td>' + escape(value) +
            '</td><td>' + escape(str(claim["mandatory_internal_caveat"])) +
            '</td></tr>'
        )
    tasks = []
    for task in report["independent_source_revalidation_queue"]:
        steps = "".join('<li>' + escape(str(step)) + '</li>'
                        for step in task["necessary_independent_replay_steps"])
        tasks.append(
            '<article><h3>' + escape(str(task["root"])) + ' — unverified'
            ' candidate fingerprint</h3><p>' +
            escape(str(task["original_evidence_description"])) +
            '</p><p>Impacted cases: ' +
            escape(", ".join(task["affected_claim_ids"])) +
            '</p><ol>' + steps + '</ol></article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Research quarantine / Lab 14</title>'
        '<style>body{font:15px/1.6 system-ui;color:#21382d;background:#f5f8f5;'
        'margin:auto;max-width:1100px;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'td,th{padding:12px;text-align:left;border-bottom:1px solid #dfe8e0}'
        'table{overflow-wrap:anywhere}article{background:white;padding:17px;'
        'margin:16px 0;border:1px solid #dfe8e0;border-radius:12px}'
        '.muted{color:#53645b}main{max-width:1100px;margin:auto}</style>'
        '</head><body><main>'
        '<small>RETALLY / EXISTING RESEARCH LAB 14 / M38 / INTERNAL ONLY</small>'
        '<h1>Research source quarantine</h1>'
        '<p><strong>' +
        str(report["qualified_values_withheld_pending_independent_replay"]) +
        '/8 historical source values withheld</strong> for possible '
        'source revisions. Source receipt differences are hypothetical and '
        'not verified new publisher releases. <strong>0 external claims '
        'authorized. 18/18 original human pilot gates unmet.</strong></p>'
        '<h2>Safe internal-only typed claim view</h2>'
        '<table><thead><tr><th>Case</th><th>Internal status</th>'
        '<th>Safe value</th><th>Mandatory qualification</th></tr></thead>'
        '<tbody>' + "".join(cards) + '</tbody></table>'
        '<h2>Required independent original-source replay queue</h2>' +
        ("".join(tasks) if tasks else '<p>No submitted differences. '
         'Existing report digests do not establish fresh source authenticity.'
         '</p>') +
        '<p class="muted">All eight unsupported real-customer/TAM inferences '
        'remain blocked. No real invoice data, cash, legal signoffs or '
        'production changes. A local SHA is not publisher or human approval.</p>'
        '<small>' + escape(str(report["receipt_sha256"])) +
        '</small></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat,
                        default=date.today())
    parser.add_argument("--candidate", type=Path,
                        help="Optional untrusted same-day M37 metadata-only JSON")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidate = (json.loads(args.candidate.read_text(encoding="utf-8"))
                 if args.candidate is not None else None)
    result = report_shell(as_of=args.as_of_date, candidate=candidate)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "claim_quarantine.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "claim_quarantine.html").write_text(
        render_html(result), encoding="utf-8"
    )
    print(json.dumps({
        "internally_visible_prior_source_values":
            result["qualified_values_still_visible_for_internal_research_only"],
        "quarantined_source_values":
            result["qualified_values_withheld_pending_independent_replay"],
        "independent_publisher_replays": 0,
        "prohibited_customer_claims": 8,
        "external_publication_authorized": 0,
        "pilot_independent_signoffs_unmet": 18,
        "receipt_sha256": result["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
