"""Bounded original Census CFS PUMS sample integrity; not representative."""
import csv
import json
from hashlib import sha256
from pathlib import Path
from decimal import Decimal, InvalidOperation
import re
HERE=Path(__file__).resolve().parent
COLUMNS=("SHIPMT_ID","ORIG_STATE","ORIG_MA","ORIG_CFS_AREA","DEST_STATE","DEST_MA","DEST_CFS_AREA","SECTOR","SCTG","MODE","SHIPMT_VALUE","SHIPMT_WGHT","SHIPMT_DIST_GC","TEMP_CNTL_YN","EXPORT_YN","EXPORT_CNTRY","HAZMAT","WGT_FACTOR")
def report():
    p=HERE/"fixtures/public_census_cfs2022_pums_first100.csv"
    m=json.loads((HERE/"fixtures/public_census_cfs2022_pums_first100_manifest.json").read_text())
    if p.is_symlink() or not p.is_file() or p.stat().st_size>16000:
        raise ValueError("CFS_UNTRUSTED_SAMPLE")
    raw=p.read_bytes()
    if (len(raw)!=m.get("fixture_bytes") or
        sha256(raw).hexdigest()!=m.get("fixture_sha256")):
        raise ValueError("CFS_ORIGINAL_ROW_BYTES_CHANGED")
    with p.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if tuple(reader.fieldnames or ())!=COLUMNS:raise ValueError("CFS_INVALID_SCHEMA")
        rows=list(reader)
    if len(rows)!=100 or any(set(r)!=set(COLUMNS) or r["SHIPMT_ID"]!=f"{i:08d}" or any(v is None for v in r.values()) for i,r in enumerate(rows,1)):
        raise ValueError("CFS_NOT_EXACT_PREFIX")
    # The CFS 2022 PUMS Data Users Guide defines WGT_FACTOR as a
    # survey tabulation factor rounded to one tenth, with the disclosed
    # maximum top-coded at 3,588,000. It is NOT permission to multiply
    # a nonrandom prefix into a national rate, invoice or savings claim.
    cap=Decimal("3588000")
    if (m.get("official_users_guide")!=
        "https://www2.census.gov/programs-surveys/cfs/datasets/2022/cfs_2022_pums_users_guide.pdf"
        or m.get("original_2022_pums_source_population",{}).get("shipment_records")!=37576546
        or m.get("source_ordering")!="PUBLISHER_RANDOMLY_SORTED_SHIPMENT_IDS"
        or m.get("weight_policy",{}).get("official_weight_cap")!="3588000"
        or m.get("weight_policy",{}).get("per_sample_100_row_extrapolation_authorized") is not False
        or m.get("disclosure_policy",{}).get("privacy_modified_values_not_invoices") is not True):
        raise ValueError("CFS_GUIDE_OR_INFERENCE_POLICY_CHANGED")
    for row in rows:
        factor=row["WGT_FACTOR"]
        if (not re.fullmatch(r"[0-9]+(?:\.[0-9])?",factor)
            or not re.fullmatch(r"[0-9]+",row["SHIPMT_VALUE"])
            or not re.fullmatch(r"[0-9]+",row["SHIPMT_WGHT"])):
            raise ValueError("CFS_UNEXPECTED_NUMERIC_PRECISION")
        try:
            weight=Decimal(factor)
            if not weight.is_finite() or weight<=0 or weight>cap:
                raise ValueError("CFS_INVALID_TABULATION_FACTOR")
            if Decimal(row["SHIPMT_VALUE"])<0 or Decimal(row["SHIPMT_WGHT"])<0:
                raise ValueError("CFS_INVALID_WEIGHT_OR_VALUE")
        except InvalidOperation as exc:
            raise ValueError("CFS_INVALID_NUMERIC_FIELD") from exc
    if m["first_complete_rows"]!=100 or m["compressed_archive_bytes"]!=677530696:
        raise ValueError("CFS_INVALID_MANIFEST")
    return {"source":"CENSUS_2022_CFS_PUBLIC_USE_MICRODATA","sample_rows":100,
        "method":"FIRST_100_OF_PUBLISHER_RANDOMIZED_RECORD_ORDER_NO_POPULATION_ESTIMATION",
        "full_source_downloaded":False,
        "shipment_value_is_not_freight_charge":True,"national_estimate_authorized":False,
        "official_CFS_2022_PUMS_guide_applied":True,
        "full_source_record_count_from_guide_only":37576546,
        "actual_original_full_source_record_count_verified":False,
        "disclosure_modified_values_not_original_invoices":True,
        "sample_not_representative_or_weighted":True,
        "publisher_ranks_shipment_ids_after_random_record_sort":True,
        "sample_prefix_is_not_separately_designed_population_estimator":True,
        "WGT_FACTOR_meaning_documented_but_not_used_for_population_extrapolation":True,
        "published_official_CFS_tables_preferred_for_population_estimates":True,
        "validated_invoice_count":0,"verified_recoveries_cents":0}
if __name__=="__main__":print(json.dumps(report(),sort_keys=True))
