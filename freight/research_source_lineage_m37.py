"""RETALLY existing Lab 14 / M37: offline macro-source change blast-radius review.

An observed digest supplied by an operator is an UNTRUSTED CANDIDATE, not
independent proof of new government source contents. Original publisher bytes
must be independently replayed and rechecked before any impacted internal
statistic is treated as source-revalidated. No customer or marketing authority.
"""
from __future__ import annotations

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_economic_denominator_m34 import report_shell as m34_report
from freight import research_claim_clearance_m35 as m35

SCOPE = "LAB14_M37_SOURCE_FAMILY_REVISION_BLAST_RADIUS_INTERNAL_ONLY"
CANDIDATE_SCOPE = "LAB14_M37_UNTRUSTED_LOCAL_CANDIDATE_DIGESTS_NOT_PUBLISHER_VERIFICATION"
ROOTS = ("BEA", "CENSUS", "BLS_PPI", "BLS_SECTORAL", "PILOT")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
# Exact lineage of the eight qualified source observations. M34 is a
# composite report, so do not mark all its measures stale on a change to
# only one of the original BEA, Census or BLS source families.
METRIC_ROOTS = {
    "BEA_2024_NOMINAL": ("BEA",),
    "CENSUS_2024_REVENUE": ("CENSUS",),
    "DENOMINATOR_2024_GAP": ("BEA", "CENSUS"),
    "CENSUS_TO_BEA_RATIO": ("BEA", "CENSUS"),
    "BEA_GROSS_OUTPUT_CHANGE": ("BEA",),
    "BLS_SECTORAL_CHANGE": ("BLS_SECTORAL",),
    "CENSUS_PPI_PROXY": ("CENSUS", "BLS_PPI"),
    "PRICE_SCOPE_GAP": ("BEA", "BLS_PPI"),
}
HUMAN_GATE_PREFIX = "P11-"
EXTERNAL_VETO = "BLOCKED_NO_INDEPENDENT_PILOT_AND_PUBLICATION_AUTHORITY"


def _sha(value: object) -> bool:
    return type(value) is str and SHA256.fullmatch(value) is not None


def _baseline(*, as_of: date) -> tuple[dict, dict[str, str]]:
    """Use already-validated date-bound local report receipts, not web data."""
    if type(as_of) is not date:
        raise ValueError("M37_AS_OF_DATE_INVALID")
    m35_report = m35.report_shell(as_of=as_of)
    m34 = m34_report(as_of=as_of)
    provenance = m35_report["source_provenance_receipts"]
    if m34["receipt_sha256"] != provenance["M34_economic_denominator"]:
        raise ValueError("M37_COMPOSITE_SOURCE_LINEAGE_CHANGED")
    # The individual upstream reports are already checked by M34 and M35,
    # including original-source provenance and false commercial-claim vetoes.
    originals = {
        "BEA": m34["prior_m33_first_party_bea_receipt_sha256"],
        "CENSUS": m34["prior_m25_census_receipt_sha256"],
        "BLS_PPI": m34["prior_m29_bls_ppi_receipt_sha256"],
        "BLS_SECTORAL": provenance["M31_BLS_sectoral"],
        "PILOT": provenance["M11_pilot_human_evidence"],
    }
    if set(originals) != set(ROOTS) or not all(_sha(v) for v in originals.values()):
        raise ValueError("M37_PRIOR_SOURCE_REPORT_RECEIPTS_INVALID")
    if (originals["BEA"] != provenance["M33_BEA_original"]
        or originals["BLS_PPI"] != provenance["M29_BLS_PPI"]):
        raise ValueError("M37_ORIGINAL_SOURCE_REPORT_RECONCILIATION_FAILED")
    if (m35_report["claim_count"] != 16
        or m35_report["qualified_internal_source_statements"] != 8
        or m35_report["blocked_unsupported_customer_business_claims"] != 8
        or m35_report["external_commercial_claims_authorized"] != 0
        or m35_report["independent_customer_pilot_human_approvals_unmet"] != 18):
        raise ValueError("M37_RESEARCH_TO_COMMERCIAL_GATE_CHANGED")
    policy = m35._policy()
    source_metrics = [x["metric_key"] for x in policy["claim_registry"][:8]]
    if set(source_metrics) != set(METRIC_ROOTS) or len(source_metrics) != 8:
        raise ValueError("M37_UNMAPPED_OR_DUPLICATE_SOURCE_CLAIM")
    for claim_id in m35.ALL_IDS:
        m35.lookup_claim(m35_report, claim_id)
    return m35_report, originals


