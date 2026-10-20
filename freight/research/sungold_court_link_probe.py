"""Discover ACTUAL public judgment/case-attachment links; never guess file URLs.

Only performs a read-only HTTPS GET against the exact already-public Indian
Kanoon judgment page. Does not log in, post forms, solve CAPTCHA, initiate any
court-file request, pay, contact a party, fetch bank statements, or store raw HTML.
Any discovered third-party exhibit link still requires independent provenance
and access/rights review before ingestion. A "Download Court Copy" button is
not an attached trial exhibit or a settlement.
"""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
import json
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

URL="https://indiankanoon.org/doc/161666818/"
MAX_HTML_BYTES=1_500_000
TRUSTED_DOMAINS=frozenset(("indiankanoon.org","www.indiankanoon.org",
    "delhidistrictcourts.nic.in","services.ecourts.gov.in","districts.ecourts.gov.in"))


class ProbeHold(ValueError):
    pass


class NoCrossSiteRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed=urlsplit(newurl)
        if parsed.scheme!="https" or parsed.hostname not in ("indiankanoon.org","www.indiankanoon.org"):
            raise ProbeHold("OFF_SOURCE_REDIRECT")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class PublicLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchor=None
        self.button=None
        self.links=[]
        self.buttons=[]
        self.forms=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="a":
            self.anchor=(d.get("href",""),[])
        if tag=="button":
            self.button=(d.get("type",""),d.get("id",""),d.get("name",""),[])
        if tag=="input" and d.get("type","").lower() in ("submit","button"):
            self.buttons.append(d.get("value","")[:100])
        if tag=="form":
            self.forms.append({"method":d.get("method","GET")[:12].upper(),
                               "has_action":bool(d.get("action"))})
    def handle_data(self,data):
        if self.anchor is not None:
            self.anchor[1].append(data)
        if self.button is not None:
            self.button[3].append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.anchor is not None:
            href,chunks=self.anchor
            self.links.append((href," ".join("".join(chunks).split())))
            self.anchor=None
        if tag=="button" and self.button is not None:
            kind,id_,name,chunks=self.button
            self.buttons.append(" ".join("".join(chunks).split())[:100])
            self.button=None


def inspect_public_source(raw:bytes)->dict:
    if not isinstance(raw,bytes) or len(raw)>MAX_HTML_BYTES or not raw:
        raise ProbeHold("EMPTY_OR_OVERSIZED_PUBLIC_HTML")
    try:
        decoded=raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ProbeHold("BAD_DOCUMENT_ENCODING") from exc
    if "<html" not in decoded[:3000].lower():
        raise ProbeHold("NOT_HTML")
    parser=PublicLinks()
    parser.feed(decoded)
    matching=[]
    for href,label in parser.links:
        if not href or len(matching)>=30:
            continue
        resolved=urljoin(URL,href)
        p=urlsplit(resolved)
        if (p.scheme!="https" or p.hostname not in TRUSTED_DOMAINS
            or p.username or p.password or p.fragment or p.port not in (None,443)):
            continue
        low=(label+" "+p.path).lower()
        if not any(k in low for k in ("court copy","original","judgment","judgement",
                                     "exhibit","pdf","file","download","161666818")):
            continue
        # Do not output query strings, hidden tokens, bank docs or user details.
        matching.append({"host":p.hostname,"path":p.path[:200],
                         "has_query":bool(p.query),
                         "label_category":
                         "TRIAL_EXHIBIT" if "exhibit" in low else
                         "PDF" if "pdf" in low else
                         "COURT_COPY" if "court copy" in low else "OTHER"})
    buttons=[b for b in parser.buttons if any(
        k in b.lower() for k in ("pdf","court copy","download","get","print"))]
    return {
      "source_url":URL,
      "public_html_bytes":len(raw),
      "html_sha256":hashlib.sha256(raw).hexdigest(),
      "relevant_public_links":matching,
      "relevant_buttons":buttons[:15],
      "form_methods":[f["method"] for f in parser.forms[:10]],
      "standalone_trial_exhibit_originals_verified":False,
      "original_bank_statement_downloaded":False,
      "customer_postjudgment_bank_settlement_verified":False,
      "source_court_judgment_not_trial_evidence":True,
    }


def fetch_page():
    op=build_opener(NoCrossSiteRedirect())
    try:
        req=Request(URL,headers={"Accept":"text/html",
            "User-Agent":"RETALLY-ReadOnlyCourtSourceDiscovery/1.0"})
        with op.open(req,timeout=18) as response:
            if response.status!=200:
                raise ProbeHold("UNEXPECTED_HTTP")
            if urlsplit(response.geturl()).hostname not in ("indiankanoon.org","www.indiankanoon.org"):
                raise ProbeHold("OFF_SOURCE_FINAL_URL")
            return response.read(MAX_HTML_BYTES+1)
    except ProbeHold:
        raise
    except Exception as exc:
        raise ProbeHold("PUBLIC_HTML_FETCH_UNAVAILABLE") from exc


def main():
    try:
        r=inspect_public_source(fetch_page())
        print(json.dumps({"status":"PUBLIC_SOURCE_ONLY","report":r},indent=2,sort_keys=True))
    except ProbeHold as exc:
        print(json.dumps({"status":"PUBLIC_SOURCE_HOLD","reason":str(exc)},sort_keys=True))


if __name__=="__main__":
    main()
