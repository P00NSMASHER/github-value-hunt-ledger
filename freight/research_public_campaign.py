"""Dated, attributable first public-source campaign for the existing RETALLY Lab 14.

Source excerpts are carefully bounded *researcher summaries* from publicly
available pages reviewed on 2026-10-10, not archival page bodies or independent
fact-checks. This module makes no HTTP requests; a separate manually triggered
capture utility can collect review candidates. Do not republish these as verified
vendor features, client results, pricing contracts or regulatory advice.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from freight.research_intelligence import (
    compile_brief, digest, seed_from_phase3, validate_registry,
)

ROOT = Path(__file__).resolve().parent
CAMPAIGN_DATE = "2026-10-10"
CAPTURE_METHOD = "HUMAN_REVIEW_OF_PUBLIC_WEB_SOURCE_2026_10_10"
SOURCE_META = {
    "bts.cfs.2022": (
        "PUBLIC_PRIMARY", "2025-06-26", "2027-01-01",
        "BTS said the 2022 Commodity Flow Survey measured about 12.2 billion tons of goods valued at $18.0 trillion among surveyed industries; not freight audit revenue."
    ),
    "bts.faf6.2026": (
        "PUBLIC_PRIMARY", "2026-08-31", "2027-01-01",
        "BTS describes FAF6 as 2022-base-year estimates of U.S. freight weight and value by origin, destination, mode and commodity."
    ),
    "recoveraudit.pricing": (
        "VENDOR_CLAIM_SNAPSHOT", None, "2026-11-10",
        "RecoverAudit publicly offers a 20% share of verified recovered amounts and a free initial ten-invoice pilot; not an independently confirmed contract."
    ),
    "retally.offer": (
        "VENDOR_CLAIM_SNAPSHOT", None, "2026-11-10",
        "RETALLY's public page says its recovery percentage is agreed before engagement; the page does not promise a universal fixed percentage."
    ),
    "nmfta.timeline.2026": (
        "PUBLIC_PRIMARY", "2026-06-09", "2026-12-12",
        "NMFTA lists October 9, 2026 as its disposition bulletin date and December 12, 2026 as the future effective date for Supplement 2026-2."
    ),
    "nmfta.bulletin.2026": (
        "PUBLIC_PRIMARY", "2026-10-09", "2026-12-12",
        "NMFTA describes 2026-2 density reclassification decisions and says the proposed Rule 640 mixed-commodity rewrite did not pass."
    ),
    "uscode.13710": (
        "PUBLIC_PRIMARY", None, "2027-01-10",
        "49 U.S.C. 13710(a)(3)(B) says a shipper must contest an original or subsequent motor-carrier bill within 180 days of receipt to retain that specified contest right."
    ),
    "govinfo.3788": (
        "PUBLIC_PRIMARY", "2018-04-16", "2026-11-10",
        "The 2018 Federal Register published a 49 CFR 378.8 provision calling for disposition of written overcharge claims within 60 days, subject to a written extension; current applicability still needs verification."
    ),
    "estes.tariff": (
        "PUBLIC_PRIMARY", "2026-08-03", "2026-11-10",
        "Estes posts an August 3, 2026 rules-tariff update and notes that specific customer pricing agreements or contracts may provide exceptions."
    ),
    "x12.210": (
        "PUBLIC_PRIMARY", None, "2027-01-10",
        "The X12 organization identifies transaction set 210 as Motor Carrier Freight Details and Invoice, conveying motor-carrier freight charge information."
    ),
    "cass.sec.2026": (
        "PUBLIC_PRIMARY", None, "2027-01-01",
        "A Cass issuer presentation filed with the SEC in 2026 reports $37 billion of freight payment volume and 34 million freight invoices; not second-look contingency revenue."
    ),
    "loop.auditbench": (
        "VENDOR_CLAIM_SNAPSHOT", "2026-09-01", "2026-11-10",
        "Loop's September 2026 vendor benchmark reports 94.8% on its production invoice set and 65% on its challenge set; external replication was not established."
    ),
}

# Source-linked observations only. Claim phrasing is no stronger than the
# original page; actionable inferences reside in next_test, not in a fact field.
CLAIMS = [
    ("campaign.market.cfs", "market", "market:freight-value-vs-audit-revenue",
     "BTS Commodity Flow Survey", "SUPPORT",
     "BTS reported $18.0 trillion of 2022 survey-covered commodity shipments; this is not an estimate of the freight audit market.",
     "PUBLIC_REPORT", ["bts.cfs.2022"], 4,
     "Acquire mode-specific shipper invoice expenditure and independently derive a plausible serviceable market."),
    ("campaign.market.faf", "market", "market:segmentation",
     "BTS Freight Analysis Framework", "SUPPORT",
     "FAF6 supplies origin-destination, mode and commodity dimensions for 2022-base-year national freight estimates.",
     "PUBLIC_REPORT", ["bts.faf6.2026"], 3,
     "Join permitted FAF6 segments to identified buyers without extrapolating freight value into recoverable bills."),
    ("campaign.competitor.price", "competitive", "competitor:recoveraudit:pricing",
     "RecoverAudit", "SUPPORT",
     "RecoverAudit's public pricing page advertises a 20% contingency share and up to ten free pilot invoices.",
     "VENDOR_CLAIM", ["recoveraudit.pricing"], 4,
     "Verify dated offer terms, carrier/mode scope, exclusions and whether a signed agreement matches the webpage."),
    ("campaign.competitor.loop", "competitive", "competitor:loop:benchmark",
     "Loop AuditBench", "SUPPORT",
     "Loop publicly reports distinct 94.8% and 65% freight invoice benchmark results on its own stated test sets.",
     "VENDOR_CLAIM", ["loop.auditbench"], 4,
     "Review methodology, denominator and dataset leakage; independently test RETALLY on blinded permissioned cases."),
    ("campaign.opposition.own", "opposition", "retally:pricing:clarity",
     "RETALLY pricing statement", "SUPPORT",
     "RETALLY says the actual recovery rate is confirmed before engagement, without publishing one universal percentage.",
     "VENDOR_CLAIM", ["retally.offer"], 5,
     "Test whether three buyer personas understand expected fees and scope before signing."),
    ("campaign.opposition.comparator", "opposition", "retally:pricing:clarity",
     "Potential transparency objection", "CHALLENGE",
     "A competitor advertises a visible 20% fee; a buyer could ask RETALLY for equally early pricing clarity, but impact is unmeasured.",
     "VENDOR_CLAIM", ["recoveraudit.pricing"], 5,
     "Conduct consented buyer usability interviews; verify signed rates and compare total effective costs, not headline fees."),
    ("campaign.buyer.coverage", "buyers", "buyer:industry-scope",
     "BTS Commodity Flow Survey", "SUPPORT",
     "CFS covers manufacturing, wholesale, warehouses and selected retail or service establishments; it does not establish demand for a recovery service.",
     "PUBLIC_REPORT", ["bts.cfs.2022"], 4,
     "Identify and interview authorized freight-payable decision-makers with written permission."),
    ("campaign.carrier.timeline", "carrier_regulatory", "carrier:nmfc:future-effective",
     "NMFTA classification calendar", "SUPPORT",
     "Supplement 2026-2 is scheduled to take effect December 12, 2026, later than the October 9 bulletin publication.",
     "PUBLIC_REPORT", ["nmfta.timeline.2026"], 5,
     "Preserve every applicable NMFC effective date and verify subsequent notices before historical rerating."),
    ("campaign.carrier.bulletin", "carrier_regulatory", "carrier:nmfc:mixed-commodity-rule",
     "NMFTA Rule 640 proposal", "SUPPORT",
     "NMFTA says its proposed Rule 640 rewrite did not pass in the 2026-2 disposition process.",
     "PUBLIC_REPORT", ["nmfta.bulletin.2026"], 4,
     "Consult official adopted classification and customer contract to distinguish proposed rules from operative rules."),
    ("campaign.carrier.billcontest", "carrier_regulatory", "carrier:uscode:bill-contest",
     "49 U.S.C. 13710", "SUPPORT",
     "Section 13710(a)(3)(B) specifies a 180-day shipper bill-contest rule for the covered motor-carrier dispute mechanism.",
     "PUBLIC_REPORT", ["uscode.13710"], 5,
     "Have transportation counsel verify scope, claim type, waiver and contractual exceptions before setting client deadlines."),
    ("campaign.carrier.response", "carrier_regulatory", "carrier:claims:response-clock",
     "49 CFR 378.8", "SUPPORT",
     "The 2018 published text of 49 CFR 378.8 describes a 60-day written-claim disposition requirement and a written-extension exception.",
     "PUBLIC_REPORT", ["govinfo.3788"], 5,
     "Distinguish processing deadlines from filing windows, credit realization, contractual exceptions and litigation limitations."),
    ("campaign.carrier.contract", "carrier_regulatory", "carrier:estes:contract-override",
     "Estes public tariff", "SUPPORT",
     "Estes warns that specific customer pricing agreements or contracts can contain exceptions to its published accessorial charges.",
     "PUBLIC_REPORT", ["estes.tariff"], 5,
     "Verify the exact customer's governing rate authority and the shipment-date tariff before flagging any accessorial."),
    ("campaign.technology.edi", "technology", "technology:x12:210",
     "X12 210 specification", "SUPPORT",
     "X12 describes transaction set 210 as motor-carrier freight invoice and charge detail data.",
     "PUBLIC_REPORT", ["x12.210"], 4,
     "Validate the actual 210 version and trading-partner implementation guide against parser fixtures."),
    ("campaign.technology.benchmark", "technology", "technology:real-world-benchmark",
     "Loop vendor benchmark", "SUPPORT",
     "Loop's reported performance differs between its production set and challenge set; neither reported figure independently validates RETALLY.",
     "VENDOR_CLAIM", ["loop.auditbench"], 4,
     "Reproduce an authorized blind comparative set, with separate ordinary and difficult cases and objective adjudication."),
    ("campaign.economics.sec", "economics", "economics:provider-scale",
     "Cass issuer presentation", "SUPPORT",
     "Cass's SEC-hosted issuer presentation reports $37 billion in annual freight payments and 34 million freight invoices.",
     "PUBLIC_REPORT", ["cass.sec.2026"], 4,
     "Do not infer second-look addressable revenue; seek itemized outsourced audit costs and realized recovery evidence."),
    ("campaign.economics.offer", "economics", "economics:contingency-offer",
     "RecoverAudit listed rate", "SUPPORT",
     "RecoverAudit's public 20% pricing claim is one provider's offer, not a distribution of market rates.",
     "VENDOR_CLAIM", ["recoveraudit.pricing"], 4,
     "Build a fee survey with dated signed or independently checked terms, methodology and sample-size limits."),
    ("campaign.strategy.classification", "strategy", "strategy:classification-change-control",
     "NMFTA future classification rules", "SUPPORT",
     "NMFTA's 2026-2 supplement has a future planned effective date, so a dated audit requires the correct rule version.",
     "PUBLIC_REPORT", ["nmfta.timeline.2026"], 5,
     "Add automated versioned-date review fixtures; block classification claims lacking original authority."),
    ("campaign.strategy.market", "strategy", "strategy:segment-first",
     "BTS market segmentation evidence", "SUPPORT",
     "BTS freight datasets provide mode and commodity segmentation but no invoice dispute rates or successful recoveries by buyer.",
     "PUBLIC_REPORT", ["bts.faf6.2026"], 4,
     "Use a small consented customer invoice sample to establish actual eligibility, false positives, and realized recovery.")
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def campaign_registry(*, as_of: date, root: Path = ROOT) -> dict:
    """Produce one combined registry with original Phase 3 provenance preserved."""
    evidence = _load_json(root / "PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json")
    matrix = _load_json(root / "PHASE3_COMPETITIVE_MATRIX_2026-10-07.json")
    manifest = _load_json(root / "research/PUBLIC_SOURCE_MANIFEST_20261010.json")
    if manifest.get("schema_version") != 1:
        raise ValueError("INVALID_PUBLIC_SOURCE_MANIFEST")
    listed = {x["id"]: x for x in manifest.get("sources", [])}
    if set(listed) != set(SOURCE_META):
        raise ValueError("PUBLIC_MANIFEST_SOURCE_SET_MISMATCH")
    registry = seed_from_phase3(as_of=as_of, evidence=evidence, matrix=matrix)
    for ident, (kind, published, expiry, summary) in SOURCE_META.items():
        row = listed[ident]
        if not row["url"].startswith("https://"):
            raise ValueError("PUBLIC_SOURCE_MUST_USE_HTTPS")
        source = {
            "id": f"20261010.{ident}",
            "type": kind, "url": row["url"], "publisher": row["publisher"],
            "captured_at": CAMPAIGN_DATE, "valid_until": expiry,
            "excerpt": summary, "excerpt_sha256": digest(summary),
            "collection_method": CAPTURE_METHOD,
            "original_page_independently_fact_checked": False,
            "full_page_archived_in_repo": False,
        }
        if published is not None:
            source["published_at"] = published
        if kind == "VENDOR_CLAIM_SNAPSHOT":
            source["page_directly_reverified"] = False
        registry["sources"].append(source)
    for ident, lane, issue, subject, stance, statement, kind, raw_ids, priority, action in CLAIMS:
        registry["claims"].append({
            "id": ident, "lane": lane, "issue_key": issue,
            "subject": subject, "stance": stance,
            "statement": statement, "classification": kind,
            "source_ids": [f"20261010.{sid}" for sid in raw_ids],
            "importance": priority, "next_test": action,
        })
    errors = validate_registry(registry, as_of=as_of)
    if errors:
        raise ValueError("INVALID_CAMPAIGN: " + "; ".join(errors))
    return registry


def campaign_brief(*, as_of: date, root: Path = ROOT) -> dict:
    """Fail-closed merged, dated report. Nothing auto-promoted to verified."""
    return compile_brief(campaign_registry(as_of=as_of, root=root), as_of=as_of)
