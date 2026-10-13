"""Fail-closed, scenario-only Research Lab Control Center consumer for M38.

This intentionally does not render or export M11-M35 historical archives.
Historical reports are retained separately, but they are NOT candidate-cleared
value feeds. The only usable historical claim values in this scenario bundle
come from M38's source-aware, internal-only claim table. No customer authority.
"""
from __future__ import annotations

from datetime import date
from html import escape
import json
from pathlib import Path

from freight.research_evidence_gate import canon_hash
from freight import research_source_lineage_m37 as m37
from freight import research_claim_quarantine_m38 as m38

SCOPE = "LAB14_M38_CONTROL_CENTER_UNTRUSTED_SOURCE_SCENARIO_INTERNAL_ONLY"


def scenario_bundle(*, as_of: date, candidate: object) -> dict:
    """Compile only candidate-aware reports; never carry legacy raw values."""
    if candidate is None:
        raise ValueError("M38_CONTROL_CENTER_CANDIDATE_REQUIRED")
    impact = m37.report_shell(as_of=as_of, candidate=candidate)
    quarantine = m38.report_shell(as_of=as_of, candidate=candidate)
    if (impact["receipt_sha256"] != quarantine["source_impact_report_receipt_sha256"]
        or impact["as_of"] != quarantine["as_of"]
        or impact["candidate_sources_submitted"] < 1
        or impact["original_pilot_human_signoffs_unmet"] != 18
        or impact["external_commercial_claims_authorized"] != 0
        or quarantine["independently_unverified_human_pilot_controls"] != 18
        or quarantine["external_claims_authorized"] != 0
        or quarantine["source_revision_independently_verified"] is not False
        or quarantine["qualified_values_withheld_pending_independent_replay"]
           != len(impact["affected_internal_source_claim_ids"])):
        raise ValueError("M38_CONTROL_CENTER_SCENARIO_EVIDENCE_MISMATCH")
    if (len(quarantine["claims"]) != 16
        or len(impact["claims"]) != 16
        or [c["claim_id"] for c in quarantine["claims"]
            if c["safe_internal_value"] is None
            and c["source_metric"] is not None]
           != impact["affected_internal_source_claim_ids"]
        or any(c["external_publication_authorized"] is not False
               for c in quarantine["claims"])):
        raise ValueError("M38_CONTROL_CENTER_UNSAFE_CLAIM_ACCESS")
    report = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of": as_of.isoformat(),
        "existing_lab": 14,
        "scenario_only": True,
        "existing_lab_executions_replayed_in_this_scenario": 0,
        "historical_archives_included_or_rewritten": False,
        "legacy_unquarantined_source_reports_exported": False,
        "research_value_access": "claim_quarantine.claims.safe_internal_value_INTERNAL_RESEARCH_ONLY",
        "external_customer_marketing_or_recovery_claims_authorized": 0,
        "independent_human_customer_pilot_controls_unmet": 18,
        "new_original_publisher_replays_authenticated": 0,
        "real_customer_invoices_observed": 0,
        "actual_recovered_cash_usd": None,
        "recoverable_freight_market_tam_usd": None,
        "source_impact": impact,
        "claim_quarantine": quarantine,
        "caveat": (
            "This candidate-scoped Control Center bundle deliberately excludes "
            "legacy M34/M35 and other raw publisher-history exports, which "
            "remain separately archived but are not scenario-cleared. Unaffected "
            "historical M35 claims remain accessible with their original caveats "
            "only through M38. No publisher revision, buyer authority, customer "
            "recovery, legal review or public marketing claim was verified."
        ),
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


def write_scenario(*, as_of: date, candidate_path: Path, out: Path) -> dict:
    """Fail before writing on invalid inputs or a nonempty output directory.

    A fresh directory prevents leftover raw M34/M35 files from appearing beside
    the safe scenario bundle and being mistaken for scenario-cleared exports.
    """
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    bundle = scenario_bundle(as_of=as_of, candidate=candidate)
    if out.is_symlink() or (out.exists() and
                             (not out.is_dir() or any(out.iterdir()))):
        raise ValueError("M38_CONTROL_CENTER_FRESH_OUTPUT_DIRECTORY_REQUIRED")
    impact = bundle["source_impact"]
    quarantine = bundle["claim_quarantine"]
    html = m38.render_html(quarantine)
    html = html.replace(
        "<h1>Research source quarantine</h1>",
        "<h1>Research Lab Control Center — source-revision scenario</h1>"
        "<p>Candidate-scoped research only. Historical raw archives are NOT "
        "exported in this bundle. Unaffected prior M35 source observations "
        "retain their caveats. No real recovery, original publisher replay, "
        "customer consent or publication approval has been established.</p>",
        1,
    )
    if "Research Lab Control Center — source-revision scenario" not in html:
        raise ValueError("M38_CONTROL_CENTER_HTML_SCOPE_MISSING")
    outputs = {
        "phase4_control.json": json.dumps(bundle, sort_keys=True, indent=2) + "\n",
        "index.html": html,
        "source_change_impact.json": json.dumps(impact, sort_keys=True, indent=2) + "\n",
        "source_change_impact.html": m37.render_html(impact),
        "claim_quarantine.json": json.dumps(quarantine, sort_keys=True, indent=2) + "\n",
        "claim_quarantine.html": m38.render_html(quarantine),
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (out / name).write_text(content, encoding="utf-8")
    return bundle
