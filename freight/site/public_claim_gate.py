"""RETALLY pre-publication claim-inference guard (Mission 36).

Narrow, deterministic static guard for the *actual allowlisted public bundle*
and selected company-authored marketing templates. Prevents known M35 false
commercial claims, unsourced macroeconomic amounts and unlabeled sample
recoveries. Does not execute HTTP, approve marketing, inspect third-party
chatbot answers, or infer real customer evidence from passing tests.

The source claim register is the one frozen Lab 14 M35 policy. A hash is a
local integrity check, NOT an independent signer, legal review or buyer
authorization. The guard is only an additional negative deployment check.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Mapping
import unicodedata

SOURCE = Path(__file__).resolve().parent
CLAIM_POLICY = SOURCE.parent/"research"/"CLAIM_CLEARANCE_M35_20261012.json"
POLICY_GIT_BLOB_SHA1 = "752ae34f4bc2b6e1baa329b8955efd35dd826f38"
STATIC_TEXT_EXTENSIONS = frozenset({".html",".htm",".txt",".csv",".xml",".js",".md"})
EXAMPLE_PAGES = frozenset({
    "freight-audit-example.html",
    "recovery-status-example.html",
})
RESEARCH_FIGURES = (
    # M35 is currently approved only for INTERNAL qualified research, not
    # customer-facing marketing. Percentages are intentionally exact.
    ("M35-01",re.compile(r"(?<!\d)(?:545\s?,\s?435(?:\.000)?|545435(?:\.000)?)(?!\d)",re.I)),
    ("M35-02",re.compile(r"(?<!\d)(?:402\s?,\s?827(?:\.246)?|402827(?:\.246)?)(?!\d)",re.I)),
    ("M35-03",re.compile(
        r"(?<!\d)(?:142\s?,\s?607(?:\.754)?|142607(?:\.754)?)(?!\d)"
        r"|\$\s*142(?:[.,]6\d*)?\s*(?:billion|bn|b)\b",re.I,
    )),
    ("M35-04",re.compile(r"(?<!\d)73\.85\s*%",re.I)),
    ("M35-05",re.compile(r"(?<!\d)8\.05\s*%",re.I)),
    ("M35-06",re.compile(r"(?<!\d)4\.02\s*%",re.I)),
    ("M35-07",re.compile(r"(?<!\d)1\.18\s*%",re.I)),
    ("M35-08",re.compile(r"(?<!\d)0\.45\s*(?:percentage\s+points?|pp)\b",re.I)),
)
PERFORMANCE_CLAIMS = (
    ("UNVERIFIED_OWN_RECOVERED_MONEY",re.compile(
        r"\b(?:we(?:['’]ve|\s+have)?|retally(?:['’]s)?|our\s+(?:company|team))\s+"
        r"(?:(?:have|has|already|successfully)\s+){0,2}"
        r"(?:recovered|refunded|saved|returned)\s+"
        r"(?:(?:over|more\s+than|nearly|about)\s+)?\$[\d,]+",re.I,
    )),
    ("UNVERIFIED_CUSTOMER_RECOVERY_RESULTS",re.compile(
        r"\b(?:our\s+(?:customers|clients|shippers)|retally\s+customers)\s+"
        r"(?:(?:have|already|successfully)\s+){0,2}"
        r"(?:saved|recovered|refunded)\s+"
        r"(?:(?:over|more\s+than)\s+)?\$[\d,]+",re.I,
    )),
    ("UNVERIFIED_HELPED_CUSTOMERS_RECOVER",re.compile(
        r"\b(?:we|retally)\s+(?:have\s+)?helped\s+"
        r"(?:[\d,]+\s+)?(?:customers|shippers|clients)\s+"
        r"(?:recover|save)\s+\$[\d,]+",re.I,
    )),
    ("UNVERIFIED_CUSTOMER_SUCCESS_PERCENT",re.compile(
        r"\b\d+(?:\.\d+)?\s*%\s+of\s+(?:our\s+|retally['’]s\s+)?"
        r"(?:customers|clients)\s+(?:saved|recovered|were\s+satisfied)\b",re.I,
    )),
    ("UNVERIFIED_OWN_AUDIT_VOLUME",re.compile(
        r"\b(?:we(?:['’]ve|\s+have)?|retally(?:\s+has)?|our\s+team)\s+"
        r"(?:(?:have|has|already|successfully)\s+){0,2}"
        r"(?:audited|reviewed|processed)\s+"
        r"(?:(?:more\s+than|over)\s+)?[\d,]+\s+"
        r"(?:freight\s+)?(?:invoices|shipments|customer\s+accounts)\b",re.I,
    )),
    ("UNVERIFIED_OWN_RECOVERY_RATE",re.compile(
        r"\b(?:our|retally(?:['’]s)?)(?:\s+\w+){0,3}\s+"
        r"(?:recovery|success|invoice\s+error|savings|accuracy)\s+rate\s*"
        r"(?:is|of|:)?\s*\d+(?:\.\d+)?\s*%",re.I,
    )),
    ("UNVERIFIED_OWN_SECURITY_CERTIFICATION",re.compile(
        r"\b(?:we|retally|our\s+platform)\s+(?:is|are)\s+"
        r"(?:soc\s*2|iso\s*27001)\s+(?:certified|compliant|attested)\b",re.I,
    )),
    ("UNVERIFIED_GUARANTEED_REFUNDS",re.compile(
        r"\b(?:we\s+guarantee|retally\s+guarantees|guaranteed)\s+"
        r"(?:a\s+)?(?:recovery|refund|savings|overcharge\s+recoveries)\b",re.I,
    )),
)
MEANINGFUL_META = frozenset({
    "description","og:description","og:title","twitter:title",
    "twitter:description","keywords",
})


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def read_frozen_claim_policy()->dict:
    """Only M35's unchanged, no-approval source policy may drive site checks."""
    raw=CLAIM_POLICY.read_bytes()
    if _git_blob(raw)!=POLICY_GIT_BLOB_SHA1:
        raise ValueError("PUBLIC_CLAIM_GATE_POLICY_BLOB_CHANGED_HUMAN_REVIEW_REQUIRED")
    data=json.loads(raw.decode("utf-8"))
    claims=data.get("claim_registry",[])
    if (data.get("schema_version")!=1
        or data.get("scope")!="RETALLY_LAB14_M35_RESEARCH_TO_COMMERCIAL_CLAIM_FIREBREAK_NO_PUBLICATION"
        or data.get("required_pilot_gate_count")!=18
        or data.get("independent_human_signoffs_observed")!=0
        or data.get("external_claims_approved")!=0
        or data.get("real_customer_invoices_observed")!=0
        or data.get("recoverable_market_tam_usd") is not None
        or data.get("no_external_marketing_or_outreach_authorized") is not True
        or len(claims)!=16 or data.get("qualified_internal_claim_count")!=8
        or data.get("blocked_inference_claim_count")!=8
        or [x.get("id") for x in claims]!=[f"M35-{n:02d}" for n in range(1,17)]
        or any(c.get("public_publication_authorized") is not False
               or c.get("approves_customer_money") is not False for c in claims)):
        raise ValueError("PUBLIC_CLAIM_GATE_POLICY_HAS_UNVERIFIED_PUBLIC_AUTHORITY")
    return data


