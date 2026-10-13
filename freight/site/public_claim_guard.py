"""RETALLY / RecoveryOS public-build claim boundary (Mission 36).

Checks the exact HTML/SEO and browser-facing text assembled for publication.
It prevents known, high-confidence fake customer outcome/accuracy/market claims
and removal of existing fictional-demo labels. It does NOT approve other
marketing statements, confirm legal rights, authenticate real customers,
check Cloudflare's separate build, or substitute for human publication review.

The closed M35 Lab 14 claim policy is the internal source of blocked claim
categories. Only site source text enters this gate. No network, uploads, mail,
customer data, payment events, schedules or research source downloads occur.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re

TEXT_EXTENSIONS = frozenset({".html", ".js", ".json", ".txt", ".xml", ".csv", ".svg"})
MAX_TEXT_BYTES = 300_000
SCOPES = ("RETALLY", "RECOVERYOS")

# These are deliberately high-specificity matches, not a general-language
# reputation classifier. Editorial/source checks and human review remain
# necessary for any real-world claims not covered by these patterns.
UNSUPPORTED = (
    (
        "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES",
        re.compile(
            r"\b(?:(?:retally|recoveryos|we|our\s+(?:team|clients|customers))"
            r"\s+(?:have|has)|we['’]ve|(?:retally|recoveryos))"
            r"\s+(?:already\s+)?(?:successfully\s+)?"
            r"(?:recovered|saved|refunded|returned)\s+\$[\d,]+(?:\.\d{1,2})?\b",
            re.I,
        ),
    ),
    (
        "M35-15_UNVERIFIED_PAID_INVOICE_COHORT",
        re.compile(
            r"\b(?:(?:retally|recoveryos|we)\s+(?:have|has)|we['’]ve)\s+"
            r"(?:already\s+)?(?:audited|processed|reviewed)\s+"
            r"(?:over\s+|more\s+than\s+)?\d[\d,]*\s+"
            r"(?:real\s+)?(?:customer\s+)?(?:freight\s+)?"
            r"(?:invoices|bills|shipments)\b", re.I,
        ),
    ),
    (
        "M35-09_UNVERIFIED_RECOVERABLE_MARKET",
        re.compile(
            r"\b(?:recoverable\s+freight(?:\s+audit)?\s+(?:market|tam)"
            r"|freight\s+recovery\s+(?:market|tam))\s*"
            r"(?:is|worth|totals|of|:)?\s*\$[\d,.]+\s*"
            r"(?:million|billion|trillion|bn)?\b", re.I,
        ),
    ),
    (
        "M35-09_BEACENSUS_DENOMINATOR_MISTAKEN_FOR_CASH",
        re.compile(
            r"\$\s*142(?:[.,]\s*(?:607(?:[.,]754)?|608))?\s*"
            r"(?:billion|million|bn|b)?\b.{0,100}\b"
            r"(?:recoverable|unpaid\s+(?:freight\s+)?invoices?|"
            r"freight\s+(?:overcharges|refunds)|audit\s+(?:tam|market))\b",
            re.I,
        ),
    ),
    (
        "M35-10_FAKE_INVOICE_ACCURACY_OR_ERROR_RATE",
        re.compile(
            r"\b(?:73\.85|90|95|99|100)\s*%\s*"
            r"(?:freight\s+)?(?:invoice\s+accuracy|"
            r"audit\s+accuracy|invoices?\s+(?:wrong|overcharged|inaccurate)|"
            r"billing\s+error\s+rate|recovery\s+success\s+rate)\b", re.I,
        ),
    ),
    (
        "M35-10_UNVERIFIED_SERVICE_ACCURACY",
        re.compile(
            r"\b(?:our|retally(?:['’]s)?|recoveryos(?:['’]s)?)\s+"
            r"(?:invoice\s+)?(?:audit|billing|review|recovery)\s+"
            r"(?:accuracy|success|error)\s+(?:rate\s+)?(?:is|of|:)?\s*"
            r"\d{1,3}(?:\.\d+)?\s*%", re.I,
        ),
    ),
    (
        "M35-12_RECOVERY_GUARANTEE_NOT_PROVEN",
        re.compile(
            r"\b(?:guaranteed\s+(?:freight\s+)?(?:refunds?|recover(?:y|ies)|"
            r"savings)|(?:all|every)\s+(?:eligible\s+)?(?:freight\s+)?"
            r"(?:refunds?|recover(?:y|ies))\s+(?:are|is)\s+guaranteed"
            r"|100\s*%\s+(?:recovery|refund|success)\s+guarantee)\b", re.I,
        ),
    ),
    (
        "M35-10_UNVERIFIED_PROMOTIONAL_ACCURACY",
        re.compile(
            r"\b(?:retally|recoveryos|our\s+audits?|we)\s+(?:are\s+|is\s+)?"
            r"\d{2,3}(?:\.\d+)?\s*%\s+"
            r"(?:accurate|successful|effective)\b", re.I,
        ),
    ),
    (
        "M35-14_UNVERIFIED_CUSTOMER_OUTCOME_PERCENT",
        re.compile(
            r"\b(?:our|retally(?:['’]s)?|recoveryos(?:['’]s)?)\s+"
            r"(?:customers|clients)\s+(?:save|recover)\s+"
            r"(?:an?\s+average\s+of\s+)?\d{1,3}(?:\.\d+)?\s*%", re.I,
        ),
    ),
)

# These labels are already present in the real public source. They cannot
# silently disappear while fictional figures/calculators remain exposed.
REQUIRED_LABELS = {
    "RETALLY": {
        "index.html": (
            "fictional data",
            "illustrative only. not customer results.",
            "illustration only; signed engagement terms govern.",
            "recovery is not guaranteed.",
        ),
        "freight-audit-example.html": (
            "a fictional freight audit example",
            "this example uses fictional data only.",
        ),
        "recovery-status-example.html": (
            "fictional / synthetic example",
            "all amounts and parties on this page are fictional.",
            "not a customer result",
        ),
    },
    "RECOVERYOS": {
        "index.html": (
            "illustrative data. a finding is not recovered cash.",
        ),
    },
}


class PublicClaimViolation(ValueError):
    """A high-confidence unsupported public claim or lost sample safeguard."""


class _PublicHTML(HTMLParser):
    """Read visible/SEO/structured text; ignore CSS, comments and JS source."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.words: list[str] = []
        self.skipping = 0
        self.script_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str,str | None]]) -> None:
        pairs = dict(attrs)
        if tag == "script":
            # Inline code can construct browser-visible copy. Check both
            # JSON-LD and executable inline JavaScript source strings.
            self.script_text = True
        elif tag in {"style","template","noscript"}:
            self.skipping += 1
        if tag == "meta":
            # Description/OG/Twitter metadata are indexed even if not visible.
            if pairs.get("content") and (
                pairs.get("name","").lower() in {"description","twitter:description"}
                or pairs.get("property","").lower() in
                {"og:description","og:title","article:description"}
                or pairs.get("itemprop","").lower() in
                {"description","reviewbody","ratingvalue"}
            ):
                self.words.append(pairs["content"])
        elif tag in {"img","a","button","input","section"}:
            for attribute in ("alt","aria-label","title"):
                if pairs.get(attribute):
                    self.words.append(pairs[attribute])

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.script_text = False
        elif tag in {"style","template","noscript"}:
            self.skipping = max(0,self.skipping-1)

    def handle_data(self, data: str) -> None:
        if self.script_text or not self.skipping:
            self.words.append(data)