def _candidate_receipts(candidate: object, *, as_of: date) -> dict[str, str]:
    if candidate is None:
        return {}
    if (type(candidate) is not dict
        or set(candidate) != {
            "schema_version", "scope", "as_of", "source_receipts",
            "original_publisher_replay_verified",
            "real_customer_evidence_verified", "external_publication_authorized",
        }
        or type(candidate["schema_version"]) is not int
        or candidate["schema_version"] != 1
        or candidate["scope"] != CANDIDATE_SCOPE
        or candidate["as_of"] != as_of.isoformat()
        or candidate["original_publisher_replay_verified"] is not False
        or candidate["real_customer_evidence_verified"] is not False
        or candidate["external_publication_authorized"] is not False):
        raise ValueError("M37_UNTRUSTED_CANDIDATE_STRUCTURE_OR_FALSE_APPROVAL")
    sources = candidate["source_receipts"]
    if (type(sources) is not dict or not 1 <= len(sources) <= len(ROOTS)
        or any(k not in ROOTS or not _sha(v) for k, v in sources.items())):
        raise ValueError("M37_UNREGISTERED_SOURCE_OR_INVALID_CANDIDATE_DIGEST")
    return sources


def candidate_template(*, as_of: date, root: str, digest: str) -> dict:
    """Produce a metadata-only hypothetical test; digest is never authenticated."""
    if root not in ROOTS or not _sha(digest):
        raise ValueError("M37_UNSUPPORTED_HYPOTHETICAL_SOURCE")
    return {
        "schema_version": 1, "scope": CANDIDATE_SCOPE,
        "as_of": as_of.isoformat(), "source_receipts": {root: digest},
        "original_publisher_replay_verified": False,
        "real_customer_evidence_verified": False,
        "external_publication_authorized": False,
    }


def report_shell(*, as_of: date, candidate: object = None) -> dict:
    baseline, original_receipts = _baseline(as_of=as_of)
    candidate_receipts = _candidate_receipts(candidate, as_of=as_of)
    changed = tuple(root for root in ROOTS
                    if root in candidate_receipts
                    and candidate_receipts[root] != original_receipts[root])
    matched = tuple(root for root in ROOTS
                    if root in candidate_receipts and root not in changed)
    source_rows = []
    for root in ROOTS:
        status = ("UNSUBMITTED_NOT_RECHECKED" if root not in candidate_receipts
                  else "CANDIDATE_DIFFERENCE_UNVERIFIED_REVALIDATE"
                  if root in changed else "CANDIDATE_DIGEST_MATCH_NOT_FRESH_PROOF")
        source_rows.append({
            "source_family": root,
            "prior_date_bound_local_report_receipt_sha256": original_receipts[root],
            "submitted_untrusted_candidate_receipt_sha256": candidate_receipts.get(root),
            "status": status,
            "new_original_publisher_bytes_replayed": False,
        })
    affected_source, affected_all, claims = [], [], []
    for old in baseline["source_claim_registry"]:
        claim_id = old["claim_id"]
        roots = (METRIC_ROOTS[old["metric_key"]] if old["metric_key"] is not None
                 else ("PILOT",))
        source_delta = tuple(root for root in changed
                             if root in roots and root != "PILOT")
        pilot_delta = "PILOT" in changed
        impacted = bool(source_delta or pilot_delta)
        if impacted:
            affected_all.append(claim_id)
        if source_delta and old["metric_key"] is not None:
            affected_source.append(claim_id)
        # Source revalidation never upgrades forbidden customer inferences.
        status = ("BLOCKED_UNSUPPORTED_CUSTOMER_INFERENCE"
                  if old["metric_key"] is None
                  else "SOURCE_REVALIDATION_REQUIRED_INTERNAL_ONLY"
                  if source_delta else "PRIOR_SOURCE_ONLY_NO_NEW_AUTHENTICATION")
        claims.append({
            "claim_id": claim_id,
            "metric_key": old["metric_key"],
            "metric_source_families": list(roots),
            "prior_internal_value": old["internal_value"],
            "candidate_source_changed": list(source_delta),
            "human_pilot_candidate_changed": pilot_delta,
            "source_revalidation_required": bool(source_delta),
            "affected_by_unverified_candidate": impacted,
            "internal_status": status,
            "external_status": EXTERNAL_VETO,
            "external_claims_authorized": False,
            "customer_recovery_or_market_proven": False,
            "required_unmet_human_signoffs": old["required_unmet_human_signoff_count"],
        })
    answer = {
        "schema_version": 1, "scope": SCOPE, "as_of": as_of.isoformat(),
        "lab": 14, "new_lab_created": False,
        "candidate_input_is_untrusted_metadata_only": True,
        "date_bound_receipts_are_not_stable_cross_date_source_content_hashes": True,
        "source_original_publisher_replay_completed_in_this_run": False,
        "report_changes_prove_actual_publisher_revisions": False,
        "original_pilot_human_signoffs_unmet": 18,
        "actual_customer_invoices_observed": 0,
        "real_cash_recovered_usd": None,
        "recoverable_freight_market_tam_usd": None,
        "external_commercial_claims_authorized": 0,
        "source_family_count": len(ROOTS),
        "candidate_sources_submitted": len(candidate_receipts),
        "candidate_sources_with_same_date_bound_receipt": list(matched),
        "candidate_sources_differing_from_prior_receipt": list(changed),
        "source_family_status": source_rows,
        "affected_internal_source_claim_ids": affected_source,
        "affected_all_claim_ids_including_pilot_review": affected_all,
        "all_eight_unsupported_business_claims_still_blocked": True,
        "claims": claims,
        "m35_source_claim_receipt_sha256": baseline["receipt_sha256"],
        "m34_original_source_lineage_receipt_sha256":
            baseline["source_provenance_receipts"]["M34_economic_denominator"],
        "no_source_authorization_or_pilot_status_modified": True,
        "no_customer_or_carrier_contact_or_data_import": True,
        "no_scheduled_task_or_production_deployment": True,
        "caveat": (
            "A digest comparison is a WHAT-IF source-lineage review, not "
            "a verified government publication revision or fresh original "
            "publisher replay. Derived report receipts are date-bound and "
            "must be compared only at the same as-of date. A different "
            "candidate digest can trigger revalidation but can never "
            "approve even the eight internally qualified facts for "
            "external marketing. All 18 real buyer pilot controls remain "
            "independently unverified. Never interpret national statistical "
            "denominator gaps as recoverable customer invoice errors."
        ),
    }
    answer["receipt_sha256"] = canon_hash(answer)
    return answer


