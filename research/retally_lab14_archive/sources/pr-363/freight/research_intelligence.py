"""RETALLY Research Intelligence Workbench: bounded, offline, read-only evidence review.

This is a *workbench inside existing Lab 14*, not a 15th laboratory.
It never fetches URLs, acts on a customer/carrier, or treats marketing copy as
independently verified. Phase-3 vendor research is imported as attributed
secondary summaries rather than misrepresented as newly viewed source pages.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


LANES = (
    "market", "competitive", "opposition", "buyers",
    "carrier_regulatory", "technology", "economics", "strategy",
)
SOURCE_TYPES = {
    "VENDOR_CLAIM_SNAPSHOT", "INTERNAL_RESEARCH_SNAPSHOT",
    "PUBLIC_PRIMARY", "INDEPENDENT_REPORT",
}
CLASSIFICATIONS = {
    "VENDOR_CLAIM", "INTERNAL_GAP", "PUBLIC_REPORT", "HYPOTHESIS",
}
STANCES = {"SUPPORT", "CHALLENGE"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,96}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ROOT = Path(__file__).parent
CLAIM_BOUNDARY = (
    "Research-only, offline source summaries. Source existence and content hashes "
    "do not prove the assertions, available services, security compliance, pricing, "
    "customer outcomes, or market share. No autonomous browser or source refresh."
)
QUESTIONS = {
    "market": (
        "Which U.S. LTL verticals have demonstrably high invoice complexity and unmet second-look needs?",
        "What independently verifiable sample underpins any serviceable-market estimate?",
    ),
    "competitive": (
        "Which direct recovery specialists compete with RETALLY on contingency terms?",
        "Which product capabilities survive independent demonstrations rather than vendor assertions?",
    ),
    "opposition": (
        "Why would a skeptical CFO decline RETALLY's unproven customer-recovery offer?",
        "Which internal product advantages would fail a blind, customer-controlled test?",
    ),
    "buyers": (
        "Who legally and operationally authorizes a shipper's third-party audit and dispute filing?",
        "What procurement, insurance, confidentiality and data-security evidence do buyers demand?",
    ),
    "carrier_regulatory": (
        "Which versioned tariff and contract governs each historical shipment date?",
        "Which claim response and litigation rules actually apply by carrier, claim and agreement?",
    ),
    "technology": (
        "Which public implementations genuinely demonstrate EDI 210, PDF parsing and reproducible rating?",
        "Can a competitor's public code lawfully be evaluated without assuming production deployment?",
    ),
    "economics": (
        "What share of validated claims becomes customer-realized cash or usable credit?",
        "At what investigation size and labor cost does a contingency claim become unprofitable?",
    ),
    "strategy": (
        "What is the fastest independently testable path to a credible first-customer pilot?",
        "Which changes create verifiable buyer trust versus merely a larger feature list?",
    ),
}
RESEARCH_TACTICS = {
    "market": "Source national freight statistics, segment-specific invoices, and independent sampling designs.",
    "competitive": "Recheck exact first-party claims and prices; triangulate with third-party evaluations.",
    "opposition": "Require a named falsification test, defend against RETALLY confirmation bias, and preserve objections.",
    "buyers": "Collect consented buyer interviews and public RFP requirements without storing personal data.",
    "carrier_regulatory": "Compare governing authority effective dates; have counsel review legal interpretations.",
    "technology": "Inspect permitted public code, license, tests, CI and real execution evidence.",
    "economics": "Measure realized dollars, reversals, analyst labor, attribution and collection chronology.",
    "strategy": "Prioritize a small permissioned and independently adjudicated real pilot.",
}


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def canonical_digest(value: object) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def iso(value: object, label: str) -> date:
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError(f"{label}: ISO YYYY-MM-DD required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid date") from exc


def _source_url(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        p = urlsplit(value)
    except ValueError:
        return False
    return (p.scheme == "https" and bool(p.hostname) and
            not p.username and not p.password and
            not any(c.isspace() for c in value))


def _ident(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def validate_registry(registry: dict, *, as_of: date) -> list[str]:
    """Validate syntax, provenance and internal relations, NOT external truth."""
    errors: list[str] = []
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        return ["research schema_version must be 1"]
    if registry.get("scope") != "PUBLIC_RESEARCH_ONLY":
        errors.append("scope must be PUBLIC_RESEARCH_ONLY")
    try:
        created = iso(registry.get("created_at"), "created_at")
        if created > as_of:
            errors.append("registry created in the future")
    except ValueError as exc:
        errors.append(str(exc))

    sources = registry.get("sources")
    claims = registry.get("claims")
    if not isinstance(sources, list) or not sources:
        return errors + ["nonempty sources list required"]
    if not isinstance(claims, list) or not claims:
        return errors + ["nonempty claims list required"]
    source_types = {}
    source_ids = set()
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            errors.append(f"source {i}: object required")
            continue
        sid = s.get("id")
        if not _ident(sid) or sid in source_ids:
            errors.append(f"source {i}: invalid or duplicate id")
            continue
        source_ids.add(sid)
        typ = s.get("type")
        source_types[sid] = typ
        if typ not in SOURCE_TYPES:
            errors.append(f"{sid}: invalid source type")
        if not _source_url(s.get("url")):
            errors.append(f"{sid}: HTTPS URL without credentials required")
        if not isinstance(s.get("publisher"), str) or not s["publisher"].strip():
            errors.append(f"{sid}: publisher required")
        excerpt = s.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip() or len(excerpt) > 3000:
            errors.append(f"{sid}: bounded source summary required")
        elif s.get("excerpt_sha256") != digest(excerpt):
            errors.append(f"{sid}: source summary hash mismatch")
        try:
            captured = iso(s.get("captured_at"), f"{sid}.captured_at")
            expiry = iso(s.get("valid_until"), f"{sid}.valid_until")
            if captured > as_of:
                errors.append(f"{sid}: future source capture")
            if expiry < captured:
                errors.append(f"{sid}: expiry precedes capture")
            if s.get("published_at") is not None:
                published = iso(s["published_at"], f"{sid}.published_at")
                if published > captured:
                    errors.append(f"{sid}: published after source capture")
        except ValueError as exc:
            errors.append(str(exc))
        if typ == "VENDOR_CLAIM_SNAPSHOT" and s.get("page_directly_reverified") is not False:
            errors.append(f"{sid}: imported vendor summary cannot claim webpage reverification")

    claim_ids = set()
    for i, c in enumerate(claims):
        if not isinstance(c, dict):
            errors.append(f"claim {i}: object required")
            continue
        cid = c.get("id")
        if not _ident(cid) or cid in claim_ids:
            errors.append(f"claim {i}: invalid or duplicate id")
            continue
        claim_ids.add(cid)
        if c.get("lane") not in LANES:
            errors.append(f"{cid}: unknown research lane")
        if c.get("classification") not in CLASSIFICATIONS:
            errors.append(f"{cid}: unsupported classification; never assert VERIFIED")
        if c.get("stance") not in STANCES:
            errors.append(f"{cid}: stance must be SUPPORT or CHALLENGE")
        for key in ("issue_key", "subject", "statement", "next_test"):
            if not isinstance(c.get(key), str) or not c[key].strip():
                errors.append(f"{cid}: {key} required")
        if type(c.get("importance")) is not int or not 1 <= c["importance"] <= 5:
            errors.append(f"{cid}: importance must be integer 1..5")
        refs = c.get("source_ids")
        if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)):
            errors.append(f"{cid}: at least one unique source required")
            continue
        if any(r not in source_ids for r in refs):
            errors.append(f"{cid}: unknown source reference")
        used_types = {source_types.get(r) for r in refs}
        classification = c.get("classification")
        if classification == "VENDOR_CLAIM" and used_types != {"VENDOR_CLAIM_SNAPSHOT"}:
            errors.append(f"{cid}: vendor source cannot be laundered into another class")
        if classification == "INTERNAL_GAP" and used_types != {"INTERNAL_RESEARCH_SNAPSHOT"}:
            errors.append(f"{cid}: internal gap requires internal evidence")
        if classification == "PUBLIC_REPORT" and not used_types <= {"PUBLIC_PRIMARY", "INDEPENDENT_REPORT"}:
            errors.append(f"{cid}: public report requires independently captured public-source excerpt")
        if classification == "HYPOTHESIS":
            errors.append(f"{cid}: hypotheses belong in the explicit open-question queue")
    return errors


def compile_brief(registry: dict, *, as_of: date) -> dict:
    errors = validate_registry(registry, as_of=as_of)
    if errors:
        raise ValueError("INVALID_RESEARCH_REGISTRY: " + "; ".join(errors))
    sources = {s["id"]: s for s in registry["sources"]}
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in registry["claims"]:
        groups[c["issue_key"]].append(c)
    contested = {
        key for key, rows in groups.items()
        if len({r["stance"] for r in rows}) > 1
    }
    findings = []
    counts = Counter()
    for c in registry["claims"]:
        s = [sources[sid] for sid in c["source_ids"]]
        stale = any(iso(x["valid_until"], "valid_until") < as_of for x in s)
        if stale:
            status = "STALE_SOURCE_HOLD"
        elif c["classification"] == "VENDOR_CLAIM":
            status = "VENDOR_CLAIM_UNVERIFIED"
        elif c["classification"] == "INTERNAL_GAP":
            status = "INTERNAL_RESEARCH_NOT_INDEPENDENTLY_TESTED"
        else:
            status = "PUBLIC_SOURCE_NOT_FACT_CHECKED"
        if c["issue_key"] in contested:
            status = "CONTESTED_REQUIRES_REVIEW" if not stale else "STALE_AND_CONTESTED_HOLD"
        counts[status] += 1
        findings.append({
            "id": c["id"], "lane": c["lane"], "subject": c["subject"],
            "issue_key": c["issue_key"], "stance": c["stance"],
            "statement": c["statement"], "classification": c["classification"],
            "evidence_status": status, "importance": c["importance"],
            "source_ids": list(c["source_ids"]),
            "source_urls": [x["url"] for x in s],
            "earliest_valid_until": min(x["valid_until"] for x in s),
            "next_test": c["next_test"],
            "can_publish_as_verified": False,
            "customer_or_financial_authority": False,
        })
    findings.sort(key=lambda x: (-x["importance"],
                                  x["evidence_status"] not in {"CONTESTED_REQUIRES_REVIEW", "STALE_AND_CONTESTED_HOLD"},
                                  x["id"]))
    lane_summary = []
    for lane in LANES:
        in_lane = [x for x in findings if x["lane"] == lane]
        lane_summary.append({
            "lane": lane,
            "sourced_observations": len(in_lane),
            "state": "RESEARCH_QUEUE_ONLY" if not in_lane else
                     "SOURCE_FRESHNESS_HOLD" if any("STALE" in x["evidence_status"] for x in in_lane) else
                     "UNVERIFIED_RESEARCH_PRESENT",
            "questions": list(QUESTIONS[lane]),
            "collection_method": RESEARCH_TACTICS[lane],
        })
    brief = {
        "schema_version": 1,
        "status": "RESEARCH_ONLY_NO_AUTONOMOUS_FETCH",
        "as_of": as_of.isoformat(),
        "source_register_count": len(sources),
        "claim_count": len(findings),
        "evidence_status_counts": dict(sorted(counts.items())),
        "contested_issues": sorted(contested),
        "opposition_findings": sum(x["lane"] == "opposition" for x in findings),
        "no_independent_truth_certification": True,
        "customer_claims_or_payment_execution": False,
        "sources": [{k: s[k] for k in ("id", "publisher", "type", "url", "captured_at", "valid_until", "excerpt_sha256")}
                    for s in registry["sources"]],
        "lanes": lane_summary,
        "prioritized_findings": findings,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_steps": [
            "Verify original vendor webpages and effective plan scope with capture timestamps.",
            "Find independent corroboration or counterexamples before elevating any public claim.",
            "Run a customer-permissioned blinded pilot before making accuracy or recovery claims.",
        ],
    }
    brief["receipt_sha256"] = canonical_digest(brief)
    return brief


def seed_from_phase3(*, as_of: date, evidence: dict, matrix: dict) -> dict:
    """Reuse original 2026-10-07 competitor registry without claiming a fresh fetch."""
    from freight.competitive_matrix import validate_matrix
    if validate_matrix(matrix):
        raise ValueError("INVALID_PHASE3_MATRIX")
    from freight.competitive_matrix import validate_competitor_evidence
    # Use the original source-capture date for validation, not a later run date.
    collected = iso(evidence.get("collected_at"), "collected_at")
    issues = validate_competitor_evidence(evidence, as_of=collected)
    if issues:
        raise ValueError("INVALID_PHASE3_EVIDENCE: " + "; ".join(issues))
    sources = []
    claims = []
    for name, vendor in sorted(evidence["competitors"].items()):
        token = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        for i, item in enumerate(vendor["sources"], 1):
            sid = f"phase3.{token}.{i}"
            summary = item["claim_scope"]
            sources.append({
                "id": sid, "type": "VENDOR_CLAIM_SNAPSHOT",
                "url": item["url"], "publisher": name, "captured_at": evidence["collected_at"],
                "valid_until": evidence["valid_until"], "excerpt": summary,
                "excerpt_sha256": digest(summary), "page_directly_reverified": False,
            })
            claims.append({
                "id": f"claim.{token}.{i}", "lane": "competitive",
                "issue_key": f"provider:{token}:scope:{i}", "subject": name,
                "stance": "SUPPORT", "statement": summary,
                "classification": "VENDOR_CLAIM", "source_ids": [sid],
                "importance": 3,
                "next_test": "Review the original vendor page; independently test actual contract, plan, geography and deployment.",
            })
    gap = matrix["vendors"]["RecoveryOS"]["scores"]
    important = ("real_world_accuracy", "ingestion_extraction",
                 "enterprise_integrations", "security_assurance",
                 "payment_execution")
    gap_info = []
    for dimension in important:
        ours = gap[dimension]["score"]
        leaders = max(v["scores"][dimension]["score"]
                      for v in matrix["vendors"].values())
        gap_info.append((dimension, ours, leaders))
    synopsis = json.dumps(gap_info, separators=(",", ":"))
    sid = "phase3.internal.matrix"
    sources.append({
        "id": sid, "type": "INTERNAL_RESEARCH_SNAPSHOT",
        "url": "https://github.com/P00NSMASHER/github-value-hunt-ledger/blob/research/retally-phase4-experiment-director-20261008/freight/PHASE3_COMPETITIVE_MATRIX_2026-10-07.json",
        "publisher": "RETALLY internal Phase 3 scoring rubric",
        "captured_at": evidence["collected_at"],
        "valid_until": evidence["valid_until"],
        "excerpt": synopsis, "excerpt_sha256": digest(synopsis),
    })
    for dimension, ours, leader in gap_info:
        claims.append({
            "id": f"gap.{dimension}", "lane": "opposition",
            "issue_key": f"retally_gap:{dimension}", "subject": "RETALLY RecoveryOS",
            "stance": "CHALLENGE",
            "statement": f"Internal rubric {dimension}: RETALLY {ours}/5 versus highest internal competitor score {leader}/5; these scores are not independent market measurements.",
            "classification": "INTERNAL_GAP", "source_ids": [sid],
            "importance": 5 if leader - ours >= 3 else 4,
            "next_test": "Design a buyer-controlled blind acceptance test with independent evaluation and actual deployment evidence.",
        })
    return {
        "schema_version": 1, "scope": "PUBLIC_RESEARCH_ONLY",
        "created_at": as_of.isoformat(),
        "sources": sources, "claims": claims,
    }


def phase3_brief(*, as_of: date, root: Path = ROOT) -> dict:
    evidence = json.loads((root / "PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json").read_text(encoding="utf-8"))
    matrix = json.loads((root / "PHASE3_COMPETITIVE_MATRIX_2026-10-07.json").read_text(encoding="utf-8"))
    return compile_brief(seed_from_phase3(as_of=as_of, evidence=evidence, matrix=matrix), as_of=as_of)


def render_html(brief: dict) -> str:
    """Standalone offline operator view that also links from existing Phase 4."""
    def e(value: object) -> str:
        return escape(str(value), quote=True)
    rows = []
    for lane in brief["lanes"]:
        rows.append(f'<section class="tile"><div class="kicker">{e(lane["lane"])}</div>'
                    f'<strong>{e(lane["state"].replace("_", " "))}</strong>'
                    f'<small>{lane["sourced_observations"]} sourced observation(s)</small>'
                    f'<p>{e(lane["questions"][0])}</p></section>')
    observations = []
    for item in brief["prioritized_findings"][:14]:
        url = item["source_urls"][0]
        observations.append(f'<article class="finding"><div class="meta">{e(item["lane"])} · '
                            f'{e(item["evidence_status"])}</div><h3>{e(item["subject"])}</h3>'
                            f'<p>{e(item["statement"])}</p><p><b>Test:</b> {e(item["next_test"])}</p>'
                            f'<a href="{e(url)}" rel="noopener noreferrer">Source/context ↗</a></article>')
    warnings = ("All source excerpts imported from the 2026-10-07 repository snapshot are analyst "
                "summaries, not independently re-read vendor webpages. Nothing is verified "
                "for public advertising or real carrier/customer action.")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RETALLY | Research Intelligence</title>
<style>
:root{{--bg:#f6f8f6;--ink:#182e25;--muted:#687c72;--edge:#dfeae1;--green:#07814c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,sans-serif}}
main{{max-width:1130px;margin:auto;padding:28px 20px 60px}}a{{color:var(--green)}}
header{{padding:23px 0 28px;border-bottom:1px solid var(--edge)}}.brand{{font-weight:900;letter-spacing:.13em;font-size:21px}}
.kicker,.meta{{color:var(--green);font-weight:700;font-size:11px;letter-spacing:.1em;text-transform:uppercase}}
h1{{font-size:clamp(30px,5vw,52px);letter-spacing:-.05em;line-height:1.04;margin:15px 0}}h2{{font-size:22px;margin-top:33px}}
.lead{{max-width:740px;color:var(--muted)}}.stats{{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}}
.stat{{background:white;border:1px solid var(--edge);padding:16px 20px;border-radius:14px;min-width:130px;flex:1}}
.stat b{{display:block;font-size:25px}}.stat small,.tile small{{display:block;color:var(--muted);font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.tile,.finding{{background:#fff;border:1px solid var(--edge);border-radius:16px;padding:18px;box-shadow:0 6px 15px #21433108}}
.tile strong{{display:block;margin:9px 0;font-size:12px;letter-spacing:.02em}}.tile p,.finding p{{color:var(--muted);font-size:13px}}
.findings{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.finding h3{{margin:7px 0 2px}}
.notice{{background:#edf4ee;border-left:4px solid var(--green);border-radius:8px;padding:14px 17px;margin-top:24px}}
footer{{margin-top:34px;color:var(--muted);font-size:12px;word-break:break-all}}
@media(max-width:850px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:560px){{.grid,.findings{{grid-template-columns:1fr}}}}
</style></head><body><main><header><div class="brand">RETALLY <span style="color:#07814c">●</span></div>
<div class="kicker">Lab 14 · Market & Oppositional Intelligence · Offline</div>
<h1>Find the evidence.<br>Challenge the assumptions.</h1>
<p class="lead">{e(brief["claim_boundary"])}</p>
<div class="stats"><div class="stat"><small>Research lanes</small><b>8</b></div>
<div class="stat"><small>Imported source records</small><b>{brief["source_register_count"]}</b></div>
<div class="stat"><small>Source-linked observations</small><b>{brief["claim_count"]}</b></div>
<div class="stat"><small>Internal counterarguments</small><b>{brief["opposition_findings"]}</b></div></div></header>
<div class="notice">{e(warnings)}<br>Research cutoff: {e(brief["as_of"])}. No automated searches performed.</div>
<h2>Eight coordinated research disciplines</h2><div class="grid">{''.join(rows)}</div>
<h2>Highest-priority items to challenge</h2><div class="findings">{''.join(observations)}</div>
<footer>Research receipt SHA-256: {e(brief["receipt_sha256"])} — no production actions, claims, or fee authority.
<a href="index.html">← Phase 4 Lab Control Center</a></footer></main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="RETALLY offline research workbench")
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--registry", type=Path, help="Optional manually curated versioned source registry")
    args = parser.parse_args()
    today = iso(args.as_of_date, "as-of-date")
    if args.registry:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        brief = compile_brief(registry, as_of=today)
    else:
        brief = phase3_brief(as_of=today)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "research_intelligence.json").write_text(json.dumps(brief, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "research.html").write_text(render_html(brief), encoding="utf-8")
    print(json.dumps({"status": brief["status"], "lanes": len(brief["lanes"]),
                      "sources": brief["source_register_count"], "claims": brief["claim_count"],
                      "receipt": brief["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
