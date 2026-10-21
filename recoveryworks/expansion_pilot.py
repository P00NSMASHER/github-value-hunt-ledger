"""Private intake kits for staged RETALLY expansion; never commercial signoff."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from .cli import write_private_json
from .private_io import atomic_private_write
from .runner import run_scan360_config

# Exact adapter schemas. Blank sources deliberately contain no sample claims.
SOURCES = {
    "ap": {
        "payments_csv": ("Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date", "payment_source_verified"),
        "obligations_csv": ("Vendor,Invoice_Number,Amount,Invoice_Date", "obligation_source_verified"),
        "vendor_statements_csv": ("Vendor,Invoice_Number,Balance,Statement_Date", "vendor_statement_source_verified"),
    },
    "warranty_credit": {
        "entitlements_csv": ("Entitlement_ID,Client_ID,Supplier_ID,Reference_ID,Credit_Category,Entitled_Amount,Effective_Date,Entitlement_Basis,Entitlement_Reviewer_ID", "entitlement_source_verified"),
        "settlements_csv": ("Settlement_ID,Entitlement_ID,Amount_Received,Settlement_Date,Settlement_Kind", "settlement_source_verified"),
    },
    "procurement": {
        "invoice_lines_csv": ("Invoice_Line_ID,Invoice_ID,Purchaser_ID,Supplier_ID,PO_Line_ID,SKU,Invoice_Date,Invoiced_Quantity,Actual_Line_Amount", "invoice_source_verified"),
        "authorities_csv": ("Authority_ID,Supplier_ID,PO_Line_ID,SKU,Effective_From,Effective_To,Contracted_Unit_Price,Price_Basis", "authority_source_verified"),
        "quantities_csv": ("Invoice_Line_ID,Approved_Billable_Quantity,Quantity_Basis", "quantity_source_verified"),
    },
    "rebate": {
        "programs_json": (None, "program_source_verified"),
        "purchases_csv": ("Purchase_ID,Supplier,Program_ID,Purchase_Date,Quantity,Net_Spend", "purchase_source_verified"),
        "settlements_csv": ("Settlement_ID,Supplier,Program_ID,Amount_Received,Settlement_Date", "settlement_source_verified"),
    },
    "parcel": {
        "charges_csv": ("Shipment_ID,Invoice_ID,Shipper_ID,Carrier_ID,Ship_Date,Service_Code,Zone,Billed_Weight,Actual_Total", "charge_source_verified"),
        "assessments_csv": ("Assessment_ID,Shipment_ID,Carrier_ID,Ship_Date,Service_Code,Zone,Billed_Weight,Expected_Total,Rate_Basis,Rate_Snapshot_Date,Rate_Reviewer_ID", "assessment_source_verified"),
    },
    "utility": {
        "bills_csv": ("Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,Billed_kWh,Billed_Demand_kW,Billed_rkVA,Days_Used,Service_Start,Service_End", "bill_source_verified"),
        "tariffs_json": (None, "tariff_source_verified"),
    },
}
STAGES = {"1": ("ap", "warranty_credit"), "2": ("procurement", "rebate"), "3": ("parcel", "utility")}


def create_kit(destination: Path, client_id: str, stage: str) -> Path:
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("client_id is required")
    branches = STAGES[stage]
    # A new directory is mandatory: never overwrite source evidence or an old run.
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    config = {"client_id": client_id.strip(), "currency": "USD"}
    for branch in branches:
        job = {}
        for key, (headers, flag) in SOURCES[branch].items():
            extension = "csv" if headers else "json"
            filename = f"{branch}_{key}.{extension}"
            atomic_private_write(destination / filename, ((headers + "\n") if headers else "[]\n").encode())
            job[key] = filename
            job[flag] = False
        if branch == "utility":
            job["utility_id"] = "REPLACE_WITH_ACTUAL_UTILITY"
        if branch in {"ap", "utility"}:
            job["default_effective_from"] = ""
        config[branch] = job
    write_private_json(destination / "scan.json", config)
    write_private_json(destination / "pilot_status.json", {
        "client_id": client_id.strip(), "stage": stage,
        "status": "AWAITING_AUTHORIZED_CUSTOMER_EVIDENCE",
        "commercially_validated": False,
        "note": "Static intake status, not a computed readiness certificate. Tests are not customer recoveries.",
    })
    atomic_private_write(destination / "overlap_review.csv", (
        "Finding_ID,Economic_Loss_ID,Related_Finding_ID,Decision,Reason,Reviewer,Evidence_Reference\n"
    ).encode())
    atomic_private_write(destination / "economics.csv", (
        "Branch,Period,Net_Realized_Recovery_Cents,Actual_Fee_Cents,Delivery_Minutes,"
        "Labor_Cost_Cents,Other_Cost_Cents,Posting_Evidence,Reversal_Evidence\n"
    ).encode())
    return destination / "scan.json"


def preflight(config: dict, root: Path) -> list[str]:
    """Check intake completeness only; loaders retain all semantic proof checks."""
    errors = []
    active = [branch for branch in SOURCES if branch in config]
    if not active:
        errors.append("No expansion branches configured")
    for branch in active:
        job = config[branch]
        if not isinstance(job, dict):
            errors.append(f"{branch}: expected one intake job object")
            continue
        if branch in {"ap", "utility"}:
            try:
                date.fromisoformat(job.get("default_effective_from", ""))
            except (TypeError, ValueError):
                errors.append(f"{branch}: supply evidence-supported default_effective_from (YYYY-MM-DD)")
        if branch == "utility" and job.get("utility_id") in {None, "", "REPLACE_WITH_ACTUAL_UTILITY"}:
            errors.append("utility: supply actual utility_id")
        for key, (headers, flag) in SOURCES[branch].items():
            if type(job.get(flag, False)) is not bool:
                errors.append(f"{branch}.{flag}: must be boolean")
            value = job.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{branch}.{key}: missing source")
                continue
            path = root / value
            try:
                if headers:
                    with path.open(encoding="utf-8-sig", newline="") as handle:
                        reader = csv.DictReader(handle)
                        missing = set(headers.split(",")) - set(reader.fieldnames or [])
                        if missing:
                            errors.append(f"{branch}.{key}: missing columns {','.join(sorted(missing))}")
                        if not any(any(str(v or '').strip() for v in row.values()) for row in reader):
                            errors.append(f"{branch}.{key}: no evidence rows")
                else:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        data = data.get("programs" if branch == "rebate" else "tariffs")
                    if not isinstance(data, list) or not data:
                        errors.append(f"{branch}.{key}: no authority records")
            except (OSError, ValueError, csv.Error):
                errors.append(f"{branch}.{key}: unreadable source")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--directory", required=True, type=Path)
    init.add_argument("--client-id", required=True)
    init.add_argument("--stage", choices=STAGES, required=True)
    for command in ("check", "run"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--config", required=True, type=Path)
        if command == "run":
            command_parser.add_argument("--state", required=True, type=Path)
            command_parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "init":
        create_kit(args.directory, args.client_id, args.stage)
        print("Private intake kit created; customer validation remains pending.")
        return 0
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    errors = preflight(config, args.config.parent)
    if errors:
        print(json.dumps({"intake_complete": False, "errors": errors}, indent=2))
        return 2
    if args.command == "check":
        print("Intake populated; source authenticity, entitlement and recovery remain unverified.")
        return 0
    result = run_scan360_config(config, state_path=args.state, base_dir=args.config.parent)
    payload = result.as_dict()
    payload["expansion_pilot"] = {
        "commercially_validated": False,
        "cross_branch_overlap_review": "REQUIRED_BEFORE_QUOTING_COMBINED_RECOVERY",
        "note": "Branch totals may overlap. Scan completion is not recovery or launch approval.",
    }
    write_private_json(args.report, payload)
    print(f"Pilot scan recorded; exceptions={len(result.exceptions)}; overlap review required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
