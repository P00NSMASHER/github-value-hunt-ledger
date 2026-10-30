"""Read-only discovery of CMA CGM's contemporaneous Indian 2022 tariff links.

Only reads the exact official Jan 2022 historical carrier announcement, caps
network response size, and prints official publisher PDF metadata URLs. Does
not use a login, submit forms, save files, contact a company, calculate a
freight overcharge, or certify that a rate governed an actual shipment.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import re
from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

URL = ("https://www.cma-cgm.com/local/india/news/2582/"
       "revised-detention-demurrage-tariff-offloading-fee-empty-return-tariff-export-import-w-e-f-20th-jan-2022")
MAX_HTML_BYTES = 2_000_000
MAX_LINKS = 60
DOC_HOST = "www.cma-cgm.com"
DOC_PATHS = ("/assets/public/pdf/", "/assets/public/documents/")
PDF_HINTS = re.compile(r"(detention|demurrage|offloading|off-loading|empty.return|tariff)",re.I)
LINK_HINTS = re.compile(r"export|detention|demurrage",re.I)


class DiscoveryHold(ValueError):
    pass


def _official(url: str, *, pdf: bool) -> bool:
    if not isinstance(url, str) or len(url) > 1200:
        return False
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname != DOC_HOST
                or p.username or p.password or p.port not in (None, 443)
                or p.fragment or any(ord(ch)<32 or ch=="\\" for ch in url)):
            return False
        path = unquote(p.path)
        if ".." in path.split("/"):
            return False
        if pdf and (not path.lower().endswith(".pdf")
                    or not any(path.startswith(prefix) for prefix in DOC_PATHS)):
            return False
        return True
    except ValueError:
        return False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiscoveryHold("REDIRECT_NOT_AUTOMATICALLY_AUTHORIZED")


class _OfficialHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            d = dict(attrs)
            self.active = [d.get("href", ""), []]

    def handle_data(self, data):
        if self.active is not None:
            self.active[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            url, chunks = self.active
            self.links.append((url, " ".join("".join(chunks).split())))
            self.active = None


def extract_official_rate_links(page: bytes) -> list[dict]:
    """Never invent a link by extrapolating a publisher filename."""
    if not isinstance(page,bytes) or not page or len(page)>MAX_HTML_BYTES:
        raise DiscoveryHold("OVERSIZED_OR_EMPTY_ANNOUNCEMENT")
    try:
        decoded=page.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DiscoveryHold("UNKNOWN_HTML_ENCODING") from exc
    if "<html" not in decoded[:8000].lower() and "<a " not in decoded[:8000].lower():
        raise DiscoveryHold("NOT_PUBLISHER_HTML")
    parser=_OfficialHTML()
    parser.feed(decoded)
    found={}
    for href,title in parser.links:
        if not href or len(found)>=MAX_LINKS:
            break
        actual=urljoin(URL,html.unescape(href))
        if not _official(actual,pdf=True):
            continue
        label=(title+" "+unquote(urlsplit(actual).path).rsplit("/",1)[-1])
        if not PDF_HINTS.search(label):
            continue
        # Public file pointers only; no private financial/customer data logged.
        found[actual]={"url":actual,"title":title[:140],
                       "export_specific":bool(LINK_HINTS.search(label)),
                       "detention_named":bool(re.search("detention",label,re.I)),
                       "demurrage_named":bool(re.search("demurrage",label,re.I))}
    return sorted(found.values(),key=lambda x:(not x["detention_named"],not x["export_specific"],x["url"]))


def source_fetch() -> bytes:
    if not _official(URL,pdf=False):
        raise DiscoveryHold("SOURCE_NOT_PINNED")
    opener=build_opener(_NoRedirect())
    try:
        with opener.open(Request(URL,headers={"Accept":"text/html",
            "User-Agent":"RETALLY-ReadOnlyTariffResearch/1.0"}),timeout=18) as r:
            if r.status!=200 or r.geturl()!=URL:
                raise DiscoveryHold("UNEXPECTED_SOURCE_RESPONSE")
            data=r.read(MAX_HTML_BYTES+1)
            mime=r.headers.get("Content-Type","").split(";",1)[0].lower()
            if mime not in ("text/html","application/xhtml+xml"):
                raise DiscoveryHold("NOT_HTML_RESPONSE")
    except DiscoveryHold:
        raise
    except Exception as exc:
        raise DiscoveryHold("ORIGINAL_PUBLISHER_NEWS_UNAVAILABLE") from exc
    if len(data)>MAX_HTML_BYTES:
        raise DiscoveryHold("SOURCE_SIZE_LIMIT")
    return data


def public_report(page:bytes) -> dict:
    return {
        "source_url":URL,
        "html_sha256":hashlib.sha256(page).hexdigest(),
        "source_bytes":len(page),
        "official_pdf_links":extract_official_rate_links(page),
        "invoice_or_bank_record_acquired":False,
        "original_shipment_rate_applicability_verified":False,
        "customer_settlement_verified":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--live",action="store_true")
    args=p.parse_args()
    if not args.live:
        raise SystemExit("Explicit --live is required; no automatic network access")
    try:
        x=public_report(source_fetch())
    except DiscoveryHold as exc:
        print(json.dumps({"status":"PUBLISHER_SOURCE_HOLD","reason":str(exc),
                          "source_url":URL},sort_keys=True))
        raise SystemExit(0)
    print(json.dumps({"status":"LINKS_FOUND" if x["official_pdf_links"]
                      else "OFFICIAL_HTML_NO_LINKS","report":x},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