class _PublicationText(HTMLParser):
    """Visible copy + search, accessibility and structured metadata.

    Does not treat CSS selectors, HTML source comments or non-JSON scripts as
    natural-language commercial claims. Public JS text is scanned separately.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts:list[str]=[]
        self._suppressed:str|None=None

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta":
            meta=(a.get("name") or a.get("property") or "").lower()
            if meta in MEANINGFUL_META and a.get("content"):
                self.parts.append(a["content"])
        for attr in ("alt","aria-label","title","data-copy",
                     "data-claim","data-description","data-message"):
            if a.get(attr):
                self.parts.append(a[attr])
        if tag in ("style","script"):
            self._suppressed=(None if tag=="script" and
                a.get("type","").lower()=="application/ld+json" else tag)

    def handle_endtag(self,tag):
        if self._suppressed==tag:
            self._suppressed=None

    def handle_data(self,data):
        if self._suppressed!="style":
            # Also scan inline scripts: client-rendered strings can become
            # public-facing copy. CSS rule text is not prose.
            self.parts.append(data)


def public_readable_text(name:str,raw:str)->str:
    if type(name) is not str or not name or type(raw) is not str:
        raise ValueError("PUBLIC_CLAIM_GATE_TEXT_FILE_NAME_OR_BODY_INVALID")
    if Path(name).suffix.lower() in {".html",".htm"}:
        parser=_PublicationText()
        parser.feed(raw)
        parser.close()
        text=" ".join(parser.parts)
    else:
        text=raw
    return " ".join(unicodedata.normalize("NFKC",unescape(text)).split())


def inspect_public_text(name:str,raw:str,*,policy:dict|None=None)->list[str]:
    """Return deterministic violation IDs; no private text in failure output."""
    if policy is None:
        policy=read_frozen_claim_policy()
    if Path(name).suffix.lower() not in STATIC_TEXT_EXTENSIONS:
        return []
    text=public_readable_text(name,raw)
    found=[]
    if Path(name).name in EXAMPLE_PAGES:
        if not re.search(r"\bfictional\b",text,re.I):
            found.append("SYNTHETIC_EXAMPLE_MISSING_FICTIONAL_LABEL")
        if not re.search(r"\bnot (?:a )?customer results?\b",text,re.I):
            found.append("SYNTHETIC_EXAMPLE_MISSING_NOT_REAL_CUSTOMER_RESULT")
    if Path(name).name=="index.html" and (
        re.search(r"\b(?:recoveries posted|invoices reviewed)\b",text,re.I)
        and re.search(r"\b1,284\b",text)
    ):
        if not re.search(r"\bfictional data\b",text,re.I):
            found.append("HOME_SAMPLE_METRICS_MISSING_FICTIONAL_LABEL")
        if not re.search(r"\bnot (?:a )?customer results?\b",text,re.I):
            found.append("HOME_SAMPLE_METRICS_MISSING_NO_REAL_CUSTOMER_DISCLAIMER")

    # National original source values are presently internal-only research
    # under M35. No bare or polished external TAM/revenue/decomposition claim.
    for id_,matcher in RESEARCH_FIGURES:
        if matcher.search(text):
            found.append("RESEARCH_ONLY_NUMBER_IN_PUBLIC_COPY_"+id_)
    for id_,matcher in PERFORMANCE_CLAIMS:
        matches=list(matcher.finditer(text))
        # "No guaranteed recovery" is not an affirmative promise.
        # Suppression applies to THAT occurrence only: a denial elsewhere
        # cannot hide a separate affirmative customer recovery guarantee.
        if id_=="UNVERIFIED_GUARANTEED_REFUNDS":
            matches=[m for m in matches if not re.search(
                r"\b(?:no|not|never)\s*$",
                text[max(0,m.start()-18):m.start()],re.I,
            )]
        if matches:
            found.append(id_)
    return sorted(set(found))


def audit_public_bundle(bundle:Mapping[str,str],*,require_examples:bool=True)->dict:
    """Check rendered public allowlist BEFORE writing any output files.

    Cannot by itself authorize public publication or prove legal review. The
    existing build pipeline retains its contact, synthetic-demo and pricing
    gates, and deploys only under its independently gated main-branch job.
    """
    policy=read_frozen_claim_policy()
    if not isinstance(bundle,Mapping) or not bundle:
        raise ValueError("PUBLIC_CLAIM_GATE_EMPTY_OR_INVALID_BUNDLE")
    if require_examples:
        missing=EXAMPLE_PAGES-set(bundle)
        if missing or "index.html" not in bundle:
            raise ValueError("PUBLIC_CLAIM_GATE_MISSING_QUALIFIED_SYNTHETIC_EXAMPLE_PAGE")
    checked=[]
    errors=[]
    for name in sorted(bundle):
        if type(name) is not str or type(bundle[name]) is not str:
            raise ValueError("PUBLIC_CLAIM_GATE_NON_TEXT_OR_INVALID_PUBLIC_ENTRY")
        if Path(name).suffix.lower() not in STATIC_TEXT_EXTENSIONS:
            continue
        checked.append(name)
        for violation in inspect_public_text(name,bundle[name],policy=policy):
            errors.append(name+":"+violation)
    if errors:
        raise ValueError("PUBLIC_CLAIM_GATE_REJECTED:"+";".join(errors))
    return {
        "scope":"BUILD_TIME_PUBLICATION_NEGATIVE_CHECK_NOT_MARKETING_APPROVAL",
        "source_registry":"M35_PINNED_CLAIM_CLEARANCE",
        "policy_git_blob_sha1":POLICY_GIT_BLOB_SHA1,
        "files_scanned":len(checked),
        "registered_source_and_claim_cases":len(policy["claim_registry"]),
        "flagged_unsupported_claims":0,
        "independent_real_customer_pilot_approvals_verified":0,
        "independent_real_customer_pilot_requirements_unmet":18,
        "legal_or_external_marketing_publication_approved":False,
        "private_customer_data_accessed":False,
        "scan_fingerprint_sha256":sha256(
            json.dumps({
                n:sha256(bundle[n].encode("utf-8")).hexdigest() for n in checked
            },sort_keys=True,separators=(",",":")).encode("utf-8")
        ).hexdigest(),
    }
