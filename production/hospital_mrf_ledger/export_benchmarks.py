#!/usr/bin/env python3
"""Export Hospital Price Transparency observations as benchmark/context evidence."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


FIELDS = [
    "Hospital_Name","Location_Name","Hospital_Address","Type_2_NPI","MRF_Date",
    "CMS_Template_Version","Code_Type","Code","Description","Setting","Modifiers",
    "Gross_Charge","Discounted_Cash","Minimum_Negotiated","Maximum_Negotiated",
    "Payer_Name","Plan_Name","Methodology","Negotiated_Dollar","Negotiated_Percentage",
    "Negotiated_Algorithm","Median_Allowed_Amount","Allowed_Amount_P10",
    "Allowed_Amount_P90","Allowed_Amount_Count","Source_URL","Source_SHA256",
    "Source_Locator","Benchmark_Only","Verified_Controlling_Rate",
    "Verified_Claim_Applicability"
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--billing-code", action="append", default=[])
    p.add_argument("--payer", action="append", default=[])
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    clauses = []
    params = []
    if args.billing_code:
        marks = ",".join("?" for _ in args.billing_code)
        clauses.append(f"code IN ({marks})")
        params.extend([x.strip().upper() for x in args.billing_code])
    if args.payer:
        marks = ",".join("?" for _ in args.payer)
        clauses.append(f"LOWER(payer_name) IN ({marks})")
        params.extend([x.strip().lower() for x in args.payer])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""

    rows = conn.execute(
        "SELECT * FROM hospital_rate_benchmark_ledger" + where +
        " ORDER BY hospital_name,code_type,code,payer_name,plan_name",
        params,
    ).fetchall()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "Hospital_Name": r["hospital_name"],
                "Location_Name": r["location_name"],
                "Hospital_Address": r["hospital_address"],
                "Type_2_NPI": r["type_2_npi"],
                "MRF_Date": r["last_updated_on"],
                "CMS_Template_Version": r["schema_version"],
                "Code_Type": r["code_type"],
                "Code": r["code"],
                "Description": r["description"],
                "Setting": r["setting"],
                "Modifiers": r["modifier_json"],
                "Gross_Charge": r["gross_charge"],
                "Discounted_Cash": r["discounted_cash"],
                "Minimum_Negotiated": r["minimum_negotiated"],
                "Maximum_Negotiated": r["maximum_negotiated"],
                "Payer_Name": r["payer_name"],
                "Plan_Name": r["plan_name"],
                "Methodology": r["methodology"],
                "Negotiated_Dollar": r["standard_charge_dollar"],
                "Negotiated_Percentage": r["standard_charge_percentage"],
                "Negotiated_Algorithm": r["standard_charge_algorithm"],
                "Median_Allowed_Amount": r["median_amount"],
                "Allowed_Amount_P10": r["percentile_10"],
                "Allowed_Amount_P90": r["percentile_90"],
                "Allowed_Amount_Count": r["allowed_amount_count"],
                "Source_URL": r["mrf_url"],
                "Source_SHA256": r["mrf_sha256"],
                "Source_Locator": r["source_locator"],
                "Benchmark_Only": "true",
                "Verified_Controlling_Rate": "false",
                "Verified_Claim_Applicability": "false",
            })
    conn.close()
    print(f"wrote {len(rows)} benchmark rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
