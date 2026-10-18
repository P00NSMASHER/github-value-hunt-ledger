"""Bounded original Census CFS PUMS sample integrity; not representative."""
import csv
import json
from pathlib import Path
from decimal import Decimal
HERE=Path(__file__).resolve().parent
COLUMNS=("SHIPMT_ID","ORIG_STATE","ORIG_MA","ORIG_CFS_AREA","DEST_STATE","DEST_MA","DEST_CFS_AREA","SECTOR","SCTG","MODE","SHIPMT_VALUE","SHIPMT_WGHT","SHIPMT_DIST_GC","TEMP_CNTL_YN","EXPORT_YN","EXPORT_CNTRY","HAZMAT","WGT_FACTOR")
def report():
    p=HERE/"fixtures/public_census_cfs2022_pums_first100.csv"
    m=json.loads((HERE/"fixtures/public_census_cfs2022_pums_first100_manifest.json").read_text())
    if p.is_symlink() or not p.is_file() or p.stat().st_size>16000:
        raise ValueError("CFS_UNTRUSTED_SAMPLE")
    with p.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if tuple(reader.fieldnames or ())!=COLUMNS:raise ValueError("CFS_INVALID_SCHEMA")
        rows=list(reader)
    if len(rows)!=100 or any(set(r)!=set(COLUMNS) or r["SHIPMT_ID"]!=f"{i:08d}" or any(v is None for v in r.values()) for i,r in enumerate(rows,1)):
        raise ValueError("CFS_NOT_EXACT_PREFIX")
    if any(Decimal(r["WGT_FACTOR"])<=0 or Decimal(r["SHIPMT_VALUE"])<0 or Decimal(r["SHIPMT_WGHT"])<0 for r in rows):
        raise ValueError("CFS_INVALID_WEIGHT_OR_VALUE")
    if m["first_complete_rows"]!=100 or m["compressed_archive_bytes"]!=677530696:
        raise ValueError("CFS_INVALID_MANIFEST")
    return {"source":"CENSUS_2022_CFS_PUBLIC_USE_MICRODATA","sample_rows":100,
        "method":"NONRANDOM_EXACT_FILE_PREFIX","full_source_downloaded":False,
        "shipment_value_is_not_freight_charge":True,"national_estimate_authorized":False,
        "validated_invoice_count":0,"verified_recoveries_cents":0}
if __name__=="__main__":print(json.dumps(report(),sort_keys=True))
