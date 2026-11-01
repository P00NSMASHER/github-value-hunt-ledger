"""Lab 14 source reconnaissance: inspect publicly released Census SAS XLSX safely.

A read-only source-discovery utility: logs limited national NAICS rows and
the surrounding table headings. It does not infer source correctness or freight
invoice recoveries, and does not store raw publisher workbooks in the repo.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import PurePosixPath
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = "https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/"
ALLOWED = {
    "revised_table1": ROOT + "Table1.xlsx",
    "revised_table2": ROOT + "Table2.xlsx",
    "original_2017_2022": ROOT + "sas-22.xlsx",
}
NS = {"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ZIP_LIMIT = 1_700_000
MAX_MEMBER = 9_000_000


def get_source(key: str) -> bytes:
    if key not in ALLOWED:
        raise ValueError("SAS_UNAPPROVED_SOURCE_KEY")
    url=ALLOWED[key]
    request=Request(url,headers={"User-Agent":"RETALLY-Lab14-Public-Census-SAS-Research/1.0"})
    with urlopen(request,timeout=30) as response:
        if response.geturl()!=url:
            raise ValueError("SOURCE_REDIRECTED")
        raw=response.read(ZIP_LIMIT+1)
    if len(raw)>ZIP_LIMIT or raw[:4]!=b"PK\x03\x04":
        raise ValueError("INVALID_OR_OVERSIZED_PUBLISHER_XLSX")
    return raw


def scan_xlsx(raw: bytes, *, key: str) -> dict:
    if key not in ALLOWED or type(raw) is not bytes or not raw or len(raw)>ZIP_LIMIT:
        raise ValueError("INVALID_SOURCE_OR_UNBOUNDED_FILE")
    with ZipFile(BytesIO(raw)) as archive:
        entries=archive.infolist()
        if len(entries)>120 or not entries:
            raise ValueError("UNBOUNDED_PUBLISHER_WORKBOOK_MEMBERS")
        for item in entries:
            if item.file_size>MAX_MEMBER or item.filename.startswith("/") or any(
                component in ("","..") for component in item.filename.split("/")
            ):
                raise ValueError("UNSAFE_PUBLISHER_WORKBOOK_MEMBER")
        shared=[]
        if "xl/sharedStrings.xml" in archive.namelist():
            tree=ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in tree.findall("m:si",NS):
                shared.append("".join(el.text or "" for el in item.iter("{"+NS["m"]+"}t")))
        worksheets=[n for n in archive.namelist()
                    if n.startswith("xl/worksheets/") and n.endswith(".xml")
                    and "/_rels/" not in n]
        if not worksheets or len(worksheets)>35:
            raise ValueError("EXPECTED_WORKBOOK_SHEETS_ABSENT")
        sheet_out=[]
        for sheetname in sorted(worksheets):
            root=ET.fromstring(archive.read(sheetname))
            headings=[]
            hits=[]
            nrows=0
            for row in root.findall(".//m:sheetData/m:row",NS):
                nrows+=1
                if nrows>15000:
                    raise ValueError("PUBLISHER_SHEET_HAS_TOO_MANY_ROWS")
                cells={}
                for cell in row.findall("m:c",NS):
                    ref=cell.get("r","")
                    typ=cell.get("t")
                    val=cell.find("m:v",NS)
                    if typ=="inlineStr":
                        inline=cell.find("m:is",NS)
                        value="".join(x.text or "" for x in inline.iter("{"+NS["m"]+"}t")) if inline is not None else ""
                    elif val is None:
                        value=""
                    elif typ=="s":
                        ix=int(val.text or "-1")
                        if ix<0 or ix>=len(shared): raise ValueError("BAD_SHARED_STRING_REFERENCE")
                        value=shared[ix]
                    else:
                        value=val.text or ""
                    if value:
                        cells[ref]=str(value)[:230]
                if len(headings)<15 and cells:
                    headings.append({"row":row.get("r"),"cells":dict(list(cells.items())[:14])})
                if any("484122" in value or "less than truckload" in value.lower()
                       for value in cells.values()):
                    hits.append({"row":row.get("r"),"cells":dict(list(cells.items())[:35])})
            sheet_out.append({
                "sheet_member":sheetname,"rows":nrows,
                "headings":headings[:12],
                "naics_484122_hits":hits[:15],
                "total_matching_rows":len(hits),
            })
        return {
            "source_id":key,"source_url":ALLOWED[key],
            "raw_xlsx_bytes":len(raw),"raw_xlsx_sha256":sha256(raw).hexdigest(),
            "source_is_original_census_url":True,
            "revenue_values_independently_reconciled":False,
            "all_values_are_employer_industry_estimates_not_customer_invoices":True,
            "sheets":sheet_out,
        }


def main() -> None:
    for key in ALLOWED:
        try:
            print("SAS_SOURCE_DISCOVERY",json.dumps(scan_xlsx(get_source(key),key=key)),flush=True)
        except (OSError,ValueError) as exc:
            print("SAS_SOURCE_UNREACHABLE_OR_INVALID",key,type(exc).__name__,str(exc)[:160],flush=True)


if __name__=="__main__":
    main()
