"""STB 2024 public-use rail waybill frozen fixed-width sample, research only."""
from hashlib import sha256
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
P=ROOT/"fixtures/public_stb_2024_waybill_first100_fixedwidth.txt"
M=ROOT/"fixtures/public_stb_waybill2024_first100_manifest.json"

def report():
    m=json.loads(M.read_text(encoding="utf8"))
    if P.is_symlink() or not P.is_file():
        raise ValueError("STB_UNTRUSTED_FILE")
    raw=P.read_bytes()
    if len(raw)!=m["sample_bytes"] or sha256(raw).hexdigest()!=m["sample_sha256"]:
        raise ValueError("STB_SAMPLE_CONTENT_CHANGED")
    lines=raw.splitlines(keepends=True)
    if len(lines)!=100 or any(len(row)!=249 or not row.endswith(b"\r\n") or len(row[:-2])!=247 or not row[:-2].isascii() for row in lines):
        raise ValueError("STB_FIXED_WIDTH_LAYOUT_CHANGED")
    # These byte slices are defined by the official 2024 STB reference guide,
    # Table 4-6, positions are one-based/inclusive in the original PDF.
    # Do NOT decode the potentially masked freight-revenue columns 55-63.
    fields={"waybill_date":(0,6),"carloads":(10,14),"stcc":(35,40),
            "billed_weight_tons":(40,47),"actual_weight_tons":(47,54),
            "origin_bea":(103,106),"destination_bea":(125,128)}
    parsed=[]
    for line in lines:
        row=line[:-2]
        rec={name:row[start:end].decode("ascii") for name,(start,end) in fields.items()}
        if any(not value.isdecimal() for value in rec.values()):
            raise ValueError("STB_UNEXPECTED_SOURCE_FIELD_ENCODING")
        if int(rec["carloads"])<1:
            raise ValueError("STB_IMPOSSIBLE_CARLOAD_COUNT")
        parsed.append(rec)
    if parsed[0]["waybill_date"]!="041118" or parsed[0]["stcc"]!="48105":
        raise ValueError("STB_SOURCE_LAYOUT_REFERENCE_MISMATCH")
    if m["source_zip"]!="https://www.stb.gov/wp-content/uploads/PublicUseWaybillSample2024.zip" or m["record_width"]!=247:
        raise ValueError("STB_UNTRUSTED_METADATA")
    return {"scope":"STB_2024_PUBLIC_USE_WAYBILL_FIXED_WIDTH_PREFIX_ONLY","original_public_records":100,
        "source_archive_fully_verified":False,"fixed_width_layout_validated":True,"official_2024_guide_field_layout_checked":True,
        "first_waybill_date_raw":parsed[0]["waybill_date"],
        "first_stcc_raw":parsed[0]["stcc"],"waybill_date_year_interpretation":"UNVERIFIED",
        "rate_field_interpreted":False,"revenue_may_be_masked":True,"unweighted_nonrepresentative_prefix":True,
        "real_customer_invoice_count":0,"real_recovery_cents":0,"commercial_claim_clearance":"NOT_ESTABLISHED"}
if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True))