def _text_surface(name: str, content: str) -> str:
    if type(content) is not str or len(content.encode("utf-8")) > MAX_TEXT_BYTES:
        raise PublicClaimViolation("M36_TEXT_ASSET_MISSING_OR_OVER_MAXIMUM")
    if name.endswith((".html",".svg",".xml")):
        parser = _PublicHTML()
        parser.feed(content)
        content = " ".join(parser.words)
    return re.sub(r"\s+", " ", unescape(content)).strip().lower()


def _frozen_policy() -> None:
    # Import lazily so site builders retain the exact output asset manifest.
    from freight.research_claim_clearance_m35 import _policy, validate_policy
    book=_policy()
    errors=validate_policy(book,as_of=date.today())
    if (errors or book["claim_count"] != 16
        or book["blocked_inference_claim_count"] != 8
        or book["independent_human_signoffs_observed"] != 0
        or book["external_claims_approved"] != 0
        or book["real_customer_invoices_observed"] != 0
        or book["recoverable_market_tam_usd"] is not None
        or book["no_external_marketing_or_outreach_authorized"] is not True):
        raise PublicClaimViolation("M36_SOURCE_CLAIM_BOUNDARY_POLICY_INVALID_OR_APPROVED")


def validate_public_text_bundle(files: Mapping[str,str], *,site: str)->dict:
    """Fail a build before copying the public output; no content mutation.

    Never returns blanket authorization for public marketing. Only specific
    unsupported metrics and missing fictional labels are tested.
    """
    if site not in SCOPES or not isinstance(files,Mapping):
        raise PublicClaimViolation("M36_UNKNOWN_OR_MISSING_PUBLICATION_SURFACE")
    _frozen_policy()
    if not files or "index.html" not in files:
        raise PublicClaimViolation("M36_PUBLIC_INDEX_MISSING")
    normalized={}
    for name,content in files.items():
        if (type(name) is not str or "/" in name or "\\" in name
            or name in {"",".."} or Path(name).suffix.lower() not in TEXT_EXTENSIONS):
            raise PublicClaimViolation("M36_UNREVIEWED_OR_NONPUBLIC_TEXT_ASSET")
        normalized[name]=_text_surface(name,content)
    for name,expected in REQUIRED_LABELS[site].items():
        if name not in normalized:
            raise PublicClaimViolation("M36_REQUIRED_SYNTHETIC_EXAMPLE_PAGE_MISSING:"+name)
        for phrase in expected:
            if phrase not in normalized[name]:
                raise PublicClaimViolation(
                    "M36_FICTIONAL_SAMPLE_OR_FEE_ILLUSTRATION_DISCLOSURE_MISSING:"+name
                )
    for name,text in normalized.items():
        for code,pattern in UNSUPPORTED:
            if pattern.search(text):
                # Never expose untrusted claim text or visitor information in
                # build logs. Error includes only a rule and static path.
                raise PublicClaimViolation(code+":"+name)
    return {
        "site":site,
        "text_assets_checked":len(normalized),
        "high_risk_claim_patterns_checked":len(UNSUPPORTED),
        "required_fictional_disclosures_checked":
            sum(len(x) for x in REQUIRED_LABELS[site].values()),
        "unsupported_real_customer_claims_detected":0,
        "external_publication_authority_granted":False,
        "human_marketing_legal_review_replaced":False,
    }


