"""100 unique fictional customer datasets against RETALLY's actual freight engine.

Source-only adversarial QA. No real customer information, contacts, provider
actions, credentials, bank confirmations, actual carrier communications, fees
or production state. All approvals and carrier actions in the existing
rehearsal are simulated in-memory and *not commercially valid*.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import csv
import io
import json
import os
import random
import subprocess
import sys
import traceback
import zipfile

from freight import synthetic_rehearsal as rehearsal
from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.priority4_adversarial_lab import make_plan, execute_case

SOURCE_BASELINE_SHA = "c2a55abca49f04d35ab438c2012fde9a309d7d2f"
SOURCE_SHA = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
SEED = 20261022
PERSONAS = (
    "regional-hospital", "pharmaceutical-distributor",
    "importer-wholesaler", "frozen-food-supplier",
    "automotive-parts-maker", "government-contractor",
    "warehouse-3pl", "small-ecommerce-store",
    "construction-materials", "disaster-relief-operator",
    "retail-franchise", "agricultural-cooperative",
    "electronics-recycler", "machinery-exporter",
    "port-forwarder", "medical-supply-chain",
    "fashion-returns-network", "industrial-maintenance",
    "consumer-goods-distributor", "specialty-chemicals-hauler",
)
STRESSORS = (
    "carrier-appeal-and-short-credit",
    "bank-return-after-partial-settlement",
    "affiliate-payment-redirection-demand",
    "shipment-weight-document-conflict",
    "customer-disputes-audit-findings",
    "two-carrier-shared-invoice-reference",
    "carrier-bankruptcy-with-time-bar",
    "lost-remittance-and-delayed-credit",
    "contract-amendment-overlap",
    "attempted-duplicate-source-replay",
    "customer-demands-guaranteed-recovery",
    "currency-and-fx-identity-mismatch",
    "incumbent-recovered-credit-exclusion",
    "unauthorized-data-export-request",
    "carrier-denial-plus-missing-tariff",
    "overbilled-accessorial-claims",
    "return-while-claim-under-review",
    "retention-exception-demand",
    "split-credit-across-many-invoices",
    "reversal-after-report-publication",
)
F1_CODES = ("DETENTION", "REWEIGH", "STORAGE", "LIFTGATE",
            "REDELIVERY", "DRAYAGE", "FUEL_ADJUSTMENT", "ACCESSORIAL_A")
F2_CODES = ("ACCESSORIAL", "OVERSIZE", "DIM_WEIGHT", "LAYOVER",
            "FUEL_SURCHARGE", "RESIDENTIAL", "ADDRESS_CORRECTION", "ACCESSORIAL_B")
F3_CODES = ("MISC", "SERVICE_ADJUSTMENT", "CUSTOMS_FEE", "MANUAL_CHARGE")
MODELS = ("FIXED", "PER_UNIT", "INCLUDED")
FAULTS = (
    "DUPLICATE_CHARGE_ID",
    "NONCANONICAL_NEGATIVE_MONEY",
    "INVALID_SERVICE_DATE",
    "UNTRUSTED_CURRENCY",
    "CARRIER_ID_MISMATCH",
    "MISSING_CONTROLLING_TARIFF",
    "COMPETING_CONTROLLING_TARIFFS",
    "FORGED_TARIFF_DOCUMENT_SHA",
    "IMPERSONATED_BUYER_CSV_COLUMN",
    "EXPIRED_TARIFF",
)
INVOICE_COLUMNS = (
    "invoice_id", "shipment_id", "customer_id", "carrier_id", "currency",
    "charge_id", "charge_code", "service_date", "quantity_units", "billed_cents",
)
RULE_COLUMNS = (
    "charge_code", "pricing_model", "effective_from", "effective_to",
    "fixed_cents", "unit_rate_cents",
)
SETTLEMENT_COLUMNS = (
    "event_id", "reference", "payer_id", "payee_id", "currency",
    "amount_cents", "booked_at", "source_kind",
)
RETURN_COLUMNS = (
    "counter_id", "original_event_id", "currency", "amount_cents",
    "observed_at", "source_kind",
)


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def csv_bytes(columns, rows) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def pricing(model: str, quantity: int, rng: random.Random) -> tuple[dict, int]:
    if model == "INCLUDED":
        return {"pricing_model": model, "fixed_cents": "", "unit_rate_cents": ""}, 0
    if model == "FIXED":
        cents = rng.randrange(1000, 20000)
        return {"pricing_model": model, "fixed_cents": str(cents),
                "unit_rate_cents": ""}, cents
    rate = rng.randrange(350, 4600)
    return {"pricing_model": model, "fixed_cents": "",
            "unit_rate_cents": str(rate)}, rate * quantity


@dataclass(frozen=True)
class SyntheticDataSet:
    number: int
    buyer: str
    business_unit: str
    persona: str
    stressor: str
    invoices: tuple[dict, ...]
    verified_rules: tuple[dict, ...]
    unverified_rules: tuple[dict, ...]
    settlement_rows: tuple[dict, ...]
    return_rows: tuple[dict, ...]
    credit_one: int
    credit_two: int
    credit_return: int
    finding_one: int
    finding_two: int
    fault: str
    mode_label: str
    source_hash: str


def construct(index: int) -> SyntheticDataSet:
    if type(index) is not int or not 0 <= index < 100:
        raise ValueError("expected exactly one unique dataset index from 0..99")
    rng = random.Random(SEED + index * 9227)
    buyer = f"SYNTHETIC-BUYER-{index:03d}"
    unit = f"BU-{index % 11:02d}"
    c1, c2, c3 = (
        F1_CODES[(index + index // 7) % len(F1_CODES)],
        F2_CODES[(index * 3 + index // 6) % len(F2_CODES)],
        F3_CODES[(index * 5 + index // 9) % len(F3_CODES)],
    )
    models = (
        MODELS[index % 3],
        MODELS[(index // 3) % 3],
        MODELS[(index // 9) % 3],
    )
    qty = [rng.randint(1, 13), rng.randint(1, 17), rng.randint(1, 9)]
    p1, expect1 = pricing(models[0], qty[0], rng)
    p2, expect2 = pricing(models[1], qty[1], rng)
    p3, expect3 = pricing(models[2], qty[2], rng)
    credit1 = rng.randrange(1000, 9500)
    credit2 = rng.randrange(1500, 11000)
    markup1 = credit1 + rng.randrange(100, 4000)
    markup2 = credit2
    markup3 = rng.randrange(100, 8000)
    # Some deliberate repeat-500 observations establish a positive control;
    # most customers report different actual returned amounts.
    amount_returned = 500 if index % 7 == 0 else rng.randrange(1, credit1)
    date = f"2026-09-{10 + index % 10:02d}"
    invoice_ids = [f"INV-{index:03d}-{j}" for j in range(1, 4)]
    invoices = []
    for j, (code, quantity, expected, markup) in enumerate(
        zip((c1, c2, c3), qty, (expect1, expect2, expect3),
            (markup1, markup2, markup3), strict=True), 1
    ):
        invoices.append({
            "invoice_id": invoice_ids[j-1],
            "shipment_id": f"SHP-{index:03d}-{j}-{rng.randrange(100, 999)}",
            "customer_id": "cust", "carrier_id": "carrier", "currency": "USD",
            "charge_id": f"charge-{j}", "charge_code": code,
            "service_date": date, "quantity_units": str(quantity),
            "billed_cents": str(expected + markup),
        })
    def rule(code, options):
        return {
            "charge_code": code, "pricing_model": options["pricing_model"],
            "effective_from": "2026-09-01", "effective_to": "2026-09-30",
            "fixed_cents": options["fixed_cents"],
            "unit_rate_cents": options["unit_rate_cents"],
        }
    verified = (rule(c1, p1), rule(c2, p2))
    unverified = (rule(c3, p3),)
    settlements = (
        {"event_id": "e-1", "reference": invoice_ids[0], "payer_id": "carrier",
         "payee_id": "cust", "currency": "USD", "amount_cents": str(credit1),
         "booked_at": "2026-09-21T10:00:00Z", "source_kind": "CREDIT-MEMO"},
        {"event_id": "e-2", "reference": invoice_ids[1], "payer_id": "carrier",
         "payee_id": "cust", "currency": "USD", "amount_cents": str(credit2),
         "booked_at": "2026-09-21T10:00:00Z", "source_kind": "CREDIT-MEMO"},
    )
    returns = ({
        "counter_id": "return-1", "original_event_id": "e-1",
        "currency": "USD", "amount_cents": str(amount_returned),
        "observed_at": "2026-09-22T10:00:00Z",
        "source_kind": "SYNTHETIC-BANK-RETURN-NOT-VERIFIED",
    },)
    # This is a source manifest, not independent document authentication.
    fixture_body = {
        "index": index, "buyer": buyer, "unit": unit, "invoices": invoices,
        "verified": verified, "unverified": unverified,
        "settlements": settlements, "returns": returns,
        "persona": PERSONAS[index % len(PERSONAS)],
        "stressor": STRESSORS[(index * 7 + index // 5) % len(STRESSORS)],
    }
    digest = sha(json.dumps(fixture_body, sort_keys=True).encode("utf-8"))
    return SyntheticDataSet(
        number=index, buyer=buyer, business_unit=unit,
        persona=PERSONAS[index % len(PERSONAS)],
        stressor=STRESSORS[(index * 7 + index // 5) % len(STRESSORS)],
        invoices=tuple(invoices), verified_rules=verified,
        unverified_rules=unverified, settlement_rows=settlements,
        return_rows=returns, credit_one=credit1, credit_two=credit2,
        credit_return=amount_returned, finding_one=markup1,
        finding_two=markup2, fault=FAULTS[index % len(FAULTS)],
        mode_label=("LTL", "PARCEL", "TL", "INTERMODAL", "AIR", "OCEAN")[index % 6],
        source_hash=digest,
    )


def generate_files(s: SyntheticDataSet) -> dict[str, bytes]:
    return {
        "invoices.csv": csv_bytes(INVOICE_COLUMNS, s.invoices),
        "verified_contracts.csv": csv_bytes(RULE_COLUMNS, s.verified_rules),
        "unverified_contracts.csv": csv_bytes(RULE_COLUMNS, s.unverified_rules),
        "carrier_credits.csv": csv_bytes(SETTLEMENT_COLUMNS, s.settlement_rows),
        "carrier_returns.csv": csv_bytes(RETURN_COLUMNS, s.return_rows),
        "scenario_metadata.json": (
            json.dumps({
                "dataset": s.number, "persona": s.persona, "stressor": s.stressor,
                "buyer": s.buyer, "business_unit": s.business_unit,
                "declared_carriage_mode_context": s.mode_label,
                "audit_rate_scope": "normalized USD charge-level only",
                "credit_one_cents": s.credit_one,
                "credit_two_cents": s.credit_two,
                "returned_cents": s.credit_return,
                "simulated_external_action_only": True,
                "no_customer_personal_data": True,
                "source_hash": s.source_hash,
            }, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
    }


def rules_for(s: SyntheticDataSet, files: dict[str, bytes], *, poisoned=False, verified_override=None):
    doc = f"SIMULATED-ONLY verified authority for dataset {s.number}".encode()
    extra = f"SIMULATED-ONLY candidate addendum for dataset {s.number}".encode()
    return (
        RuleCSVInput(
            filename="verified_contracts.csv", data=files["verified_contracts.csv"],
            customer_id="cust", carrier_id="carrier", currency="USD",
            authority_document_id=f"SYN-AUTH-{s.number}",
            source_document_sha256=("0"*64 if poisoned else None),
            source_document_data=doc,
            verified_controlling_authority=(
                True if verified_override is None else verified_override
            ),
        ),
        RuleCSVInput(
            filename="unverified_contracts.csv", data=files["unverified_contracts.csv"],
            customer_id="cust", carrier_id="carrier", currency="USD",
            authority_document_id=f"SYN-PENDING-{s.number}",
            source_document_sha256=None, source_document_data=extra,
            verified_controlling_authority=False,
        ),
    )


def audit_fault_probe(s: SyntheticDataSet, files: dict[str, bytes]) -> dict:
    """One fault per distinct dataset. A safe HOLD counts as correct defense."""
    rows = [dict(x) for x in s.invoices]
    rules = [dict(x) for x in s.verified_rules]
    filename = "invoices.csv"
    fake_source = False
    target = 0
    kind = s.fault
    expected = "BLOCKED"
    if kind == "DUPLICATE_CHARGE_ID":
        rows[-1]["charge_id"] = rows[0]["charge_id"]
    elif kind == "NONCANONICAL_NEGATIVE_MONEY":
        rows[0]["billed_cents"] = "-1800"
    elif kind == "INVALID_SERVICE_DATE":
        rows[0]["service_date"] = "2026-02-30"
    elif kind == "UNTRUSTED_CURRENCY":
        rows[1]["currency"] = "EUR"
        target, expected = 1, "NOT_VALIDATED"
    elif kind == "CARRIER_ID_MISMATCH":
        rows[0]["carrier_id"] = "SYN-OTHER-CARRIER"
        target, expected = 0, "NOT_VALIDATED"
    elif kind == "MISSING_CONTROLLING_TARIFF":
        rules.pop(0)
        target, expected = 0, "NOT_VALIDATED"
    elif kind == "COMPETING_CONTROLLING_TARIFFS":
        first = dict(rules[0])
        first.update({"pricing_model": "FIXED",
                      "fixed_cents": str(int(rows[0]["billed_cents"]) + 1),
                      "unit_rate_cents": ""})
        rules.append(first)
        target, expected = 0, "NOT_VALIDATED"
    elif kind == "FORGED_TARIFF_DOCUMENT_SHA":
        fake_source = True
    elif kind == "IMPERSONATED_BUYER_CSV_COLUMN":
        for row in rows:
            row["buyer_id"] = "SYN-IMPERSONATED"
    elif kind == "EXPIRED_TARIFF":
        rules[0]["effective_to"] = "2026-09-05"
        target, expected = 0, "NOT_VALIDATED"
    else:
        raise AssertionError("unrecognized fault")
    input_headers = INVOICE_COLUMNS + (
        ("buyer_id",) if kind == "IMPERSONATED_BUYER_CSV_COLUMN" else ()
    )
    tampered = csv_bytes(input_headers, rows)
    variant = dict(files)
    variant["verified_contracts.csv"] = csv_bytes(RULE_COLUMNS, rules)
    result = run_audit_workflow(
        invoice_filename=filename, invoice_data=tampered,
        buyer_id=s.buyer, business_unit=s.business_unit,
        selection_rule=f"SYN-FAULT-{s.number}",
        rule_inputs=rules_for(s, variant, poisoned=fake_source),
    )
    if expected == "BLOCKED":
        guarded = result.state == "BLOCKED" and result.artifacts is None
        interpretation = "reject malformed/forged source before any claims"
    else:
        guarded = result.state == "BLOCKED"
        if result.artifacts is not None:
            entry = next(
                d for d in result.artifacts.factory.derivations
                if d.charge_id == f"charge-{target+1}"
            )
            guarded = entry.decision != "VALIDATED"
        interpretation = "never validate charge without uniquely scoped authority"
    return {
        "fault": kind, "expected_control": expected, "actual_state": result.state,
        "failure_stage": result.stage if result.state == "BLOCKED" else None,
        "guard_pass": guarded, "interpretation": interpretation,
        "source_sha256": sha(tampered),
    }


def full_rehearsal(s: SyntheticDataSet, files: dict[str, bytes]) -> dict:
    # The original all-stages commercial rehearsal owns its own isolated
    # TemporaryDirectory and uses pure in-memory synthetic human-role evidence.
    with patch.multiple(
        rehearsal,
        BUYER=s.buyer, BU=s.business_unit,
        SCENARIO_ID=f"SYNTHETIC-CASE-{s.number:03d}",
        INVOICE_CSV=files["invoices.csv"],
        VERIFIED_RULES_CSV=files["verified_contracts.csv"],
        REVIEW_RULES_CSV=files["unverified_contracts.csv"],
        SETTLEMENT_CSV=files["carrier_credits.csv"],
        COUNTER_CSV=files["carrier_returns.csv"],
    ):
        out = rehearsal.run_rehearsal()
    if out["synthetic"] is not True:
        raise AssertionError("non-synthetic commercial claim emerged")
    if out["carrier_action_external_action_performed"] is not False:
        raise AssertionError("actual external action wrongly reported")
    if out["commercial_value_claimed"] is not False:
        raise AssertionError("real customer savings wrongly asserted")
    metrics = out["metrics"]
    expected_net = s.credit_one + s.credit_two - s.credit_return
    expected_fee_eligible = s.credit_one - s.credit_return
    expected_validated = s.finding_one + s.finding_two
    assertions = {
        "pipeline_audit_completed": out["audit_workflow_state"] == "REVIEW_REQUIRED",
        "buyer_review_confirmed": out["buyer_review_confirmed_count"] == 2,
        "claim_count_two": out["recovery_claim_count"] == 2,
        "original_invoices_three": out["population_invoice_count"] == 3,
        "source_declared_net_is_correct": metrics["realized_cents"] == expected_net,
        "eligible_fee_base_not_double_counted": (
            metrics["fee_eligible_realized_cents"] == expected_fee_eligible
        ),
        "validated_not_based_on_pending_tariff": (
            metrics["validated_finding_cents"] == expected_validated
        ),
        "settlement_matches_sqlite": (
            out["persistent_store"]["realized_cents"] == expected_net
        ),
        "return_preserves_stale_report_hold": out["persistent_reporting"]["stale_report_rejected"] is True,
        "synthetic_action_not_sent": out["carrier_action_external_action_performed"] is False,
        "no_commercial_claim": out["commercial_value_claimed"] is False,
    }
    # Extra forensic invariant: the output's claimed return amount must equal
    # the exact immutable synthetic counter source, not a template constant.
    reported_return = out["persistent_reporting"]["return_cents"]
    assertions["return_metadata_equals_actual_counter_source"] = (
        reported_return == s.credit_return
    )
    return {
        "pipeline_state": out["audit_workflow_state"],
        "buyer_review_state": out["buyer_review_state"],
        "claim_count": out["recovery_claim_count"],
        "source_net_cents": metrics["realized_cents"],
        "expected_source_net_cents": expected_net,
        "fee_base_cents": metrics["fee_eligible_realized_cents"],
        "validated_discrepancy_cents": metrics["validated_finding_cents"],
        "actual_return_cents": s.credit_return,
        "reported_return_cents": reported_return,
        "audit_run_hash": out["audit_run_hash"],
        "truth_hash": out["truth_hash"],
        "report_hash": out["persistent_reporting"]["report_hash"],
        "recovery_claim_batch_hash": out["recovery_claim_batch_hash"],
        "checks": assertions,
    }


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets_dir = output_dir / "datasets"
    datasets_dir.mkdir(exist_ok=True)
    results = []
    all_sources = set()
    all_audits = set()
    all_reports = set()
    for i in range(100):
        s = construct(i)
        files = generate_files(s)
        if s.source_hash in all_sources:
            raise AssertionError("two purportedly unique dataset manifests collided")
        all_sources.add(s.source_hash)
        destination = datasets_dir / f"dataset-{i:03d}"
        destination.mkdir()
        for name, data in files.items():
            (destination / name).write_bytes(data)
        case = {
            "dataset": i, "persona": s.persona, "stressor": s.stressor,
            "mode_context_only": s.mode_label, "core_audit_currency": "USD",
            "source_sha256": s.source_hash, "fault_type": s.fault,
            "invoice_csv_sha256": sha(files["invoices.csv"]),
            "verified_rules_sha256": sha(files["verified_contracts.csv"]),
            "carrier_credits_sha256": sha(files["carrier_credits.csv"]),
            "carrier_returns_sha256": sha(files["carrier_returns.csv"]),
            "core": None, "fault": None, "actual_settlement": None,
            "error": None,
        }
        try:
            core = full_rehearsal(s, files)
            case["core"] = core
            all_audits.add(core["audit_run_hash"])
            all_reports.add(core["report_hash"])
        except Exception as exc:
            case["error"] = {"stage": "full_commercial_rehearsal",
                             "type": type(exc).__name__, "message": str(exc)[:250]}
        try:
            case["fault"] = audit_fault_probe(s, files)
        except Exception as exc:
            case["fault_error"] = {"type": type(exc).__name__, "message": str(exc)[:250]}
        try:
            # Additional actual SQLite recovery/return lifecycle per case,
            # linked by case ordinal but not falsely represented as the same
            # claim as the preceding buyer-audit fixture.
            p4plan = make_plan(1000 + i, seed=SEED)
            with TemporaryDirectory(prefix=f"retally-dataset-{i:03d}-") as td:
                recovery, oracle = execute_case(p4plan, root=Path(td))
                case["actual_settlement"] = {
                    "real_sqlite_lifecycle": True,
                    "distinct_scoped_synthetic_claim": True,
                    "mode": p4plan.customer.mode,
                    "currency": p4plan.customer.currency,
                    "credit_pattern": p4plan.credit_mode,
                    "status": recovery.state,
                    "net_source_declared_cents": recovery.settlement.source_declared_net_cents,
                    "independent_cash_cents": recovery.independently_verified_cash_cents,
                    "billable_fee_cents": recovery.customer_fee_billable_cents,
                    "source_report_hash": recovery.report_hash,
                }
        except Exception as exc:
            case["actual_settlement_error"] = {
                "type": type(exc).__name__, "message": str(exc)[:250],
            }
        results.append(case)
        headline = {
            "dataset": i, "persona": s.persona, "stressor": s.stressor,
            "full": (
                "EXCEPTION" if case["core"] is None else
                ("PASSED_ALL_ORACLES" if all(case["core"]["checks"].values()) else
                 "FINANCIAL_OR_REPORTING_INVARIANT_FAILED")
            ),
            "guard": (
                "EXCEPTION" if case["fault"] is None else
                ("HELD" if case["fault"]["guard_pass"] else "UNSAFE_ACCEPTANCE")
            ),
            "sqlite": (
                "EXCEPTION" if case["actual_settlement"] is None else "PASSED_ORACLE"
            ),
            "returned_cents": s.credit_return,
        }
        print("RETALLY_CASE_JSON " + json.dumps(headline, sort_keys=True), flush=True)
    findings = []
    failed_invariants = Counter()
    for case in results:
        if case["core"] is None:
            findings.append({"dataset": case["dataset"], "type": "PIPELINE_EXCEPTION",
                             "evidence": case.get("error")})
        else:
            for name, value in case["core"]["checks"].items():
                if value is not True:
                    failed_invariants[name] += 1
                    findings.append({"dataset": case["dataset"], "type": name,
                                     "actual_return_cents": case["core"]["actual_return_cents"],
                                     "reported_return_cents": case["core"]["reported_return_cents"],
                                     "report_hash": case["core"]["report_hash"]})
        if not case["fault"] or case["fault"]["guard_pass"] is not True:
            findings.append({"dataset": case["dataset"], "type": "INVALID_INPUT_GUARD",
                             "evidence": case.get("fault_error") or case.get("fault")})
        if not case["actual_settlement"]:
            findings.append({"dataset": case["dataset"], "type": "RECOVERY_SIMULATION_EXCEPTION",
                             "evidence": case.get("actual_settlement_error")})
    summary = {
        "schema": "retally-unique-100-redteam-v1",
        "source_commit": SOURCE_SHA, "historical_defect_baseline": SOURCE_BASELINE_SHA,
        "seed": SEED,
        "dataset_count": len(results), "unique_dataset_sources": len(all_sources),
        "unique_full_audit_hashes": len(all_audits),
        "unique_commercial_report_hashes": len(all_reports),
        "full_rehearsal_completed": sum(x["core"] is not None for x in results),
        "full_all_invariants_passed": sum(
            x["core"] is not None and all(x["core"]["checks"].values())
            for x in results
        ),
        "fault_guards_passed": sum(
            x["fault"] is not None and x["fault"]["guard_pass"] for x in results
        ),
        "sqlite_lifecycles_passed": sum(x["actual_settlement"] is not None for x in results),
        "failed_assertions": dict(sorted(failed_invariants.items())),
        "findings_count": len(findings), "findings": findings,
        "customer_personas": sorted(set(x["persona"] for x in results)),
        "stressors_covered": sorted(set(x["stressor"] for x in results)),
        "model_scope": "AUDIT-FREIGHT-USD + SEPARATE-SQLITE-MULTICURRENCY",
        "real_customer_permissions": False, "actual_bank_settlement": False,
        "external_business_actions": False, "independently_adjudicated_real_freight_truth": False,
    }
    (output_dir / "report.json").write_text(
        json.dumps({"summary": summary, "cases": results}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(output_dir / "all_100_datasets.zip", "w",
                         compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for file in sorted(datasets_dir.rglob("*")):
            if file.is_file():
                bundle.write(file, file.relative_to(datasets_dir).as_posix())
    summary["dataset_zip_sha256"] = sha((output_dir / "all_100_datasets.zip").read_bytes())
    summary["dataset_zip_files"] = sum(
        1 for f in datasets_dir.rglob("*") if f.is_file()
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    print("RETALLY_SUMMARY_JSON " + json.dumps(
        {key: val for key,val in summary.items() if key != "findings"},
        sort_keys=True,
    ), flush=True)
    return summary


if __name__ == "__main__":
    requested = Path(os.environ.get(
        "RETALLY_SYNTHETIC_REPORT_DIR", "retally-100-redteam-output"
    ))
    outcome = run(requested)
    # This is an adversarial observation job, not a green production release
    # gate: never hide finding counts behind a success claim.
    if outcome["full_rehearsal_completed"] == 0:
        sys.exit("No complete end-to-end customer lifecycles were exercised")
