"""Original published Census 2022 CFS PUMS Maryland worked example.

The full 37.6-million-row PUMS was NOT downloaded or independently replayed
here. Only the publisher's authoritative example and GVF are checked.
This must never become a customer freight-rate or recovery calculation.
"""
from __future__ import annotations

import json
from math import exp, log, isfinite
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"fixtures/public_cfs2022_official_maryland_example.json"

EXPECTED={
    "source":"US_CENSUS_2022_CFS_PUMS_USERS_GUIDE_OFFICIAL_WORKED_EXAMPLE",
    "survey_year":2022,
    "published_example_pums_domain_records":612317,
    "published_example_weighted_goods_value_usd":"198598788295",
    "published_example_coefficient_of_variation_percent":"9.74",
    "published_example_total_value_gvf_coefficients":{
        "a":"3.905","b":"0.011","c":"-0.010",
    },
}
ALLOWED_SOURCE_KEYS=frozenset(['schema_version','source','original_guide_url','source_location','survey_year','shipment_domain','published_example_pums_domain_records','published_example_weighted_goods_value_usd','published_example_total_value_gvf_coefficients','published_example_coefficient_of_variation_percent','weighting_rule','variance_rule','never_interchange_with','actual_source_rows_downloaded_for_this_example','this_is_official_published_example_not_locally_recomputed_from_full_file','ordinary_100_row_prefix_permitted_as_substitute','full_census_pums_sha_verified','own_customer_invoices_seen','real_recoveries_cents'])
NONCLAIMS={
    "ordinary_100_row_prefix_permitted_as_substitute":False,
    "full_census_pums_sha_verified":False,
    "own_customer_invoices_seen":0,
    "real_recoveries_cents":0,
}

def verified_published_example()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>8192:
        raise ValueError("CFS_MD_EXAMPLE_UNTRUSTED_SOURCE")
    try:
        x=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        raise ValueError("CFS_MD_EXAMPLE_INVALID_JSON") from e
    if (type(x) is not dict or frozenset(x)!=ALLOWED_SOURCE_KEYS
        or x.get("schema_version")!=1
        or x.get("original_guide_url")!="https://www2.census.gov/programs-surveys/cfs/datasets/2022/cfs_2022_pums_users_guide.pdf"
        or x.get("shipment_domain")!="ORIG_STATE = 24 (all Maryland-origin shipments in CFS-covered establishments, all destinations, all modes)"
        or not all(x.get(k)==v for k,v in EXPECTED.items())
        or not all(x.get(k)==v for k,v in NONCLAIMS.items())
        or x.get("this_is_official_published_example_not_locally_recomputed_from_full_file") is not True
        or x.get("actual_source_rows_downloaded_for_this_example")!=0):
        raise ValueError("CFS_MD_EXAMPLE_SOURCE_OR_CLAIM_CHANGED")
    n=EXPECTED["published_example_pums_domain_records"]
    co=EXPECTED["published_example_total_value_gvf_coefficients"]
    ln=log(n)
    cv=exp(float(co["a"])+float(co["b"])*ln+float(co["c"])*ln*ln)
    if not isfinite(cv) or f"{cv:.2f}"!=EXPECTED["published_example_coefficient_of_variation_percent"]:
        raise ValueError("CFS_MD_EXAMPLE_VARIANCE_REPRODUCTION_FAILED")
    return {
        "scope":"PUBLISHER_VERIFIED_MD_2022_CFS_GOODS_VALUE_EXAMPLE_ONLY",
        "publisher":"US Census Bureau",
        "pums_md_origin_unweighted_record_count":n,
        "census_published_weighted_goods_value_usd":x["published_example_weighted_goods_value_usd"],
        "census_published_gvf_cv_percent":f"{cv:.2f}",
        "country_or_route_total_freight_spend":None,
        "underlying_full_37576546_source_records_locally_recomputed":False,
        "100_prefix_rows_used_to_make_estimate":False,
        "census_estimate_not_equal_faf6_md_pa_lane":True,
        "no_original_customer_tariff_invoice_or_recoveries":True,
        "commercial_claim_clearance":"NOT_ESTABLISHED",
    }

if __name__=="__main__":
    print(json.dumps(verified_published_example(),indent=2,sort_keys=True))