def validate_public_tree(path:Path, *,site:str)->dict:
    """Check actual built HTML/SEO/JS assets after templating, before deploy."""
    root=Path(path).resolve()
    if not root.is_dir():
        raise PublicClaimViolation("M36_PUBLIC_BUILD_DIRECTORY_NOT_FOUND")
    text={}
    for file in root.rglob("*"):
        if file.is_symlink():
            raise PublicClaimViolation("M36_PUBLIC_ASSET_SYMLINK_NOT_ALLOWED")
        if file.is_file() and file.suffix.lower() in TEXT_EXTENSIONS:
            relative=file.relative_to(root).as_posix()
            if "/" in relative:
                # Only root-level visitor-facing publication text is expected.
                # Font license/source attribution JSON nested under assets is
                # not marketing copy and must not be mistaken for it.
                continue
            text[relative]=file.read_text(encoding="utf-8")
    return validate_public_text_bundle(text,site=site)


def main() -> None:
    p=argparse.ArgumentParser(description="Non-deploying RETALLY/RecoveryOS public claim QA")
    p.add_argument("--freight-root",type=Path)
    p.add_argument("--recoveryos-root",type=Path)
    args=p.parse_args()
    if args.freight_root is None and args.recoveryos_root is None:
        p.error("Provide an existing public build directory to inspect")
    for name,root in (("RETALLY",args.freight_root),("RECOVERYOS",args.recoveryos_root)):
        if root is None:
            continue
        checked=validate_public_tree(root,site=name)
        print(f"{name} PUBLIC CLAIM GATE PASSED: {checked['text_assets_checked']} text assets; "
              f"{checked['required_fictional_disclosures_checked']} demo/illustration labels; "
              "0 unsupported customer outcome / recoverable-market statements. "
              "Human content approval remains separate.")


if __name__ == "__main__":
    main()