def render_html(report: dict) -> str:
    rows = []
    for source in report["source_family_status"]:
        rows.append(
            "<tr><th>" + escape(str(source["source_family"])) +
            "</th><td>" + escape(str(source["status"])) + "</td></tr>"
        )
    cases = []
    for case in report["claims"]:
        if case["affected_by_unverified_candidate"]:
            cases.append(
                "<li><strong>" + escape(case["claim_id"]) + "</strong> — " +
                escape(case["internal_status"]) + "; public claims BLOCKED.</li>"
            )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Source impact / Lab 14</title>'
        '<style>body{font:15px/1.6 system-ui;color:#1b3026;background:#f5f8f6;'
        'margin:auto;max-width:900px;padding:28px}article{background:white;'
        'border:1px solid #dce6df;border-radius:16px;padding:23px;margin:20px 0}'
        'table{border-collapse:collapse;width:100%}td,th{border-bottom:'
        '1px solid #dce6df;padding:11px;text-align:left}small{color:#65746c}'
        '</style></head><body><h1>Research source-change blast radius</h1>'
        '<p><strong>Internal Lab 14 only.</strong> Untrusted local digest '
        'comparisons are not fresh publisher verification. Zero external '
        'claims or customer permissions authorized.</p><article>'
        '<h2>Five separate source families</h2><table><tbody>' +
        "".join(rows) + '</tbody></table></article><article><h2>Impacted '
        'claim cases (hypothetical)</h2><p>' +
        str(len(report["affected_all_claim_ids_including_pilot_review"])) +
        ' of 16 claim cases flagged; all 8 unsupported commercial claims '
        'remain blocked regardless.</p><ul>' + "".join(cases) +
        '</ul></article><p>All 18 independent customer-pilot human gates '
        'remain unmet. Original publication or customer records were not '
        'accessed. A SHA receipt is not third-party proof.</p><small>' +
        escape(report["receipt_sha256"]) + '</small></body></html>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only Lab 14 source impact review")
    ap.add_argument("--as-of-date", type=date.fromisoformat,
                    default=date.today())
    ap.add_argument("--candidate", type=Path,
                    help="Optional metadata-only unverified same-day digest scenario")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    incoming = (json.loads(args.candidate.read_text(encoding="utf-8"))
                if args.candidate is not None else None)
    report = report_shell(as_of=args.as_of_date, candidate=incoming)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "source_change_impact.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out / "source_change_impact.html").write_text(
        render_html(report), encoding="utf-8")
    print(json.dumps({
        "source_families": report["source_family_count"],
        "candidate_sources": report["candidate_sources_submitted"],
        "hypothetically_impacted_claims":
            len(report["affected_all_claim_ids_including_pilot_review"]),
        "external_claims_authorized": 0,
        "pilot_human_gates_unmet": 18,
        "receipt_sha256": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
