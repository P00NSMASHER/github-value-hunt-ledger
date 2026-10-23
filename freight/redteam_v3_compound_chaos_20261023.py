"""RETALLY v3 extreme 100-customer synthetic end-to-end adversarial gauntlet.

Runs the *actual* current freight application: 100 structurally diverse buyer
audit->buyer decisions->claims->SQLite ledgers; 600 native multimodal
contract ratings with 3 invoice mutations each; independent compound error,
concurrency, return, forgery and source-custody oracles.

All customers, contracts, carrier statuses, receipts and banking outcomes are
FICTIONAL. No real external action, use of actual credentials, or independent
real-world recovery/accuracy claim is possible through this module.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch
import csv
import io
import json
import os
import random
import sys
import time
import zipfile

from freight.canonical_schema import (
    ChargeLine, PackageFacts, build_record,
)
from freight.contracts import canonical_hash
from freight.currency_reporting import (
    assert_currency_report_current, build_currency_settlement_report,
)
from freight.payment_orchestration import (
    PaymentOrchestrator, prepare_payment_instruction, authorize_payment,
    verify_payment_snapshot, ProviderPaymentEvent,
)
import freight.payment_orchestration as payment_module
from freight.priority4_adversarial_lab import (
    make_plan, execute_case, independent_oracle, assert_independent_invariants,
    case_receipt, verify_receipt,
)
from freight.rate_authority import AuthorityBook
from freight.rating_engine import RATED, rate_record
from freight.recovery_resilience import evaluate_recovery_scenario
from freight.redteam_deep_generator_20261022 import (
    generate, source_files, INVOICE_HEADERS, csv_bytes,
)
from freight.redteam_deep_engine_20261022 import (
    run_one as run_v2_case, audit, make_sources,
)
from freight.scoped_reconciliation import ScopedTxn
from freight.priority2_evidence import reconcile_invoice_evidence
from freight.settlement_store import (
    SettlementStore, RecoveryClaim, SettlementEventRecord,
    CounterEventRecord, ALLOCATED, REVIEW, REVERSED,
)
from freight.test_phase0_recoveryos import (
    ltl_record, ltl_authority, parcel_record, parcel_authority,
)
from freight.test_phase2_recoveryos import (
    record as mode_record, authority as mode_authority,
)
from recoveryworks.reconciliation_kernel import ReconTxn

SCHEMA = "retally-extreme-100-compound-v3-20261023"
SEED = 20261023
MODES = ("LTL", "PARCEL", "TL", "INTERMODAL", "AIR", "OCEAN")
STRESS_WINDOW = "2026-10-22"
ATTACK_COUNT_TARGET = 7
EXPECTED_MODES = {
    "LTL": 16000, "PARCEL": 1600, "TL": 114000,
    "INTERMODAL": 72000, "AIR": 5700, "OCEAN": 220000,
}


def digest(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def _assert(checks: dict[str, bool], code: str, good: bool):
    checks[code] = bool(good)


def _exception_to_tag(ex: BaseException) -> dict:
    return {"type": type(ex).__name__, "message": str(ex)[:240]}


def native_mode_fixture(mode: str):
    """Versioned genuine native rate-engine fixtures; not six-mode labels."""
    if mode == "LTL":
        return ltl_record(), ltl_authority()
    if mode == "PARCEL":
        return parcel_record(), parcel_authority()
    if mode == "TL":
        return (
            mode_record("TL", (
                ("LINEHAUL", 105000), ("FUEL", 10000), ("DETENTION", 5000),
            ), miles=500),
            mode_authority("TL", {
                "pricing_model": "PER_MILE", "per_mile_cents": 200,
                "minimum_cents": 80000, "fuel_bps": 1000,
                "accessorials": {"DETENTION": {"model":"FIXED","cents":4000}},
            }),
        )
    if mode == "INTERMODAL":
        return (
            mode_record("INTERMODAL", (
                ("TRANSPORTATION", 62000), ("FUEL", 6000), ("CHASSIS", 7000),
            ), miles=100, chassis_days=2),
            mode_authority("INTERMODAL", {
                "base_cents":50000,"per_mile_cents":100,"fuel_bps":1000,
                "chassis_per_day_cents":3000,
            }),
        )
    if mode == "AIR":
        pkg=PackageFacts(
            "AIR-1", 5000, length_mm=500, width_mm=400, height_mm=300
        )
        return (
            mode_record("AIR", (
                ("TRANSPORTATION", 5200), ("FUEL", 550), ("SECURITY", 250),
            ), weight=5000, packages=(pkg,)),
            mode_authority("AIR",{
                "per_kg_cents":500,"minimum_cents":0,
                "volumetric_divisor_cm3_per_kg":6000,
                "fuel_bps":1000,"security_per_kg_cents":20,
            }),
        )
    if mode == "OCEAN":
        return (
            mode_record("OCEAN",(
                ("TRANSPORTATION",205000),("FUEL",25000),
            ),container_type="40HC"),
            mode_authority("OCEAN", {
                "pricing_model":"CONTAINER",
                "container_rates_cents":{"20GP":150000,"40HC":200000},
                "fuel_bps":1000,
            }),
        )
    raise ValueError("unrecognized mode")


def recreate(original, *, index:int, mode:str, delta:int):
    """Rebuild signed invoice content. Never bypass the original hash validator."""
    charges=list(original.charges)
    if charges[0].billed_cents + delta < 0:
        raise ValueError("invalid mutation would make a negative original charge")
    charges[0]=replace(charges[0],billed_cents=charges[0].billed_cents+delta)
    shipment=replace(original.shipment,shipment_id=f"SYN-NATIVE-{mode}-{index}")
    return build_record(
        buyer_id=original.buyer_id,
        business_unit=original.business_unit,
        invoice_id=f"SYN-MODE-{mode}-{index}",
        invoice_date=original.invoice_date,
        customer_id=original.customer_id,currency=original.currency,
        shipment=shipment,charges=tuple(charges),
        sources=original.sources,account_id=original.account_id,
        adjustments=original.adjustments,
    )


def native_rating_stress(index:int) -> dict:
    checks={}
    records=[]
    for mode in MODES:
        original,auth=native_mode_fixture(mode)
        bound=AuthorityBook((auth,))
        base=recreate(original,index=index,mode=mode,delta=0)
        fixed=EXPECTED_MODES[mode]
        baseline=rate_record(base,bound)
        _assert(checks,f"{mode}.rated",baseline.status==RATED)
        _assert(checks,f"{mode}.source_expected",baseline.expected_total_cents==fixed)
        # Value changes independently of the underlying governing tariff.
        inc=5+(index*337) % (original.charges[0].billed_cents*2+1)
        decrease=min(original.charges[0].billed_cents//2,1+index*27)
        vals=(0,inc,-decrease)
        all_results=[]
        for j,delta in enumerate(vals):
            mutated=recreate(original,index=index,mode=mode,delta=delta)
            rr=rate_record(mutated,bound)
            wanted_billed=base.billed_total_cents+delta
            _assert(checks,f"{mode}.variance.{j}",
                rr.variance_cents==max(wanted_billed-fixed,0))
            _assert(checks,f"{mode}.billed.{j}",rr.billed_total_cents==wanted_billed)
            _assert(checks,f"{mode}.expected.{j}",rr.expected_total_cents==fixed)
            _assert(checks,f"{mode}.status.{j}",rr.status==RATED)
            all_results.append(rr.rating_hash)
        _assert(checks,f"{mode}.tamper_record_hash_refused",_refused(
            lambda: rate_record(replace(base,invoice_id="SYN-MUTATED-NO-HASH"),bound)
        ))
        _assert(checks,f"{mode}.tamper_authority_hash_refused",_refused(
            lambda: rate_record(base,AuthorityBook((
                replace(auth,source_sha256=digest("UNTRUSTED-"+mode)),
            )))
        ))
        _assert(checks,f"{mode}.unique_signed_results",len(set(all_results))==3)
        records.append({
            "mode":mode, "baseline_expected_cents":fixed,
            "source_original_cents":base.billed_total_cents,
            "variants":len(vals), "receipt_digest":digest("|".join(all_results)),
        })
    return {"checks":checks,"native_mode_runs":18,"all_modes":records}


def _refused(fn) -> bool:
    try:
        fn()
    except (ValueError, TypeError, AssertionError):
        return True
    return False


def sabotage_audit(index:int) -> dict:
    d=generate(index)
    files=source_files(d)
    inputs=make_sources(d)
    rows=[dict(x) for x in d.invoice_rows]
    findings={}
    examined=0
    mutators=[
        ("DUPLICATE_ID_AND_WRONG_DATE",[
            *rows,dict(rows[0],service_date="2026-02-30")
        ],inputs,INVOICE_HEADERS,"BLOCKED"),
        ("NEGATIVE_AND_SCIENTIFIC_MONEY",[
            dict(rows[0],billed_cents="-100"),
            dict(rows[0],charge_id=rows[0]["charge_id"]+"-X",
                 billed_cents="1e4"),*rows[1:]
        ],inputs,INVOICE_HEADERS,"BLOCKED"),
        ("CORRUPT_ORIGINAL_DATE",[
            dict(rows[0],service_date="2026-02-30"),*rows[1:]
        ],inputs,INVOICE_HEADERS,"BLOCKED"),
        ("DISGUISED_BUYER_IMPERSONATION",[
            dict(row,buyer_id="SYN-FOREIGN-BUYER") for row in rows
        ],inputs,INVOICE_HEADERS+("buyer_id",),"BLOCKED"),
        ("INVALID_EXCESS_CELL",[
            dict(rows[0],extra_cell="MALICIOUS"),*rows[1:]
        ],inputs,INVOICE_HEADERS+("extra_cell",),"BLOCKED"),
    ]
    if inputs:
        mutators.append(("ALTERED_CONTRACT_SOURCE_HASH",rows,(
            replace(inputs[0],source_document_sha256="0"*64),*inputs[1:]
        ),INVOICE_HEADERS,"BLOCKED"))
    else:
        mutators.append(("NO_CONTRACT_CASE",rows,(),INVOICE_HEADERS,"NO_VALIDATED"))
    mutators.append(("NO_CONTRACT_FOR_THIS_CUSTOMER",rows,(),INVOICE_HEADERS,
                     "NO_VALIDATED"))
    for name,these,contract,header,mode in mutators:
        examined+=1
        try:
            outcome=audit(d,contract,csv_bytes(header,these))
            if mode=="BLOCKED":
                good=outcome.state=="BLOCKED" and outcome.artifacts is None
            else:
                good=(outcome.artifacts is not None and
                      all(x.decision!="VALIDATED"
                          for x in outcome.artifacts.factory.derivations))
            findings[name]=good
        except Exception as ex:
            findings[name]=False
    # Record reordering must not change rated charge-level economic decisions.
    if len(rows)>1:
        first=audit(d,inputs,files["invoice_charges.csv"])
        reversed_rows=audit(d,inputs,csv_bytes(INVOICE_HEADERS,list(reversed(rows))))
        original_decisions={
            x.charge_id:(x.decision,x.variance_cents)
            for x in first.artifacts.factory.derivations
        } if first.artifacts is not None else {}
        alternative={
            x.charge_id:(x.decision,x.variance_cents)
            for x in reversed_rows.artifacts.factory.derivations
        } if reversed_rows.artifacts is not None else {}
        findings["ROW_ORDER_ECONOMICS_INVARIANT"]=(
            bool(original_decisions) and original_decisions==alternative
        )
        examined+=1
    return {"checks":findings,"injected_attack_count":examined}


def forged_audit_receipt_probe(index:int) -> dict:
    """Direct tamper oracle for synthetic projected fees and 'real' cash."""
    plan=make_plan(8000+index,seed=SEED)
    result=evaluate_recovery_scenario(
        plan.scenario,events=plan.events,
        customer_requests=plan.requests,
        assumptions=plan.assumptions,as_of=plan.as_of,
    )
    variants=(
        replace(result,customer_fee_billable_cents=1000),
        replace(result,independently_verified_cash_cents=1000),
        replace(result,externally_approved_case=True),
        replace(result,payment_actions_performed=1),
        replace(result,carrier_contact_attempts=1),
        replace(result,settlement=replace(
            result.settlement,real_recovered_cash_cents=100)),
    )
    base=case_receipt(plan,result)
    verify_receipt(plan,result,base)
    return {
        "checks":{
            f"forged_result_{idx}_rejected":_refused(
                lambda forged=poison: case_receipt(plan,forged)
            )
            for idx,poison in enumerate(variants)
        },
        "tamper_challenges":len(variants),
    }


def ledger_compound(index:int) -> dict:
    """Two claims, delayed returns, competing evidence and cross-tenant safety.

    This tests native SQLite against an independent original-credit cents
    oracle. Separate from the v2 dataset's already proven positive ledger.
    """
    checks={}
    rng=random.Random(SEED+100*index)
    with TemporaryDirectory(prefix=f"rt-chaos-{index:03d}-") as td:
        path=Path(td)/"synthetic.sqlite3"
        buyer=f"SYN-B-{index:03d}"
        unit=f"SYN-U-{index%7}"
        s=SettlementStore(path,buyer_id=buyer,business_unit=unit)
        cents1=rng.randrange(12000,25000)
        cents2=rng.randrange(4000,12000)
        total=cents1+cents2
        base_amounts=(cents1,cents2)
        ref=f"SYN-REMIT-{index:03d}"
        for n,amount in enumerate(base_amounts):
            cl=RecoveryClaim(
                f"SYN-C-{index}-{n}",ref,f"SYN-CARRIER-{index}",
                f"SYN-PAYEE-{index}", "USD",amount,
                "2026-09-01T12:00:00Z",digest(f"SYN-FIND-{index}-{n}"),
                False,
            )
            s.create_claim(cl)
        event=SettlementEventRecord(
            f"SYN-E-{index}",ref,f"SYN-CARRIER-{index}",
            f"SYN-PAYEE-{index}","USD",total,
            "2026-09-02T12:00:00Z",digest(f"SYN-CREDIT-{index}"),
            "SYNTHETIC_NOT_BANK_CLEARED",
        )
        s.ingest_event(event)
        _assert(checks,"duplicate_provider_credit_inert",s.ingest_event(event) is False)
        _assert(checks,"tampered_provider_credit_rejected",_refused(
            lambda:s.ingest_event(replace(event,amount_cents=total+1))
        ))
        first_id=f"SYN-A-{index}-0"
        _assert(checks,"first_reviewed_allocation",s.review_allocate(
            allocation_id=first_id,claim_id=f"SYN-C-{index}-0",
            event_id=event.event_id,amount_cents=cents1,
            created_at="2026-09-03T12:00:00Z",
        )=="ALLOCATED")
        ret_amt=rng.randrange(cents1//2,cents1+1)
        ret=CounterEventRecord(
            f"SYN-R-{index}",event.event_id,"USD",ret_amt,
            "2026-09-04T12:00:00Z",
            digest(f"SYN-RETURN-{index}"),
            "SYNTHETIC_EVENT_UNVERIFIED",
        )
        before=build_currency_settlement_report(s)
        s.ingest_counter(ret)
        _assert(checks,"pre_return_snapshot_is_stale",_refused(
            lambda:assert_currency_report_current(before,s)
        ))
        status=s.auto_apply_counter(ret.counter_id,
                                    created_at="2026-09-05T12:00:00Z").status
        _assert(checks,"reviewable_full_or_partial_counter",
                status in ("REVERSED","REVIEW"))
        now=build_currency_settlement_report(s)
        one=now.by_currency[0]
        expected_reversed=ret_amt if status=="REVERSED" else 0
        _assert(checks,"return_applied_exact_cents",
                one.declared_reversed_cents==expected_reversed)
        _assert(checks,"current_net_integers",
                one.declared_net_allocated_cents==cents1-expected_reversed)
        _assert(checks,"never_bank_clear_customer",
                not now.external_settlement_verified)
        # The remaining second-claim credit can be booked only when the
        # event's counter return evidence is fully applied. A pending return
        # blocks it from being booked as recovered.
        if status=="REVERSED":
            second=s.review_allocate(
                allocation_id=f"SYN-A-{index}-1",
                claim_id=f"SYN-C-{index}-1",
                event_id=event.event_id,
                amount_cents=cents2,
                created_at="2026-09-06T12:00:00Z",
            )
            _assert(checks,"second_leg_conserves_credit",second=="ALLOCATED")
            r=build_currency_settlement_report(s).by_currency[0]
            _assert(checks,"new_net_exact",r.declared_net_allocated_cents==total-ret_amt)
        else:
            _assert(checks,"unresolved_return_blocks_other_claim",_refused(
                lambda:s.review_allocate(
                    allocation_id=f"SYN-A-{index}-1",
                    claim_id=f"SYN-C-{index}-1",
                    event_id=event.event_id,
                    amount_cents=cents2,
                    created_at="2026-09-06T12:00:00Z"
                )
            ))
        _assert(checks,"aggregate_return_over_source_rejected",_refused(
            lambda:s.ingest_counter(CounterEventRecord(
                f"SYN-X-{index}",event.event_id,"USD",total,
                "2026-09-07T12:00:00Z",
                digest(f"SYN-EXTRA-RETURN-{index}"),
                "INVALID_SYNTHETIC_RETURN",
            ))
        ))
        # Cross-customer tenant must not see this scoped ledger and source.
        foreign=SettlementStore(path,buyer_id=f"OTHER-BUYER-{index}",
                                business_unit=unit)
        snap=json.loads(foreign.report_snapshot_json())
        _assert(checks,"cross_tenant_source_separation",
                len(snap["tables"]["recovery_claims"])==0
                and len(snap["tables"]["allocations"])==0)
        scoped_snapshot=s.report_snapshot_json()
        _assert(checks,"read_only_snapshot_unchanged",
                s.report_snapshot_json()==scoped_snapshot)
        return {"checks":checks,"counter_cents":ret_amt,
                "original_credit_cents":total,
                "source_net_cents":s.realized_cents(),
                "snapshot_sha256":canonical_hash(scoped_snapshot)}


def concurrent_payment_sabotage(index:int) -> dict:
    """Adversarial 2-thread first provider submission must be serializable."""
    i=prepare_payment_instruction(
        instruction_id=f"SYN-I-{index}",
        buyer_id=f"SYN-BUYER-{index}",
        business_unit=f"SYN-U-{index%7}",
        payer_id=f"SYN-CARRIER-{index}",
        payee_id=f"SYN-CUSTOMER-{index}",
        currency="USD",amount_cents=1000+index*13,
        purpose="SYNTHETIC_CONCURRENCY_ONLY",
        finding_proof_hashes=(digest(f"FINDING-{index}"),),
        idempotency_key=f"SYN-KEY-{index}",
    )
    approved=authorize_payment(
        i,authorized_by="SYNTHETIC_NOT_A_REAL_HUMAN",
        reason="simulated lab approval only",
        authorized_at="2026-10-22T12:00:00Z",
    )
    engine=PaymentOrchestrator(i)
    engine.authorize(approved)
    gate=Barrier(2)
    def run(n):
        gate.wait(timeout=5)
        try:
            value=engine.record_provider_event(
                state="SUBMITTED",provider="SYNTHETIC_PROVIDER",
                provider_reference=f"SYN-REF-{index}-{n}",
                amount_cents=i.amount_cents,
                source_hash=digest(f"SYN-PROVIDER-RECEIPT-{index}-{n}"),
                occurred_at="2026-10-22T12:01:00Z",
            )
            return value
        except ValueError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        res=list(pool.map(run,(0,1)))
    accepted=sum(isinstance(x,ProviderPaymentEvent) for x in res)
    checks={
        "exactly_one_provider_first_event":accepted==1,
        "single_immutable_ledger_event":len(engine.events)==1,
        "valid_replay_after_concurrent_event":not _refused(
            lambda:verify_payment_snapshot(i,approved,engine.events,engine.snapshot())
        ),
        "no_independent_bank_status_claim":engine.current_state=="SUBMITTED",
    }
    return {"checks":checks,"accepted":accepted}


def run_one(index:int,out:Path) -> dict:
    base=run_v2_case(index,out)
    phases={"baseline_v2":base["status"]}
    case_failures=[]
    engine={
        "structural_v2_checks":base.get("checks",{}),
        "source_sha256":base["source_sha256"],
        "structure":base.get("structure",{}),
    }
    phases["base_failures"]=[e["invariant"] for e in base.get("findings",[])]
    attacks=[
        ("six_mode_rating",lambda:native_rating_stress(index)),
        ("compound_audit_corruption",lambda:sabotage_audit(index)),
        ("forged_financial_receipts",lambda:forged_audit_receipt_probe(index)),
        ("two_claim_return_chaos",lambda:ledger_compound(index)),
        ("concurrent_provider_first_event",lambda:concurrent_payment_sabotage(index)),
    ]
    counts=Counter()
    for name,fn in attacks:
        try:
            result=fn()
            failures=[key for key,value in result["checks"].items() if not value]
            case_failures.extend({"family":name,"invariant":x} for x in failures)
            phases[name]={
                "checks_passed":sum(x is True for x in result["checks"].values()),
                "checks_failed":len(failures),
                "probe_counts":{k:v for k,v in result.items() if k!="checks"},
                "failed_codes":failures[:30],
            }
            counts[name]+=len(result["checks"])
        except Exception as ex:
            case_failures.append({"family":name,"invariant":"UNHANDLED_ENGINE_EXCEPTION",
                                  "reason":_exception_to_tag(ex)})
            phases[name]={"unexpected_exception":_exception_to_tag(ex)}
    for x in phases["base_failures"]:
        case_failures.append({"family":"baseline_v2","invariant":x})
    return {
        "dataset":index,
        "source_sha256":base["source_sha256"],
        "structure":base.get("structure",{}),
        "phases":phases,
        "assertions_executed":dict(counts),
        "findings":case_failures,
        "status":"PASS" if not case_failures else "FINDINGS",
        "real_customer_data":False,
        "bank_cleared_cash":False,
        "real_freight_accuracy":None,
    }


def execute(out:Path):
    out.mkdir(parents=True,exist_ok=True)
    findings=Counter()
    cases=[]
    families=Counter()
    for idx in range(100):
        item=run_one(idx,out)
        cases.append(item)
        for e in item["findings"]:
            findings[f'{e["family"]}:{e["invariant"]}']+=1
        for k,v in item["assertions_executed"].items():
            families[k]+=v
        print("RETALLY_V3_CASE "+json.dumps({
            "index":idx,"status":item["status"],
            "assertions":sum(item["assertions_executed"].values()),
            "failure_codes":[f'{e["family"]}:{e["invariant"]}'
                             for e in item["findings"]][:18],
        },sort_keys=True),flush=True)
    all_sources={x["source_sha256"] for x in cases}
    structures={
        json.dumps({
            "inv":x["structure"].get("invoice_count"),
            "charges":x["structure"].get("charge_count"),
            "carrier":x["structure"].get("carrier_count"),
            "customer":x["structure"].get("customer_count"),
            "currencies":x["structure"].get("currencies"),
            "contracts":x["structure"].get("contract_document_count"),
        },sort_keys=True)
        for x in cases
    }
    summary={
        "schema":SCHEMA,
        "dataset_count":len(cases),
        "unique_source_sha256":len(all_sources),
        "unique_structural_signatures":len(structures),
        "cases_passing_all_checks":sum(x["status"]=="PASS" for x in cases),
        "cases_with_findings":sum(x["status"]!="PASS" for x in cases),
        "distinct_failure_codes":len(findings),
        "raw_failed_assertions":sum(findings.values()),
        "failures_by_code":dict(sorted(findings.items())),
        "assertions_by_phase":dict(sorted(families.items())),
        "total_chaos_assertions":sum(families.values()),
        "six_actual_native_rating_modes":list(MODES),
        "native_rate_variants_expected":100*len(MODES)*3,
        "customer_compound_invoice_mutations_expected_min":100*ATTACK_COUNT_TARGET,
        "sqlite_concurrent_credit_cases_expected":100,
        "provider_concurrent_submissions_expected":100*2,
        "source_classification":"FICTIONAL_NO_INDEPENDENT_BANK_PROOF",
        "real_customers":0,
        "actual_carrier_contacts":0,
        "money_moved":0,
        "empirical_freight_detection_accuracy":None,
    }
    (out/"v3_report.json").write_text(
        json.dumps({"summary":summary,"cases":cases},sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    (out/"v3_summary.json").write_text(
        json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf-8",
    )
    src_dir=out/"datasets"
    with zipfile.ZipFile(out/"all_fictional_source_inputs.zip","w",
                         compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(src_dir.rglob("*")):
            if file.is_file():
                z.write(file,file.relative_to(src_dir).as_posix())
    summary["source_dataset_zip_sha256"]=sha256(
        (out/"all_fictional_source_inputs.zip").read_bytes()
    ).hexdigest()
    (out/"v3_summary.json").write_text(json.dumps(
        summary,sort_keys=True,indent=2
    )+"\n",encoding="utf-8")
    print("RETALLY_V3_SUMMARY "+json.dumps(summary,sort_keys=True),flush=True)
    return summary


if __name__=="__main__":
    location=Path(os.environ.get("RETALLY_V3_REPORT_DIR","retally-v3-output"))
    result=execute(location)
    if result["dataset_count"]!=100 or result["unique_source_sha256"]!=100:
        sys.exit("Incomplete or nonunique 100-case synthetic evidence run")
