"""Executable red team: 100 structurally diverse fictional freight customer datasets.

Tests current RETALLY source code from CSV audit to buyer findings, claim
persistence, carrier-action PREVIEW (never authorization/send), durable SQLite
credit, return, currency-specific report and source-bound review holds.
Reproductions and denominators are independent of engine-calculated dollars.

Every source, contract, bank credit, carrier, and buyer is invented.
No actual customer or external provider action is performed or permitted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import io
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import traceback
import zipfile

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import (
    BuyerReviewDecisionInput, build_buyer_review_batch,
)
from freight.carrier_action_payload import build_carrier_action_payload
from freight.carrier_action_workflow import build_carrier_action_proposal_batch
from freight.contracts import (
    open_incumbent_output, seal_incumbent_submission, canonical_hash,
)
from freight.currency_reporting import (
    assert_currency_report_current, build_currency_settlement_report,
)
from freight.external_action_authorization import ActionType
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import (
    build_recovery_claim_batch, persist_recovery_claim_batch,
)
from freight.recovery_resilience import (
    RecoveryScenario, RecoveryEvent, CustomerRequest, evaluate_recovery_scenario,
)
from freight.settlement_store import (
    SettlementStore, SettlementEventRecord, CounterEventRecord,
    ALLOCATED, REVIEW, REVERSED,
)
from freight.redteam_deep_generator_20261022 import (
    H, SEED, SOURCE_SCHEMA, INVOICE_HEADERS, RULE_HEADERS,
    CURRENCIES, FictionalDataset, csv_bytes, generate, source_files,
)


def _proof(v: str) -> str:
    return sha256(v.encode("ascii")).hexdigest()


def make_sources(d: FictionalDataset) -> tuple[RuleCSVInput, ...]:
    return tuple(RuleCSVInput(
        filename=spec["filename"], data=spec["data"],
        customer_id=spec["customer_id"], carrier_id=spec["carrier_id"],
        currency=spec["currency"],
        authority_document_id=spec["authority_document_id"],
        source_document_sha256=None,
        source_document_data=spec["source_document_bytes"],
        verified_controlling_authority=spec["verified_controlling_authority"],
    ) for spec in d.contracts)


def audit(d: FictionalDataset, sources: tuple[RuleCSVInput, ...], data: bytes):
    return run_audit_workflow(
        invoice_filename=f"customer-{d.index:03d}.csv", invoice_data=data,
        buyer_id=d.buyer, business_unit=d.business_unit,
        selection_rule="FROZEN_SYNTHETIC_ORIGINAL_POPULATION_NOT_REAL_TRUTH",
        rule_inputs=sources,
    )


def _raise_if_mismatch(checks: dict, name: str, wanted, actual) -> None:
    checks[name] = wanted == actual
    if checks[name] is not True:
        checks["witness_"+name] = {"expected": wanted, "observed": actual}


def actual_audit(d: FictionalDataset, files: dict[str, bytes], checks: dict):
    out = audit(d, make_sources(d), files["invoice_charges.csv"])
    checks["valid_csv_not_rejected"] = out.state != "BLOCKED" and out.artifacts is not None
    if out.artifacts is None:
        raise AssertionError("valid diverse source blocked: " + str((out.stage,out.error_code,out.error_message)))
    art = out.artifacts
    oracle = {x["charge_id"]:x for x in d.independent_charge_oracle}
    actual = {x.charge_id:x for x in art.factory.derivations}
    _raise_if_mismatch(checks,"all_charge_identities_preserved",set(oracle),set(actual))
    for id, predicted in oracle.items():
        if id not in actual:
            continue
        x=actual[id]
        if x.decision != predicted["decision"]:
            checks["independent_rating_mismatch"] = False
            checks.setdefault("rating_examples",[]).append({
                "charge": id, "expected": predicted["decision"],
                "observed":x.decision,"reason":x.reason,
            })
        if x.decision == "VALIDATED":
            _raise_if_mismatch(
                checks,"validated_amount_"+id,
                predicted["independent_expected_positive_cents"],x.variance_cents,
            )
    expected_counts=Counter(x["decision"] for x in oracle.values())
    actual_counts=Counter(x.decision for x in actual.values())
    for c in ("VALIDATED","CLEAR","REVIEW"):
        _raise_if_mismatch(checks,"decision_"+c,expected_counts[c],actual_counts[c])
    _raise_if_mismatch(checks,"full_invoice_census",d.invoice_count,art.population_build.invoice_count)
    _raise_if_mismatch(checks,"full_charge_census",len(d.invoice_rows),art.population_build.charge_count)
    expected_money=sum(x["independent_expected_positive_cents"] for x in oracle.values())
    calculated_money=sum(
        x.variance_cents or 0 for x in actual.values() if x.decision=="VALIDATED"
    )
    _raise_if_mismatch(checks,"independent_provisional_validated_cents",expected_money,calculated_money)
    checks["real_world_validated_cents_not_estimated"] = True  # Contract authenticity isn't established.
    return art, {"expected_decisions": dict(sorted(expected_counts.items())),
                 "actual_decisions":dict(sorted(actual_counts.items())),
                 "independent_synthetic_validated_cents":expected_money,
                 "invoice_count":art.population_build.invoice_count,
                 "charge_count":art.population_build.charge_count,
                 "contract_docs":len(d.contracts),
                 "audit_manifest":art.manifest.run_hash,
                 "truth_sha256":art.factory.truth.truth_hash}


def buyer_and_claims(d:FictionalDataset, art, store: SettlementStore, checks:dict):
    truth=art.factory.truth
    original_population=art.population_build.population
    sealed=seal_incumbent_submission(
        original_population,_proof("FICTIONAL_PREEXISTING_INCUMBENT_"+str(d.index))
    )
    validations=tuple(f for f in truth.findings if f.status=="VALIDATED")
    incumbent_ids=tuple(f.finding_id for n,f in enumerate(validations)
                        if (d.index+2*n)%5==0)
    incumbent=open_incumbent_output(
        population=original_population,truth=truth,
        submission=sealed,finding_ids=incumbent_ids,
    )
    approved_cases=[]
    for n,case in enumerate(art.review_packet.cases):
        if case.case_hash not in art.review_routing.buyer_review_case_hashes:
            continue
        result = (
            ReviewDisposition.CONFIRMED if n==0 or (d.index+n)%5<=2
            else ReviewDisposition.FALSE_POSITIVE if (d.index+n)%5==3
            else ReviewDisposition.UNRESOLVED
        )
        approved_cases.append(BuyerReviewDecisionInput(
            case_hash=case.case_hash,disposition=result,
            reviewer_minutes=5+(n+d.index)%40,
            reviewed_at="2026-10-01T09:00:00Z",
        ))
    buyer=build_buyer_review_batch(
        review_packet=art.review_packet,review_routing=art.review_routing,
        truth=truth,reviewer_role="FICTIONAL_ONLY_NO_AUTHENTICATED_BUYER",
        decisions=tuple(approved_cases),
    )
    _raise_if_mismatch(checks,"buyer_review_complete_count",
                       len(art.review_routing.buyer_review_case_hashes),
                       len(approved_cases))
    claims=build_recovery_claim_batch(
        truth=truth,incumbent=incumbent,review_packet=art.review_packet,
        review_routing=art.review_routing,buyer_review=buyer,
        issued_at="2026-10-02T12:00:00Z",
    )
    persisted=persist_recovery_claim_batch(store,claims)
    _raise_if_mismatch(checks,"only_confirmed_claims",
                       buyer.confirmed_count,claims.claim_count)
    _raise_if_mismatch(checks,"claims_persisted_once",
                       claims.claim_count,persisted.created_claim_count)
    repeated=persist_recovery_claim_batch(store,claims)
    _raise_if_mismatch(checks,"claim_replays_idempotent",
                       claims.claim_count,repeated.already_present_count)
    _raise_if_mismatch(checks,"incumbent_fee_exclusion",
                       sum(c.fee_disqualified for c in claims.claims),
                       claims.fee_disqualified_count)
    proposals=build_carrier_action_proposal_batch(recovery_claims=claims)
    _raise_if_mismatch(checks,"carrier_proposal_claim_population",
                       claims.claim_count,proposals.claim_count)
    action_preview_count=0
    for proposal in proposals.proposals[:4]:
        payload=build_carrier_action_payload(
            proposal=proposal,recovery_claims=claims,
            action_type=ActionType.REQUEST_CREDIT_REVIEW,
        )
        action_preview_count+=1
        _raise_if_mismatch(
            checks,"preview_proof_amount_"+str(action_preview_count),
            proposal.total_claim_cents,payload.requested_cents
        )
    return claims,{"simulated_buyer_reviewed":len(approved_cases),
                   "reviewed_confirmed":buyer.confirmed_count,
                   "false_positive":buyer.false_positive_count,
                   "unresolved":buyer.unresolved_count,
                   "claims":claims.claim_count,
                   "incumbent_disqualified":claims.fee_disqualified_count,
                   "carrier_action_previews_not_sent":action_preview_count,
                   "claims_hash":claims.batch_hash}


PATTERNS=(
    "NO_CREDIT", "FULL_CREDIT", "PARTIAL_CREDIT", "SPLIT_CREDIT",
    "OVERPAYMENT", "PARTIAL_RETURN", "FULL_RETURN", "COUNTER_BEFORE_ALLOCATION",
    "DUPLICATE_RECEIPT", "WRONG_PAYEE",
)


def make_credit(d,claim,seq,amount,wrong_payee=False) -> SettlementEventRecord:
    return SettlementEventRecord(
        event_id=f"SYN-CREDIT-{d.index}-{seq}",reference=claim.reference,
        payer_id=claim.payer_id,
        payee_id=claim.payee_id+"-UNVERIFIED-AFFILIATE" if wrong_payee else claim.payee_id,
        currency=claim.currency,amount_cents=amount,
        booked_at="2026-10-05T10:00:00Z",
        source_hash=_proof(f"FICTIONAL-CARRIER-CREDIT-{d.index}-{seq}"),
        source_kind="SIMULATED_CREDIT_NOT_BANK_CLEARED",
    )


def settle(d:FictionalDataset,claims,store: SettlementStore,checks:dict):
    expected_net=Counter()
    expected_fee=Counter()
    applied_patterns=Counter()
    sources=[]
    attempted_cases=0
    valid_claims=tuple(sorted(claims.claims,key=lambda a:a.claim_id))
    for j,claim in enumerate(valid_claims[:min(len(valid_claims),9)]):
        pattern=PATTERNS[(d.index+j*3)%len(PATTERNS)]
        applied_patterns[pattern]+=1
        if pattern=="NO_CREDIT":
            continue
        if pattern=="WRONG_PAYEE":
            evil=make_credit(d,claim,j*10,claim.amount_cents,wrong_payee=True)
            store.ingest_event(evil)
            result=store.auto_allocate(evil.event_id,created_at="2026-10-06T11:00:00Z")
            checks["wrong_payee_must_not_auto_book"]=result.status=="REVIEW"
            continue
        quantity=claim.amount_cents
        if pattern in ("PARTIAL_CREDIT","DUPLICATE_RECEIPT"):
            quantity=max(1,quantity//2)
        if pattern=="OVERPAYMENT":
            quantity=quantity+2500
        quantities=(
            (max(1,quantity//3),quantity-max(1,quantity//3))
            if pattern=="SPLIT_CREDIT" and quantity>2 else (quantity,)
        )
        for k,amount in enumerate(quantities):
            event=make_credit(d,claim,j*10+k,amount)
            store.ingest_event(event)
            sources.append(event)
            if pattern=="DUPLICATE_RECEIPT":
                if store.ingest_event(event) is not False:
                    checks["identical_credit_replay_inert"]=False
                try:
                    store.ingest_event(replace(event,amount_cents=event.amount_cents+1))
                except ValueError:
                    pass
                else:
                    checks["conflicting_credit_replay_rejected"]=False
            if pattern=="COUNTER_BEFORE_ALLOCATION":
                ret=CounterEventRecord(
                    counter_id=f"SYN-RETURN-{d.index}-{j}-{k}",
                    original_event_id=event.event_id,currency=event.currency,
                    amount_cents=event.amount_cents,
                    observed_at="2026-10-05T11:00:00Z",
                    source_hash=_proof(f"FICTIONAL-RETURN-{d.index}-{j}-{k}"),
                    source_kind="SIMULATED_REVERSAL_NOT_BANK_CLEARED",
                )
                store.ingest_counter(ret)
                result=store.auto_allocate(event.event_id,created_at="2026-10-06T11:00:00Z")
                checks["returned_before_allocation_held"]=result.status=="REVIEW"
                try:
                    store.review_allocate(
                        allocation_id=f"SYN-BAD-ALLOC-{d.index}-{j}-{k}",
                        claim_id=claim.claim_id,event_id=event.event_id,
                        amount_cents=amount,created_at="2026-10-06T11:00:00Z",
                    )
                except ValueError:
                    pass
                else:
                    checks["returned_credit_manual_override_rejected"]=False
                continue
            choice=store.auto_allocate(
                event.event_id,created_at="2026-10-06T11:00:00Z"
            )
            allowed_amt=min(amount,claim.amount_cents)
            if choice.status=="ALLOCATED":
                # Most invoice IDs have multiple charge claims; automatic
                # allocation must never silently book a different claim.
                snapshot=json.loads(store.report_snapshot_json())
                edges=[e for e in snapshot["tables"]["allocations"]
                       if e["event_id"]==event.event_id]
                if len(edges)!=1 or edges[0]["claim_id"]!=claim.claim_id:
                    checks["auto_credit_scoped_to_correct_claim"]=False
                    continue
                booked=edges[0]["amount_cents"]
            elif choice.status=="REVIEW":
                store.review_allocate(
                    allocation_id=f"SYN-REVIEWED-ALLOCATION-{d.index}-{j}-{k}",
                    claim_id=claim.claim_id,event_id=event.event_id,
                    amount_cents=allowed_amt,
                    created_at="2026-10-06T11:00:00Z",
                )
                booked=allowed_amt
            else:
                checks["settlement_requires_expected_auto_or_review"]=False
                continue
            expected_net[claim.currency]+=booked
            if not claim.fee_disqualified:
                expected_fee[claim.currency]+=booked
            if pattern in ("PARTIAL_RETURN","FULL_RETURN"):
                ret_amt = (
                    booked if pattern=="FULL_RETURN" else max(1,booked//2)
                )
                before=build_currency_settlement_report(store)
                ret=CounterEventRecord(
                    counter_id=f"SYN-RETURN-{d.index}-{j}-{k}",
                    original_event_id=event.event_id,currency=event.currency,
                    amount_cents=ret_amt,observed_at="2026-10-07T10:00:00Z",
                    source_hash=_proof(f"FICTIONAL-RETURN-{d.index}-{j}-{k}"),
                    source_kind="SIMULATED_RETURN_NOT_BANK_CLEARED",
                )
                store.ingest_counter(ret)
                undone=store.auto_apply_counter(
                    ret.counter_id,created_at="2026-10-07T11:00:00Z"
                )
                checks["counter_return_applied_exactly"]=undone.status=="REVERSED"
                expected_net[claim.currency]-=ret_amt
                if not claim.fee_disqualified:
                    expected_fee[claim.currency]-=ret_amt
                try:
                    assert_currency_report_current(before,store)
                except ValueError:
                    pass
                else:
                    checks["stale_pre_return_report_rejected"]=False
    # Every dataset also checks that a non-existent carrier credit cannot
    # generate realized amount, irrespective of any legitimate booked credits.
    try:
        store.auto_allocate("SYN-UNKNOWN-CREDIT",created_at="2026-10-08T00:00:00Z")
    except ValueError:
        pass
    else:
        checks["unknown_settlement_source_rejected"]=False
    actual_report=build_currency_settlement_report(store)
    by_currency={r.currency:r for r in actual_report.by_currency}
    for currency in set(expected_net)|set(expected_fee):
        _raise_if_mismatch(checks,"realized_"+currency,
                           expected_net[currency],
                           by_currency[currency].declared_net_allocated_cents)
        _raise_if_mismatch(checks,"fee_base_"+currency,
                           expected_fee[currency],
                           by_currency[currency].declared_fee_eligible_net_cents)
    # Aggregate integer cents below is an internal conservation check
    # within each currency separately; never publish a cross-FX total.
    if len(by_currency)>1:
        checks["no_cross_currency_aggregate"]=(
            actual_report.single_aggregated_total_cents is None
        )
    _raise_if_mismatch(checks,"source_declared_total_internal",
                       sum(expected_net.values()),store.realized_cents())
    _raise_if_mismatch(checks,"source_declared_fee_internal",
                       sum(expected_fee.values()),store.fee_eligible_cents())
    checks["no_external_bank_attestation"]=actual_report.external_settlement_verified is False
    checks["no_cross_currency_fake_dollar_total"]=actual_report.single_aggregated_total_cents is None
    assert_currency_report_current(actual_report,store)
    return {
        "patterns":dict(sorted(applied_patterns.items())),
        "currency_actual_and_oracle":{
            c:{"actual":by_currency[c].declared_net_allocated_cents,
               "oracle":expected_net[c],
               "fee_actual":by_currency[c].declared_fee_eligible_net_cents,
               "fee_oracle":expected_fee[c]}
            for c in sorted(expected_net)
        },
        "credit_sources":len(sources),
        "verified_bank_cash_cents":0,
        "commercially_billable_cents":0,
        "snapshot_sha256":actual_report.snapshot_hash,
        "report_sha256":actual_report.report_hash,
        "source_declared_not_bank_verified":True,
    }


def challenge(d:FictionalDataset,files:dict[str,bytes],checks:dict):
    source=make_sources(d)
    base=[dict(x) for x in d.invoice_rows]
    failures=[]
    passes=Counter()
    cases={
        "duplicate_invoice_charge":(
            [*base,dict(base[0])],source,None
        ),
        "negative_monetary_value":(
            [dict(base[0],billed_cents="-1"),*base[1:]],source,None
        ),
        "malformed_monetary_exponent":(
            [dict(base[0],billed_cents="1e3"),*base[1:]],source,None
        ),
        "impossible_service_date":(
            [dict(base[0],service_date="2026-02-30"),*base[1:]],source,None
        ),
    }
    # A copied identity column is never an authenticated buyer.
    impersonated=[dict(x,buyer_id="SYNTHETIC-OTHER-CUSTOMER") for x in base]
    cases["untrusted_buyer_column"]=(impersonated,source,(*INVOICE_HEADERS,"buyer_id"))
    if source:
        bad_src=replace(source[0],source_document_sha256="0"*64)
        cases["altered_source_document_digest"]=(base,(bad_src,*source[1:]),None)
    for code,(rows,case_rules,header) in cases.items():
        try:
            data=csv_bytes(header or INVOICE_HEADERS,rows)
            res=audit(d,case_rules,data)
            okay=(res.state=="BLOCKED" and res.artifacts is None)
        except Exception as ex:
            okay=False
            failures.append({"code":code,"error":type(ex).__name__,
                             "message":str(ex)[:150]})
        if okay:
            passes[code]+=1
        else:
            failures.append({"code":code,"observed":"UNSAFE_ACCEPTANCE_OR_UNHANDLED_EXCEPTION"})
    # Any targeted change to a valid invoice with VERIFIED source authority
    # must not reuse the original frozen audit/source evidence fingerprint.
    changed=[dict(x) for x in base]
    changed[0]["billed_cents"]=str(int(changed[0]["billed_cents"])+17)
    mutated=csv_bytes(INVOICE_HEADERS,changed)
    checks["input_bytes_change_sha"]=H(mutated)!=H(files["invoice_charges.csv"])
    # Test metamorphic shuffled input without assuming its file SHA stays
    # unchanged. Decision *counts* must remain invariant.
    if len(base)>1:
        other=audit(d,source,csv_bytes(INVOICE_HEADERS,list(reversed(base))))
        if other.artifacts is None:
            failures.append({"code":"ROW_REORDER_BLOCKED","state":other.state})
        else:
            counts=Counter(x.decision for x in other.artifacts.factory.derivations)
            wanted=Counter(x["decision"] for x in d.independent_charge_oracle)
            if counts!=wanted:
                failures.append({"code":"ROW_ORDER_AFFECTS_ECONOMICS",
                                 "expected":dict(wanted),"actual":dict(counts)})
            else:
                passes["reordered_row_economics"]+=1
    return {"injected_tests":len(cases)+(1 if len(base)>1 else 0),
            "guards_passed":dict(sorted(passes.items())),
            "defects":failures}


def hard_mutations(d:FictionalDataset,files:dict[str,bytes]) -> dict:
    """Change actual tariff scope and original source rows, not just labels.

    These are deliberately separate negative challenge datasets. No synthetic
    reviewers may promote an altered carrier/currency, unauthorized rate or
    expired amendment into a VALIDATED finding.
    """
    source=make_sources(d)
    bases=[dict(x) for x in d.invoice_rows]
    defects=[]
    totals=Counter()
    accepted_review=[]
    targets=[x["charge_id"] for x in d.independent_charge_oracle
             if x["decision"]=="VALIDATED"]
    if not targets:
        return {"targeted_source_mutations":0,"reason":"NO_VALIDATED_CLAIM_TO_DEVALIDATE",
                "safeguards":{},"defects":[]}
    target_id=targets[(d.index*7)%len(targets)]
    ix=next(k for k,row in enumerate(bases) if row["charge_id"]==target_id)
    row=bases[ix]
    def poison(kind,changed_rows,changed_rules):
        data=csv_bytes(INVOICE_HEADERS,changed_rows)
        try:
            out=audit(d,changed_rules,data)
            if out.artifacts is None:
                # Full blocking is safe, but a valid changed customer source
                # should usually be held for rate/contract review.
                safe=out.state=="BLOCKED"
                actual="BLOCKED:"+str(out.error_code)
            else:
                affected=next(z for z in out.artifacts.factory.derivations
                              if z.charge_id==target_id)
                safe=affected.decision!="VALIDATED"
                actual=affected.decision+":"+str(affected.reason)
        except Exception as ex:
            safe=False
            actual=type(ex).__name__+":"+str(ex)[:110]
        totals[kind]+=1
        if not safe:
            defects.append({"code":kind,"target_charge":target_id,"observed":actual})
        else:
            accepted_review.append(kind)
    wrong_carrier=[dict(x) for x in bases]
    wrong_carrier[ix]["carrier_id"]=row["carrier_id"]+"-UNAUDITED"
    poison("CARRIER_SWITCH_AFTER_SOURCE_FREEZE",wrong_carrier,source)
    wrong_currency=[dict(x) for x in bases]
    wrong_currency[ix]["currency"]="JPY"  # no JPY cent contract from this test
    poison("CURRENCY_SWITCH_NO_CONTROLLING_AUTHORITY",wrong_currency,source)
    outside=[dict(x) for x in bases]
    outside[ix]["service_date"]="2027-03-15"
    poison("SHIPMENT_DATE_AFTER_TARIFF_EXPIRY",outside,source)
    # A synthetic human simply toggling a contract's verified bit must not
    # be treated as independent execution/legal contract authenticity.
    which=next((k for k,z in enumerate(source)
                if z.customer_id==row["customer_id"]
                and z.carrier_id==row["carrier_id"]
                and z.currency==row["currency"]
                and z.verified_controlling_authority
                and any(r["charge_code"]==row["charge_code"]
                        for r in csv.DictReader(io.StringIO(z.data.decode())))),
                None)
    if which is not None:
        changed=list(source)
        changed[which]=replace(changed[which],verified_controlling_authority=False)
        poison("ORIGINAL_TARIFF_AUTHORITY_REVOKED",bases,tuple(changed))
    competing=RuleCSVInput(
        filename="ADVERSARIAL-CONFLICT.csv",
        data=csv_bytes(RULE_HEADERS,[{
            "charge_code":row["charge_code"],"pricing_model":"FIXED",
            "effective_from":"2026-09-01","effective_to":"2026-09-30",
            "fixed_cents":str(int(row["billed_cents"])+211),"unit_rate_cents":"",
        }]),
        customer_id=row["customer_id"],carrier_id=row["carrier_id"],
        currency=row["currency"],
        authority_document_id="UNRESOLVED_COMPETING_FICTIONAL_AMENDMENT",
        source_document_sha256=None,
        source_document_data=b"SIMULATED CONFLICTING RATE NOT AN EXECUTED AGREEMENT",
        verified_controlling_authority=True,
    )
    poison("CONFLICTING_EXECUTED_TARIFF_AMENDMENT",bases,(*source,competing))
    # The source hash must change when the original invoice monetary row does;
    # a valid audit may still pass, but original evidence cannot be reused.
    changed=[dict(x) for x in bases]
    changed[ix]["billed_cents"]=str(int(row["billed_cents"])+129)
    new=audit(d,source,csv_bytes(INVOICE_HEADERS,changed))
    initial=audit(d,source,files["invoice_charges.csv"])
    totals["SILENT_INVOICE_MONETARY_REWRITE"]+=1
    if (not new.artifacts or not initial.artifacts or
        new.artifacts.invoice_batch.file_sha256==
        initial.artifacts.invoice_batch.file_sha256):
        defects.append({"code":"SILENT_INVOICE_MONETARY_REWRITE",
                        "observed":"ORIGINAL_RECEIPT_NOT_CHANGED"})
    else:
        accepted_review.append("SILENT_INVOICE_MONETARY_REWRITE")
    return {"targeted_source_mutations":sum(totals.values()),
            "safeguards":dict(sorted(totals.items())),
            "held_or_rejected":len(accepted_review),"defects":defects}


def adversarial_customer_demands(d:FictionalDataset,claims,store: SettlementStore) -> dict:
    """Embed insolvency, redirection, denial and data-rights concerns in a
    case sourced from the SAME actual settlement evidence in this dataset.
    """
    if not claims.claims:
        return {"cases":0,"reason":"NO_CONFIRMED_REVIEW_SOURCE","defects":[]}
    claim=claims.claims[d.index % len(claims.claims)]
    scenario=RecoveryScenario(
        case_id=claim.reference,claim_id=claim.claim_id,
        buyer_id=d.buyer,business_unit=d.business_unit,
        payer_id=claim.payer_id,payee_id=claim.payee_id,
        currency=claim.currency,disputed_cents=claim.amount_cents,
        issued_at=claim.issued_at,
        source_invoice_sha256=H(
            f"FICTIONAL_CUSTOMER_INVOICE_ORIGINAL_{d.index}".encode("utf-8")),
        source_finding_sha256=claim.source_hash,
    )
    kinds=(
        "INSOLVENCY_NOTICE","CARRIER_DENIAL","PAYMENT_REVERSAL_NOTICE",
        "CLAIM_TIME_BAR_CONCERN","CUSTOMER_DISPUTE","DELAY_NOTICE",
    )
    demands=(
        "PAY_AFFILIATE","GUARANTEED_RECOVERY","DELETE_ALL_EVIDENCE",
        "CROSS_TENANT_MERGE","IMMEDIATE_SETTLEMENT","FEE_WAIVER",
    )
    chosen_kind=kinds[(d.index*5)%len(kinds)]
    chosen_demand=demands[(d.index*7)%len(demands)]
    event=RecoveryEvent(
        event_id=f"SYN-EVENT-{d.index}",kind=chosen_kind,
        observed_at="2026-10-12T10:00:00Z",
        source_sha256=H(f"FICTIONAL_CARRIER_NOTE_{d.index}".encode()),
    )
    request=CustomerRequest(
        request_id=f"SYN-DEMAND-{d.index}",kind=chosen_demand,
        requested_at="2026-10-12T11:00:00Z",
        source_sha256=H(f"FICTIONAL_BUYER_REQUEST_{d.index}".encode()),
        requested_payee_id=(
            f"SYN-UNVERIFIED-AFFILIATE-{d.index}"
            if chosen_demand=="PAY_AFFILIATE" else None
        ),
    )
    before=store.report_snapshot_json()
    result=evaluate_recovery_scenario(
        scenario,events=(event,),customer_requests=(request,),
        as_of="2026-12-31",store=store,
    )
    after=store.report_snapshot_json()
    bad=[]
    if result.customer_fee_billable_cents!=0 or result.independently_verified_cash_cents!=0:
        bad.append({"code":"UNVERIFIED_PAYMENT_PROMOTED_TO_ACTUAL_CASH"})
    if result.carrier_contact_attempts or result.payment_actions_performed:
        bad.append({"code":"UNAUTHORIZED_EXTERNAL_REQUEST_EXECUTED"})
    if not result.customer_request_triage[0].no_external_action:
        bad.append({"code":"BUYER_INSTRUCTION_BYPASSED_GUARD"})
    if before!=after:
        bad.append({"code":"READ_ONLY_RECOVERY_REVIEW_MUTATED_LEDGER"})
    if result.externally_approved_case:
        bad.append({"code":"SIMULATED_SOURCE_TREATED_AS_REAL_APPROVAL"})
    return {"cases":1,"source_claim":claim.claim_id,
            "event":chosen_kind,"buyer_demand":chosen_demand,
            "result_state":result.state,"report_hash":result.report_hash,
            "defects":bad}


def run_one(i: int,output:Path) -> dict:
    d=generate(i)
    files=source_files(d)
    where=output / "datasets" / f"fictional-buyer-{i:03d}"
    where.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        (where/name).write_bytes(data)
    checks:dict={}
    stages={}
    errors=[]
    try:
        art,stages["audit"]=actual_audit(d,files,checks)
    except Exception as ex:
        errors.append({"stage":"AUDIT","type":type(ex).__name__,"message":str(ex)[:220]})
        art=None
    if art is not None:
        try:
            with TemporaryDirectory(prefix=f"retally-deep-{i:03d}-") as temp:
                store=SettlementStore(
                    Path(temp)/"isolated.sqlite3",
                    buyer_id=d.buyer,business_unit=d.business_unit,
                )
                claims,stages["claim"]=buyer_and_claims(d,art,store,checks)
                stages["settlement"]=settle(d,claims,store,checks)
                stages["difficult_requests"]=adversarial_customer_demands(d,claims,store)
                for problem in stages["difficult_requests"]["defects"]:
                    checks["DEMAND_"+problem["code"]]=False
        except Exception as ex:
            errors.append({"stage":"CLAIM_SETTLEMENT","type":type(ex).__name__,
                           "message":str(ex)[:220]})
    try:
        stages["negative"]=challenge(d,files,checks)
        stages["hard_mutations"]=hard_mutations(d,files)
        for finding in stages["hard_mutations"]["defects"]:
            checks["HARD_"+finding["code"]]=False
    except Exception as ex:
        errors.append({"stage":"MALFORMED_SOURCE_PROBES","type":type(ex).__name__,
                       "message":str(ex)[:220]})
    failures=[
        {"invariant":k,"actual":checks.get("witness_"+k)}
        for k,v in checks.items()
        if v is False and not k.startswith("witness_")
    ]
    for f in stages.get("negative",{}).get("defects",[]):
        failures.append({"invariant":"FAULT_"+f["code"],"actual":f})
    for e in errors:
        failures.append({"invariant":"STAGE_"+e["stage"],"actual":e})
    return {
        "dataset":i,"source_sha256":d.scenario_sha256,
        "structure":{
            "persona":d.persona,"stressor":d.stressor,
            "mode_context_only":d.carriage_mode_context,
            "invoice_count":d.invoice_count,"charge_count":len(d.invoice_rows),
            "carrier_count":len({x["carrier_id"] for x in d.invoice_rows}),
            "customer_count":len({x["customer_id"] for x in d.invoice_rows}),
            "currencies":sorted({x["currency"] for x in d.invoice_rows}),
            "contract_document_count":len(d.contracts),
            "pricing_models": sorted({row["pricing_model"] for c in d.contracts
                for row in csv.DictReader(io.StringIO(c["data"].decode("utf-8")))}),
            "authority_kinds":sorted({x["category"] for x in d.independent_charge_oracle}),
        },
        "stages":stages,
        "checks":{k:v for k,v in checks.items() if not k.startswith("witness_")},
        "errors":errors,
        "findings":failures,
        "status":"PASS" if not failures else "ADVERSARIAL_FINDING",
        "customer_data_real":False,"approved_bank_clearing":False,
        "real_carrier_action":False,
    }


def execute_all(out:Path) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    findings=Counter()
    cases=[]
    all_sources=set()
    structures=set()
    covered=Counter()
    for i in range(100):
        case=run_one(i,out)
        cases.append(case)
        all_sources.add(case["source_sha256"])
        q=case["structure"]
        signature=(
            q["invoice_count"],q["charge_count"],q["carrier_count"],
            q["customer_count"],len(q["currencies"]),q["contract_document_count"],
        )
        structures.add(signature)
        for k in q["authority_kinds"]:covered["rule:"+k]+=1
        for k in q["pricing_models"]:covered["pricing:"+k]+=1
        for k in q["currencies"]:covered["currency:"+k]+=1
        for error in case["findings"]:
            findings[error["invariant"]]+=1
        print("RETALLY_DEEP_CASE "+json.dumps({
            "i":i,"structure":{k:q[k] for k in
                ("invoice_count","charge_count","carrier_count","customer_count","currencies","contract_document_count")},
            "status":case["status"],
            "failure_families":sorted({x["invariant"] for x in case["findings"]}),
            "checks":sum(v is True for v in case["checks"].values()),
        },sort_keys=True),flush=True)
    (out/"report.json").write_text(json.dumps({
        "schema":"retally-adversarial-diversity-v2","cases":cases,
    },sort_keys=True,indent=2)+"\n",encoding="utf-8")
    with zipfile.ZipFile(out/"fictional-datasets.zip","w",
                         compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted((out/"datasets").rglob("*")):
            if p.is_file():
                z.write(p,p.relative_to(out/"datasets").as_posix())
    summary={
        "schema":"retally-adversarial-diversity-v2",
        "source_schema":SOURCE_SCHEMA,
        "seed":SEED,"cases":len(cases),
        "unique_source_manifests":len(all_sources),
        "unique_structure_signatures":len(structures),
        "genuine_structural_axes":[
            "invoice_count","charge_lines_per_invoice","customer_count",
            "carrier_count","currency_count","pricing_models","rate_disputes",
            "buyer_review_dispositions","incumbent_exclusions","claim_count",
            "partial_split_overpay_credit","returned_credit_amounts",
            "wrong_payee","duplicate_receipt","stale_reports","invalid_sources",
        ],
        "accepted_fictional_source_corpora":sum(bool(x["stages"].get("audit")) for x in cases),
        "claim_and_payment_stages_exercised":sum(bool(x["stages"].get("settlement")) for x in cases),
        "claim_bearing_cases":sum(x["stages"].get("claim",{}).get("claims",0)>0 for x in cases),
        "intentional_no_claim_cases":sum(x["stages"].get("claim",{}).get("claims",0)==0 for x in cases),
        "confirmed_claim_count":sum(x["stages"].get("claim",{}).get("claims",0) for x in cases),
        "adversarial_authority_mutations":sum(x["stages"].get("hard_mutations",{}).get("targeted_source_mutations",0) for x in cases),
        "difficult_recovery_requests":sum(x["stages"].get("difficult_requests",{}).get("cases",0) for x in cases),
        "cases_passing_all_oracles":sum(x["status"]=="PASS" for x in cases),
        "cases_with_finding":sum(x["status"]!="PASS" for x in cases),
        "raw_findings":sum(findings.values()),
        "distinct_root_cause_test_codes":len(findings),
        "root_cause_failures":dict(sorted(findings.items())),
        "coverage":dict(sorted(covered.items())),
        "invoice_count_range":[min(x["structure"]["invoice_count"] for x in cases),
                              max(x["structure"]["invoice_count"] for x in cases)],
        "charge_count_range":[min(x["structure"]["charge_count"] for x in cases),
                             max(x["structure"]["charge_count"] for x in cases)],
        "total_invoices":sum(x["structure"]["invoice_count"] for x in cases),
        "total_charge_lines":sum(x["structure"]["charge_count"] for x in cases),
        "zip_sha256":H((out/"fictional-datasets.zip").read_bytes()),
        "real_customer_data":False,"real_carrier_actions":False,
        "bank_cleared_funds":False,"real_world_detection_accuracy":None,
        "contract_execution_verified":False,
    }
    (out/"summary.json").write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("RETALLY_DEEP_SUMMARY "+json.dumps(summary,sort_keys=True),flush=True)
    return summary


if __name__=="__main__":
    dest=Path(os.environ.get("RETALLY_DEEP_REPORT_DIR","retally-deep-100-output"))
    outcome=execute_all(dest)
    if outcome["cases"]!=100 or outcome["unique_source_manifests"]!=100:
        sys.exit("The complete unique synthetic test population was not produced")
