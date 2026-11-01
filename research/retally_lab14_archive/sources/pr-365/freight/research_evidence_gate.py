"""Source-anchor fidelity checks and a bounded decision register for RETALLY Lab 14.

This is an offline analyst review tool. It NEVER verifies external truth, changes
claim states to VERIFIED, autonomously fetches websites, or gives authority for
commercial, legal, customer or financial actions.

Quote snippets represent short source text manually captured from public
web views. The integrity hash checks the stored snippet, not the publisher.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from hashlib import sha256
from html import escape
import argparse
import json
from pathlib import Path
import re

from freight.research_intelligence import compile_brief, iso
from freight.research_public_campaign import campaign_registry


ROOT = Path(__file__).resolve().parent
VALID_METHODS = {"PUBLIC_WEB_VIEW", "SEARCH_RESULT_ONLY"}
VALID_SCOPE = {"DIRECT_SCOPE", "LIMITED_CONTEXT", "HISTORICAL_TEXT", "UNVERIFIED_SNIPPET"}
HEX64 = re.compile(r"^[a-f0-9]{64}$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,96}$")
CORE_BOUNDARY = (
    "Quote and date integrity are checks on stored source snippets only. "
    "No independent publisher authentication, independent customer outcomes, "
    "live-carrier authority, or verified legal conclusion is established."
)


def digest_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def canon_hash(value: object) -> str:
    return digest_bytes(json.dumps(value, sort_keys=True,
                                   separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def validate_anchor_book(book: dict, registry: dict, *, as_of: date) -> list[str]:
    errors: list[str] = []
    if not isinstance(book, dict) or book.get("schema_version") != 1:
        return ["anchor schema_version must be 1"]
    if book.get("scope") != "SHORT_PUBLIC_SOURCE_EXCERPTS_RESEARCH_ONLY":
        errors.append("unauthorized anchor scope")
    try:
        recorded = iso(book.get("recorded_at"), "recorded_at")
        if recorded > as_of:
            errors.append("anchor book recorded in future")
    except ValueError as exc:
        errors.append(str(exc))

    sources = {s["id"]: s for s in registry.get("sources", [])}
    claims = {c["id"]: c for c in registry.get("claims", [])}
    anchors = book.get("anchors")
    if not isinstance(anchors, list) or not anchors or len(anchors) > 32:
        return errors + ["anchors must be a nonempty bounded list"]
    ids = set()
    for row_num, row in enumerate(anchors):
        if not isinstance(row, dict):
            errors.append(f"anchor {row_num}: record must be object")
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not IDENT.fullmatch(ident) or ident in ids:
            errors.append(f"anchor {row_num}: invalid or duplicate id")
            continue
        ids.add(ident)
        source = sources.get(row.get("source_id"))
        if source is None:
            errors.append(f"{ident}: source ID does not exist")
            continue
        if row.get("url") != source.get("url"):
            errors.append(f"{ident}: source URL mismatched")
        method = row.get("method")
        if method not in VALID_METHODS:
            errors.append(f"{ident}: unknown source review method")
        strength = row.get("support_scope")
        if strength not in VALID_SCOPE:
            errors.append(f"{ident}: unknown support_scope")
        if method == "SEARCH_RESULT_ONLY" and strength == "DIRECT_SCOPE":
            errors.append(f"{ident}: search snippet cannot be direct-source proof")
        excerpt = row.get("quote")
        if not isinstance(excerpt, str) or not 6 <= len(excerpt) <= 320:
            errors.append(f"{ident}: bounded quote required")
            continue
        if not isinstance(row.get("quote_sha256"), str) or not HEX64.fullmatch(row["quote_sha256"]):
            errors.append(f"{ident}: SHA-256 format invalid")
        elif digest_bytes(excerpt.encode("utf-8")) != row["quote_sha256"]:
            errors.append(f"{ident}: source quote checksum mismatch")
        if len(excerpt.split()) > 25:
            errors.append(f"{ident}: excerpt exceeds 25-word quotation budget")
        if any(ord(c) < 32 and c not in "\t\n" for c in excerpt):
            errors.append(f"{ident}: control characters in quote")
        try:
            observed = iso(row.get("observed_at"), f"{ident}.observed_at")
            if observed > as_of:
                errors.append(f"{ident}: source observed in future")
            captured = iso(source.get("captured_at"), f"{ident}.captured_at")
            if observed < captured:
                errors.append(f"{ident}: observation precedes existing source snapshot")
        except ValueError as exc:
            errors.append(str(exc))
        if not isinstance(row.get("limitation"), str) or len(row["limitation"].strip()) < 12:
            errors.append(f"{ident}: explicit limitation required")
        claim_ids = row.get("claim_ids")
        if (not isinstance(claim_ids, list) or not claim_ids or
                len(claim_ids) != len(set(claim_ids))):
            errors.append(f"{ident}: at least one unique claim required")
            continue
        for claim_id in claim_ids:
            claim = claims.get(claim_id)
            if claim is None:
                errors.append(f"{ident}: nonexistent claim ID {claim_id}")
            elif source["id"] not in claim.get("source_ids", []):
                errors.append(f"{ident}: unrelated claim {claim_id} lacks source binding")
        marker = row.get("literal_markers", [])
        if not isinstance(marker, list) or len(marker) > 6:
            errors.append(f"{ident}: malformed literal markers")
        else:
            for needle in marker:
                if (not isinstance(needle, str) or not needle or
                        needle not in excerpt):
                    errors.append(f"{ident}: claimed literal absent from quote")
        if row.get("verified_external_fact") is not False:
            errors.append(f"{ident}: never promote manual quote into independently verified fact")
        if row.get("customer_action_authorized") is not False:
            errors.append(f"{ident}: quoted page cannot authorize customer action")
        if row.get("effective_on") is not None:
            try:
                effective = iso(row["effective_on"], f"{ident}.effective_on")
                if row.get("represents_current_rule") is True and effective > as_of:
                    errors.append(f"{ident}: future rule misrepresented as currently effective")
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def review_evidence(registry: dict, book: dict, *, as_of: date) -> dict:
    """Rank review quality, never claim accuracy or external validation."""
    # The campaign itself already validates its provenance and dates.
    compile_brief(registry, as_of=as_of)
    errors = validate_anchor_book(book, registry, as_of=as_of)
    if errors:
        raise ValueError("INVALID_SOURCE_ANCHORS: " + "; ".join(errors))
    anchor_by_claim: dict[str, list[dict]] = {}
    for anchor in book["anchors"]:
        for cid in anchor["claim_ids"]:
            anchor_by_claim.setdefault(cid, []).append(anchor)
    sources = {s["id"]: s for s in registry["sources"]}
    assessments = []
    for claim in registry["claims"]:
        anchors = anchor_by_claim.get(claim["id"], [])
        anchors_source = [a for a in anchors if a["method"] == "PUBLIC_WEB_VIEW"]
        future = [a for a in anchors if a.get("effective_on") is not None
                  and iso(a["effective_on"], "effective_on") > as_of]
        stale = any(iso(sources[sid]["valid_until"], "valid_until") < as_of
                    for sid in claim["source_ids"])
        if stale:
            state = "EXPIRED_SOURCE_HOLD"
        elif future:
            state = "FUTURE_EFFECTIVE_RULE_HOLD"
        elif not anchors:
            state = "NO_ORIGINAL_SOURCE_ANCHOR"
        elif not anchors_source:
            state = "SEARCH_SNIPPET_ONLY_RECHECK"
        elif any(a["support_scope"] != "DIRECT_SCOPE" for a in anchors_source):
            state = "CONTEXT_OR_HISTORICAL_REVIEW"
        else:
            state = "ATTRIBUTED_TEXT_PRESENT_INDEPENDENT_REVIEW_PENDING"
        assessments.append({
            "claim_id": claim["id"],
            "lane": claim["lane"],
            "classification": claim["classification"],
            "review_status": state,
            "source_quote_ids": [a["id"] for a in anchors],
            "vendor_or_internal_claim_verified": False,
            "independent_real_world_proof": False,
            "public_marketing_permitted": False,
            "next_test": claim["next_test"],
        })
    count = Counter(item["review_status"] for item in assessments)
    report = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": "RESEARCH_ONLY_NO_VERIFICATION_PROMOTION",
        "source_count": len(registry["sources"]),
        "claim_count": len(registry["claims"]),
        "anchored_claim_count": sum(bool(a["source_quote_ids"]) for a in assessments),
        "anchor_count": len(book["anchors"]),
        "status_counts": dict(sorted(count.items())),
        "assessments": assessments,
        "quote_metadata": [
            {
                "id": a["id"], "source_id": a["source_id"],
                "url": a["url"], "observed_at": a["observed_at"],
                "method": a["method"], "support_scope": a["support_scope"],
                "effective_on": a.get("effective_on"),
                "quote_sha256": a["quote_sha256"],
                "limitation": a["limitation"],
            } for a in book["anchors"]
        ],
        "claim_boundary": CORE_BOUNDARY,
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


# Curated, explicit decisions rather than a spurious statistical forecast.
# 1..5 ordinal scores are internal prioritization assumptions, NOT observed ROI.
_DECISIONS = (
    ("M4-01", "Secure real-customer pilot proof",
     "External buyer evidence and independent blind audit accuracy are not yet established.",
     ("gap.real_world_accuracy", "gap.security_assurance", "campaign.competitor.loop"),
     5, 5, 4, 4, "Obtain buyer-approved scope and restricted intake, blind independent adjudication, and measured reviewer effort."),
    ("M4-02", "Carrier tariff and NMFC effective-date control",
     "A future classification supplement can cause false historical rerating if applied before effective date.",
     ("campaign.carrier.timeline", "campaign.carrier.bulletin", "campaign.carrier.contract"),
     5, 4, 2, 5, "Add boundary fixtures on the actual shipment date, applicable tariff and official NMFC effective-date record."),
    ("M4-03", "Competitive fee and buyer-understanding experiment",
     "A publicly posted 20% rival fee makes RETALLY's negotiated-rate message a testable clarity risk.",
     ("campaign.competitor.price", "campaign.opposition.own", "campaign.opposition.comparator"),
     4, 5, 2, 5, "Run a consented controlled buyer comprehension exercise; compare total fee definitions and exclusions."),
    ("M4-04", "Source-grounded second-look market segmentation",
     "Freight shipment value and freight-audit service revenue are not interchangeable.",
     ("campaign.market.cfs", "campaign.market.faf", "campaign.buyer.coverage"),
     4, 5, 3, 4, "Use legally acquired invoice samples and decision-maker interviews to estimate reachable profitable accounts."),
    ("M4-05", "Independent vendor capability replication",
     "Vendor claims and internal competitor scores are not blind comparative results.",
     ("campaign.competitor.loop", "gap.ingestion_extraction", "gap.enterprise_integrations"),
     4, 4, 4, 4, "Agree a blind set of common invoice/authority fixtures and independently adjudicate outputs."),
    ("M4-06", "Measure actual realized recovery economics",
     "Investor payment processing volumes and isolated headline fees do not establish RETALLY cash profitability.",
     ("campaign.economics.sec", "campaign.economics.offer", "campaign.strategy.market"),
     5, 5, 3, 5, "Pilot claim-level labor, exclusions, credit/reversal chronology and independently reconciled realized cash."),
)


def decision_register(registry: dict, verification: dict) -> dict:
    claims = {x["id"]: x for x in registry["claims"]}
    checked = {x["claim_id"]: x for x in verification["assessments"]}
    decisions = []
    for ident, name, hypothesis, ids, impact, uncertainty, effort, testability, test in _DECISIONS:
        if not set(ids) <= set(claims):
            raise ValueError(f"{ident}: missing required evidence dependency")
        unresolved = [x for x in ids if checked[x]["review_status"] !=
                      "ATTRIBUTED_TEXT_PRESENT_INDEPENDENT_REVIEW_PENDING"]
        priority = 3 * impact + 2 * uncertainty + testability - effort
        decisions.append({
            "id": ident,
            "subject": name,
            "adversarial_hypothesis": hypothesis,
            "claim_ids": list(ids),
            "research_blocked_claim_ids": unresolved,
            "priority_score_ordinal_not_forecast": priority,
            "impact_ordinal": impact,
            "uncertainty_ordinal": uncertainty,
            "effort_ordinal": effort,
            "testability_ordinal": testability,
            "recommended_test": test,
            "execution_permission": "INTERNAL_DESK_RESEARCH_ONLY",
            "external_actions_allowed": False,
            "next_action": "EVIDENCE_VERIFICATION" if unresolved else "HUMAN_DECISION_AND_TEST_DESIGN",
        })
    decisions.sort(key=lambda r: (-r["priority_score_ordinal_not_forecast"], r["id"]))
    result = {
        "schema_version": 1,
        "scope": "INTERNAL_OPPOSITION_AND_RESEARCH_ONLY",
        "evidence_receipt_sha256": verification["receipt_sha256"],
        "priority_math": "3*impact + 2*uncertainty + testability - effort; ordinal internal values, not ROI",
        "decisions": decisions,
        "all_require_human_review": True,
        "zero_automated_corporate_actions": True,
        "actual_customer_results_inferred": False,
        "limitations": CORE_BOUNDARY,
    }
    result["receipt_sha256"] = canon_hash(result)
    return result


def run_mission(*, as_of: date, root: Path = ROOT) -> tuple[dict, dict]:
    registry = campaign_registry(as_of=as_of, root=root)
    anchors = json.loads((root / "research/SOURCE_ANCHORS_20261010.json").read_text(encoding="utf-8"))
    proof = review_evidence(registry, anchors, as_of=as_of)
    decisions = decision_register(registry, proof)
    return proof, decisions


def render_html(proof: dict, decisions: dict) -> str:
    """Static internal workbench; no production/public results."""
    rows = []
    for d in decisions["decisions"]:
        refs = ", ".join(d["claim_ids"])
        rows.append(
            '<article class="item"><div class="meta">'
            + escape(d["id"]) + ' · priority ' + str(d["priority_score_ordinal_not_forecast"])
            + '</div><h3>' + escape(d["subject"]) + '</h3><p>'
            + escape(d["adversarial_hypothesis"]) + '</p><p><b>Falsification test:</b> '
            + escape(d["recommended_test"]) + '</p><small>'
            + escape(refs) + '</small><small>Gate: '
            + escape(d["next_action"]) + '</small></article>'
        )
    count = "".join(
        '<tr><th>' + escape(k) + '</th><td>' + str(v) + '</td></tr>'
        for k, v in proof["status_counts"].items()
    )
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RETALLY | Evidence & Opposition</title><style>
*{box-sizing:border-box}body{background:#f7faf8;color:#173329;margin:0;font:15px/1.55 system-ui,-apple-system,sans-serif}
main{margin:auto;max-width:1120px;padding:36px 20px 66px}
header{border-bottom:1px solid #d7e6df;margin-bottom:26px;padding-bottom:24px}
.brand{font-weight:850;letter-spacing:.13em}.brand em{color:#0c8f55;font-style:normal}
h1{font-size:clamp(32px,4.8vw,55px);letter-spacing:-.05em;line-height:1.08;margin:18px 0}
h2{font-size:23px;margin-top:35px}.muted,p,small{color:#63786d}a{color:#067d4a}
.top{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}
.stat,.item,.panel{background:white;border:1px solid #d7e6df;border-radius:15px;padding:19px}
.stat strong{display:block;font-size:30px;color:#173329}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.item h3{margin:8px 0 6px}.item small{display:block;font-size:11px;word-break:break-word}
.meta{font-size:11px;color:#07814c;text-transform:uppercase;font-weight:800;letter-spacing:.08em}
.notice{border-left:4px solid #07945a;padding:13px 16px;background:#eaf4ee;margin-top:20px}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #d7e6df}
@media(max-width:750px){.top,.grid{grid-template-columns:1fr}}
</style></head><body><main><header><div class="brand">RETA<em>LL</em>Y</div>
<div class="meta">Lab 14 · Source fidelity and opposition war room</div>
<h1>What do we know?<br>What could prove us wrong?</h1>
<p>Research-only findings, not independent verification or customer authorization.</p>
<div class="top"><div class="stat"><small>Source snippets</small><strong>""" + str(proof["anchor_count"]) + """</strong></div>
<div class="stat"><small>Anchored claims</small><strong>""" + str(proof["anchored_claim_count"]) + """</strong></div>
<div class="stat"><small>Adversarial decisions</small><strong>""" + str(len(decisions["decisions"])) + """</strong></div></div></header>
<div class="notice">""" + escape(proof["claim_boundary"]) + """</div>
<h2>Most important questions to resolve</h2><div class="grid">""" + "".join(rows) + """</div>
<h2>Source-quality review state</h2><section class="panel"><table>""" + count + """</table></section>
<footer><small>Proof SHA-256: """ + escape(proof["receipt_sha256"]) + """</small>
<small>Decisions SHA-256: """ + escape(decisions["receipt_sha256"]) + """</small>
<p><a href="index.html">Back to Phase 4</a> · <a href="research.html">Research Intelligence</a></p>
</footer></main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only, dated evidence fidelity + opposition")
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    as_of = iso(args.as_of_date, "as-of-date")
    proof, decisions = run_mission(as_of=as_of)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"evidence_fidelity.json").write_text(
        json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out/"opposition_decisions.json").write_text(
        json.dumps(decisions, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out/"opposition.html").write_text(
        render_html(proof, decisions), encoding="utf-8")
    print(json.dumps({
        "anchors": proof["anchor_count"], "anchored_claims": proof["anchored_claim_count"],
        "unresolved_claims": proof["claim_count"] - proof["anchored_claim_count"],
        "decisions": len(decisions["decisions"]),
        "receipt_sha256": decisions["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
