#!/usr/bin/env python3
"""Export TiC observations as benchmark-only PayerRecovery comparison data.

This intentionally does NOT emit recoveryworks.branches.payer_csv rate input,
because TiC public rates are not automatically the provider's controlling
contract. The export makes that boundary explicit.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


FIELDS = [
    "Reporting_Entity",
    "NPI",
    "TIN_Type",
    "TIN_Value",
    "Provider_Business_Name",
    "Billing_Code_Type",
    "Billing_Code",
    "Negotiated_Rate",
    "Negotiated_Type",
    "Setting",
    "Billing_Class",
    "Service_Codes",
    "Modifiers",
    "Expiration_Date",
    "Source_URL",
    "Source_SHA256",
    "Source_Locator",
    "Benchmark_Only",
    "Verified_Controlling_Rate",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--npi", action="append", default=[])
    p.add_argument("--billing-code", action="append", default=[])
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    clauses = []
    params = []
    if args.npi:
        marks = ",".join("?" for _ in args.npi)
        clauses.append(f"npi IN ({marks})")
        params.extend(args.npi)
    if args.billing_code:
        marks = ",".join("?" for _ in args.billing_code)
        clauses.append(f"billing_code IN ({marks})")
        params.extend([x.upper() for x in args.billing_code])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""

    rows = conn.execute(
        """SELECT * FROM payer_rate_benchmark_ledger""" + where +
        """ ORDER BY npi,billing_code,negotiated_rate,expiration_date""",
        params,
    ).fetchall()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "Reporting_Entity": row["reporting_entity_name"],
                "NPI": row["npi"],
                "TIN_Type": row["tin_type"],
                "TIN_Value": row["tin_value"],
                "Provider_Business_Name": row["business_name"],
                "Billing_Code_Type": row["billing_code_type"],
                "Billing_Code": row["billing_code"],
                "Negotiated_Rate": row["negotiated_rate"],
                "Negotiated_Type": row["negotiated_type"],
                "Setting": row["setting"],
                "Billing_Class": row["billing_class"],
                "Service_Codes": row["service_code_json"],
                "Modifiers": row["billing_code_modifier_json"],
                "Expiration_Date": row["expiration_date"],
                "Source_URL": row["rate_file_url"],
                "Source_SHA256": row["rate_file_sha256"],
                "Source_Locator": row["source_locator"],
                "Benchmark_Only": "true",
                "Verified_Controlling_Rate": "false",
            })
    conn.close()
    print(f"wrote {len(rows)} benchmark rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
