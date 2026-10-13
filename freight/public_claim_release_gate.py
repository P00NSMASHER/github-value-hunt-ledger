"""RETALLY public copy preflight / Mission 36.

This is a conservative deterministic build-time blocklist for *known high-risk*
factual claims. It is not an AI fact-checker, legal signoff, security scanner,
live social-post moderation, or an authorization to market RETALLY.

Checks rendered HTML text (including metadata and JSON-LD), allowlisted JS,
CSS, CSV, XML and text copy BEFORE GitHub Pages output is written. It rejects
asserted past customer recoveries, unsupported measured audit performance,
guaranteed refunds, and fabricated recoverable TAM tied to public research.

The existing Mission 35 closed 16-claim/18-human-approval research policy is
validated each time; those research receipts never confer publication rights.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import unicodedata

from freight import research_claim_clearance_m35 as m35

RELEVANT_EXTENSIONS = frozenset({".html",".htm",".js",".txt",".csv",".xml",".css"})
RULES = (
    # First-person operational track records: not hypothetical examples,
    # definitions of fees, or conditionals about potential findings.
    ("CLAIMED_CUSTOMER_RECOVERIES",
     r"\b(?:retally(?:['’]s)?|we(?:['’]ve)?|our\s+(?:company|team|platform))"
     r"(?:\s+(?:has|have|already|successfully|personally))?"
     r"\s+(?:recovered|refunded|saved|returned|collected|audited)"
     r"\s+(?:over\s+|more\s+than\s+|nearly\s+|approximately\s+)?"
     r"(?:\$\s*[\d,]+(?:\.\d+)?(?:\s*(?:m|b|k|million|billion))?"
     r"|\d[\d,]*\s+(?:paid\s+)?(?:freight\s+)?(?:invoices|clients|customers|shipments|bills))"),
    ("CLAIMED_REAL_CUSTOMER_RESULT",
     r"\b(?:recovered|saved|refunded)\s+\$\s*[\d,]+(?:\.\d+)?"
     r".{0,65}\bfor\s+(?:our|a\s+real|a\s+verified|an\s+actual)\s+"
     r"(?:customer|client|shipper)\b"),
    ("UNVERIFIED_AUDIT_ACCURACY",
     r"\b(?:retally(?:['’]s)?|our|we)\b.{0,65}"
     r"\b(?:verified|proven|actual|real.world|achieved|delivered)\s+"
     r"(?:\d{2,3}(?:\.\d+)?\s*%|\d{2,3}\s+percent)\s+"
     r"(?:freight\s+)?(?:accuracy|recovery|refund|error.detection|success)\b"),
    ("UNVERIFIED_AUDIT_RATE",
     r"\b(?:retally(?:['’]s)?|our|we)\b.{0,55}"
     r"\b(?:accuracy|recovery|refund|success|error.detection)\s+rate"
     r"\s*(?:of|is|:|=)\s*(?:\d{2,3}(?:\.\d+)?\s*%|\d{2,3}\s+percent)(?=\s|[.!?,;]|$)"),
    ("GUARANTEED_CUSTOMER_OUTCOMES",
     r"\b(?:guaranteed|guarantees?|promise(?:d|s)?)\s+"
     r"(?:\d{2,3}\s*%\s+)?"
     r"(?:freight\s+)?(?:refunds?|recover(?:y|ies)|savings?|accuracy|cash\s+back)\b"),
    ("FABRICATED_RECOVERABLE_TAM",
     r"\b(?:retally(?:['’]s)?|our\s+(?:recovery|audit|freight)\s+)?"
     r"(?:recoverable|serviceable|addressable)\s+(?:freight\s+)?"
     r"(?:audit\s+)?(?:market|tam|opportunity|carrier\s+overcharges?)"
     r"\s*(?:is|of|worth|=|:)\s*(?:\$|usd\s+)\s*[\d,.]+"),
    ("PUBLISHED_M34_GAP_AS_RECOVERY",
     r"\b(?:\$\s*)?(?:142[,. ]?607[,. ]?754|142[,. ]?60\d)"
     r"(?:\s*(?:million|billion|bn|b|m))?.{0,75}"
     r"(?:recoverable|refunds?|overcharges?|audit\s+tam|addressable\s+market)"
     r"|(?:recoverable|refunds?|overcharges?|audit\s+tam)"
     r".{0,75}\b(?:\$\s*)?(?:142[,. ]?607[,. ]?754|142[,. ]?60\d)"
     r"(?:\s*(?:million|billion|bn|b|m))?"),
)
REGEXES = tuple(
    (code,re.compile(pattern,re.I))
    for code,pattern in RULES
)
# Do not suppress offending claims simply because "sample" is mentioned
# somewhere else on the page. Review exact block/metadata string.
BLOCK_ELEMENTS = frozenset({
    "title","p","li","h1","h2","h3","h4","h5","h6","dt",
    "dd","blockquote","figcaption","summary","button","th","td",
    "header","footer","section","article","aside","form"
})
META_IDENTIFIERS = frozenset({
    "description","og:title","og:description","twitter:title",
    "twitter:description","itemprop:description","itemprop:name"
})
JSONLD_KEYS = frozenset({"name","description","headline","text","reviewBody","award"})


@dataclass(frozen=True)
class CopyViolation:
    file: str
    channel: str
    rule: str
    excerpt: str


def _normalize(value: str) -> str:
    value=unicodedata.normalize("NFKC",value)
    value=value.replace("\u200b","").replace("\ufeff","")
    value=value.replace("’","'").replace("–","-").replace("—","-")
    return " ".join(value.split())


def _jsonld_values(obj: object) -> list[str]:
    if type(obj) is dict:
        result=[]
        for key,val in obj.items():
            if key in JSONLD_KEYS and type(val) is str:
                result.append(val)
            elif type(val) in (dict,list):
                result.extend(_jsonld_values(val))
        return result
    if type(obj) is list:
        output=[]
        for val in obj:
            output.extend(_jsonld_values(val))
        return output
    return []


class _PageCopy(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks=[]
        self.current=[]
        self.hidden=None
        self.script_parts=[]

    def _flush(self):
        if self.current:
            rendered=_normalize(" ".join(self.current))
            if rendered:
                self.blocks.append(("visible",rendered))
            self.current=[]

    def handle_starttag(self,tag,attrs):
        if self.hidden is not None:
            return
        attrs=dict(attrs)
        if tag in ("script","style","template"):
            self._flush()
            self.hidden="jsonld" if (
                tag=="script" and attrs.get("type","").casefold()=="application/ld+json"
            ) else tag
            self.script_parts=[]
            return
        if tag in BLOCK_ELEMENTS:
            self._flush()
        if tag=="meta":
            kind=attrs.get("name",attrs.get("property",""))
            if attrs.get("itemprop"):
                kind="itemprop:"+attrs.get("itemprop","")
            if kind.casefold() in META_IDENTIFIERS and attrs.get("content"):
                self.blocks.append(("metadata",_normalize(attrs["content"])))
        if tag not in ("script","style"):
            for key in ("alt","aria-label","title"):
                if attrs.get(key):
                    self.blocks.append(("attribute",_normalize(attrs[key])))

    def handle_data(self,data):
        if self.hidden=="jsonld":
            self.script_parts.append(data)
        elif self.hidden is None:
            self.current.append(data)

    def handle_endtag(self,tag):
        if self.hidden is not None:
            if (self.hidden=="jsonld" and tag=="script"):
                try:
                    parsed=json.loads("".join(self.script_parts))
                except (TypeError,ValueError):
                    raise ValueError("PUBLIC_CLAIM_GATE_JSONLD_INVALID")
                for text in _jsonld_values(parsed):
                    self.blocks.append(("jsonld",_normalize(text)))
                self.hidden=None
                self.script_parts=[]
            elif self.hidden==tag:
                self.hidden=None
            return
        if tag in BLOCK_ELEMENTS:
            self._flush()

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)

    def finish(self):
        if self.hidden is not None:
            raise ValueError("PUBLIC_CLAIM_GATE_HTML_UNCLOSED_SCRIPT_OR_STYLE")
        self._flush()
        return self.blocks


def _content_blocks(name: str,content: str) -> list[tuple[str,str]]:
    extension=Path(name).suffix.lower()
    if extension not in RELEVANT_EXTENSIONS:
        return []
    if extension in {".html",".htm"}:
        parser=_PageCopy()
        parser.feed(content)
        return parser.finish()
    # Raw script, style, and text content is scanned per line, preventing
    # distant unrelated statements from being spliced into fake findings.
    return [(extension,_normalize(line)) for line in content.splitlines() if line.strip()]


def _check_authority() -> None:
    """No source data or SHA consistency receipt confers publication approval."""
    from freight.research_pilot_preflight import build_preflight
    book=m35._policy()
    problems=m35.validate_policy(book,as_of=date.today())
    if problems:
        raise ValueError("PUBLIC_CLAIM_GATE_M35_SOURCE_POLICY_INVALID:"+";".join(problems))
    report=build_preflight(as_of=date.today())
    if (report.get("required_controls")!=18
        or report.get("unmet_requirements")!=18
        or report.get("controls_with_independently_verified_external_evidence")!=0
        or report.get("public_performance_claims_permitted") is not False
        or report.get("real_invoices_received")!=0):
        raise ValueError("PUBLIC_CLAIM_GATE_HUMAN_APPROVAL_SOURCE_CHANGED")
    if (book.get("external_claims_approved")!=0
        or book.get("real_customer_invoices_observed")!=0
        or book.get("no_external_marketing_or_outreach_authorized") is not True):
        raise ValueError("PUBLIC_CLAIM_GATE_FALSE_APPROVAL")


def _is_negated_or_faq_question(text:str,rule:str,start:int,end:int)->bool:
    """Avoid mistaking 'Do you guarantee recovery?' or 'we do not' for a promise."""
    if rule!="GUARANTEED_CUSTOMER_OUTCOMES":
        return False
    left=text[max(0,start-65):start].casefold()
    right=text[end:min(len(text),end+10)]
    if re.search(r"\b(?:not|never|no|without)\s+$",left):
        return True
    if re.search(r"\b(?:do|does|can|could|would|will)\s+(?:you|we|retally)\s+$",left) and (
        "?" in right or "?" in text[start:]
    ):
        return True
    return False


def scan_public_copy(text_assets: dict[str,str]) -> list[CopyViolation]:
    if type(text_assets) is not dict:
        raise ValueError("PUBLIC_CLAIM_GATE_ASSET_MAP_REQUIRED")
    issues=[]
    for name,content in sorted(text_assets.items()):
        if (type(name) is not str or name.startswith("/")
            or ".." in Path(name).parts or
            type(content) is not str):
            raise ValueError("PUBLIC_CLAIM_GATE_INVALID_ASSET_PATH_OR_COPY")
        for channel,value in _content_blocks(name,content):
            if not value:
                continue
            for rule,pattern in REGEXES:
                for match in pattern.finditer(value):
                    if _is_negated_or_faq_question(
                        value,rule,match.start(),match.end()
                    ):
                        continue
                    issues.append(CopyViolation(
                        file=name,channel=channel,rule=rule,
                        excerpt=value[max(0,match.start()-44):min(len(value),match.end()+44)]
                    ))
    return issues


def require_public_copy_clearance(text_assets:dict[str,str]) -> None:
    _check_authority()
    issues=scan_public_copy(text_assets)
    if issues:
        # Only deterministic high-risk copy-pattern matches. A clean result
        # is NOT general legal, accuracy, advertising, or consent clearance.
        location=", ".join(f"{v.file}:{v.channel}:{v.rule}" for v in issues[:8])
        raise ValueError("PUBLIC_CLAIM_GATE_UNSUPPORTED_ASSERTION: "+location)


def main() -> None:
    from freight.site.build import SOURCE,TEXT_SOURCE_FILES
    ap=argparse.ArgumentParser(description="Check the allowlisted public RETALLY source copy, not customer evidence")
    ap.add_argument("--site-root",type=Path,default=SOURCE)
    args=ap.parse_args()
    src=args.site_root.resolve()
    text_assets={}
    for name in TEXT_SOURCE_FILES:
        path=(src/name).resolve()
        if src not in path.parents or not path.is_file():
            raise ValueError("PUBLIC_CLAIM_GATE_MISSING_OR_SYMLINK_ASSET:"+name)
        text_assets[name]=path.read_text(encoding="utf-8")
    require_public_copy_clearance(text_assets)
    print(json.dumps({
        "result":"PASS_NO_KNOWN_HIGH_RISK_STATIC_COPY_PATTERN",
        "assets_scanned":len(text_assets),
        "external_claims_approved":0,
        "human_pilot_requirements_unmet":18,
        "scope":"FREIGHT_GITHUB_PAGES_ALLOWLISTED_PUBLIC_COPY_ONLY_NOT_ALL_EXTERNAL_CHANNELS",
    },sort_keys=True))


if __name__=="__main__":
    main()
