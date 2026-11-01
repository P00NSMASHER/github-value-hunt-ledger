"""Independent verification of Phase 5C fictional, QA-staged, signed financial facts.

Pure offline verifier. Trust anchors (public keys) and sample truths are
fixtures managed outside the tested QA application. Passing does NOT prove
real buyers, banks, carrier settlement or deployed RecoveryOS correctness.
"""
from __future__ import annotations
import base64
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

ROOT = Path(__file__).parent
EXPECTED_ROLES = {
 "CONTRACT":"BUYER", "CARRIER_CREDIT":"CARRIER",
 "CUSTOMER_POST":"BUYER_ACCOUNTING","CUSTOMER_REVERSAL":"BUYER_ACCOUNTING",
 "FEE_INVOICE":"RETALLY_BILLING","FEE_COLLECTION":"PAYMENT_PROCESSOR",
 "FEE_CREDIT":"RETALLY_BILLING","FEE_REFUND":"PAYMENT_PROCESSOR",
}
KIND_GROUPS = tuple(EXPECTED_ROLES)


class IndependentProofRejected(ValueError):
    pass


def check(condition: bool, reason: str):
    if not condition:
        raise IndependentProofRejected(reason)


def _date(x: str) -> datetime:
    return datetime.fromisoformat(x.replace("Z", "+00:00")).astimezone(timezone.utc)


def _int(x, name: str) -> int:
    try:
        i=int(x)
    except (ValueError,TypeError) as ex:
        raise IndependentProofRejected("INVALID_"+name) from ex
    check(type(x) in (int,str) and str(i)==str(x) and i>=0, "INVALID_"+name)
    return i


def signed_bytes(payload:dict) -> bytes:
    return json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False,
                      allow_nan=False).encode("utf8")


def verify_frozen_finances(fixture: dict) -> dict:
    check(fixture.get("schema")==1 and fixture.get("classification")==
          "INDEPENDENTLY_SIGNED_FICTIONAL_QA_EVIDENCE_ONLY","WRONG_FIXTURE_BOUNDARY")
    check(fixture.get("actualCustomerRecoveryProven") is False and
          fixture.get("productionDatabaseWrites")==0,"FAKE_PRODUCTION_CERTIFICATION")
    check(fixture["cluster"]==[{"sysid":"7694294930552894346"}],
          "WRONG_STAGING_CLUSTER")
    check("WHERE 1 = 0" in fixture["view"][0]["text"],
          "LEGACY_FAIL_CLOSED_VIEW_REPLACED")
    cases=fixture["cases"]
    check(len(cases)==1,"MULTI_CASE_FIXTURE_NOT_SUPPORTED")
    case=cases[0]
    tenant=case["tenant_id"];case_id=case["case_id"];currency=case["currency"]
    claim_cap=_int(case["max_claim_cents"],"CLAIM_CAP")
    keys={(row["tenant_id"],row["key_id"]):row for row in fixture["keys"]}
    records=fixture["documents"]
    check(len(records)>0,"MISSING_SIGNED_FINANCIAL_RECORDS")
    by_id={}
    economic_ids=set()
    source_ids=set()
    grouped=defaultdict(list)
    for row in sorted(records,key=lambda r:(r["occurred_at"],r["record_id"])):
        payload=row["body"]
        check(isinstance(payload,dict),"NOT_STRUCTURED_SIGNED_BODY")
        rid=row["record_id"];kind=row["kind"]
        check(kind in EXPECTED_ROLES,"UNSUPPORTED_FINANCIAL_EVENT")
        check(rid not in by_id,"DUPLICATE_EVENT_ID")
        check((row["tenant_id"],row["case_id"],row["kind"],row["economic_key"]) not in economic_ids,
              "DUPLICATE_ECONOMIC_EVENT")
        economic_ids.add((row["tenant_id"],row["case_id"],row["kind"],row["economic_key"]))
        check((kind,row["source_sha256"]) not in source_ids,"RELABELLED_DUPLICATE_DOCUMENT")
        source_ids.add((kind,row["source_sha256"]))
        check(row["tenant_id"]==tenant and row["case_id"]==case_id and row["currency"]==currency,
              "CROSS_TENANT_CASE_OR_CURRENCY")
        check(payload["tenantId"]==tenant and payload["caseId"]==case_id and
              payload["customerId"]==case["customer_id"] and
              payload["invoiceId"]==case["invoice_id"] and payload["currency"]==currency,
              "SIGNED_SOURCE_SCOPE_MISMATCH")
        for body_key,column in [("recordId","record_id"),("economicKey","economic_key"),
                                ("referenceId","reference_id"),("kind","kind"),
                                ("sourceHash","source_sha256"),("issuerKeyId","issuer_key_id")]:
            check(payload[body_key]==row[column],"SIGNATURE_ROW_DISAGREEMENT_"+body_key)
        check(_int(payload["amountCents"],"AMOUNT")==_int(row["amount_cents"],"AMOUNT"),
              "SIGNED_AMOUNT_MISMATCH")
        check(payload["feeBps"]==row["fee_bps"],"SIGNED_FEE_RATE_MISMATCH")
        signer=keys.get((tenant,row["issuer_key_id"]))
        check(signer is not None,"UNKNOWN_SYNTHETIC_SIGNER")
        check(signer["role"]==EXPECTED_ROLES[kind],"WRONG_SIGNER_ROLE")
        when=_date(payload["occurredAt"])
        revoked=signer["revoked_at"]
        check(_date(signer["enabled_from"])<=when<_date(signer["expires_at"]) and
              (revoked is None or when<_date(revoked)), "EXPIRED_OR_REVOKED_ISSUER")
        check(_date(row["occurred_at"])==when,"SIGNATURE_TIMESTAMP_MISMATCH")
        try:
            public=load_pem_public_key(signer["public_key_pem"].encode())
            check(isinstance(public,Ed25519PublicKey),"UNSUPPORTED_SIGNER_ALGORITHM")
            public.verify(base64.b64decode(row["signature_b64"],validate=True),signed_bytes(payload))
        except Exception as ex:
            raise IndependentProofRejected("SIGNATURE_VERIFICATION_FAILED") from ex
        by_id[rid]=row
        grouped[kind].append(row)
    contracts=grouped["CONTRACT"]
    check(len(contracts)==1,"MISSING_OR_AMBIGUOUS_HISTORICAL_CONTRACT")
    contract=contracts[0];bps=_int(contract["fee_bps"],"FEE_BPS")
    check(0<bps<10000 and _int(contract["amount_cents"],"CONTRACT_AMOUNT")==0,
          "INVALID_CONTRACT_FEE")
    for row in records:
        if row["kind"]!="CONTRACT":
            check(_date(row["occurred_at"])>=_date(contract["occurred_at"]),"PRECONTRACT_TRANSACTION")
            check(row["body"]["contractVersion"]==contract["body"]["contractVersion"],
                  "HISTORICAL_CONTRACT_VERSION_MISMATCH")
    settled={e["id"]:e for e in fixture["events"] if e["state"]=="SETTLED" and e["tenant_id"]==tenant}
    credits={}
    for row in grouped["CARRIER_CREDIT"]:
        posted_ref=row["body"]["providerEventId"]
        event=settled.get(posted_ref)
        check(event is not None and _int(event["amount_cents"],"PROVIDER_EVENT_AMOUNT")==
              _int(row["amount_cents"],"CARRIER_AMOUNT"),
              "UNSUPPORTED_CARRIER_CREDIT_EVENT")
        check(posted_ref not in (c["body"]["providerEventId"] for c in credits.values()),
              "DUPLICATED_PROVIDER_SETTLEMENT")
        credits[row["record_id"]]=row
    gross_carrier=sum(_int(r["amount_cents"],"CARRIER") for r in credits.values())
    check(gross_carrier<=claim_cap,"CLAIM_CAP_EXCEEDED")
    postings={}
    posted_refs=set()
    for row in grouped["CUSTOMER_POST"]:
        ref=row["reference_id"];credit=credits.get(ref)
        check(credit is not None,"POST_WITHOUT_CARRIER_CREDIT")
        check(ref not in posted_refs,"DUPLICATE_CUSTOMER_POST")
        posted_refs.add(ref)
        check(_date(row["occurred_at"])>=_date(credit["occurred_at"]),"PRE_CREDIT_POSTING")
        check(_int(row["amount_cents"],"POST")==_int(credit["amount_cents"],"CREDIT"),
              "UNBACKED_POSTED_CREDIT")
        postings[row["record_id"]]=row
    reversals=defaultdict(int)
    for row in grouped["CUSTOMER_REVERSAL"]:
        original=postings.get(row["reference_id"])
        check(original is not None,"ORPHAN_RECOVERY_REVERSAL")
        check(_date(row["occurred_at"])>=_date(original["occurred_at"]),"REVERSAL_PREDATES_POSTING")
        reversals[original["record_id"]]+=_int(row["amount_cents"],"REVERSAL")
        check(reversals[original["record_id"]]<=_int(original["amount_cents"],"POST"),
              "EXCESSIVE_RECOVERY_REVERSAL")
    gross_posted=sum(_int(r["amount_cents"],"POST") for r in postings.values())
    reversed_cents=sum(reversals.values())
    net_recovery=gross_posted-reversed_cents
    check(0<=net_recovery<=claim_cap,"NET_RECOVERY_INVALID")
    earned=(net_recovery*bps+5000)//10000
    def total(kind):return sum(_int(r["amount_cents"],kind) for r in grouped[kind])
    invoice=total("FEE_INVOICE");credit_notes=total("FEE_CREDIT")
    collection=total("FEE_COLLECTION");refund=total("FEE_REFUND")
    check(invoice-credit_notes==earned,"FEE_INVOICED_BALANCE_WRONG")
    check(collection>=refund,"FEES_REFUNDED_EXCEED_COLLECTION")
    net_collection=collection-refund
    receivable=max(earned-net_collection,0)
    refund_liability=max(net_collection-earned,0)
    check(receivable==0 and refund_liability==0,"FINAL_FEES_UNRECONCILED")
    independently={
        "currency":currency,"carrier_credits_cents":gross_carrier,
        "customer_posted_cents":gross_posted,"reversed_cents":reversed_cents,
        "net_recovered_cents":net_recovery,"contract_fee_bps":bps,
        "net_earned_fee_cents":earned,"gross_invoiced_fee_cents":invoice,
        "fee_credit_cents":credit_notes,"gross_fee_collected_cents":collection,
        "fee_refunded_cents":refund,"net_retally_fee_cents":net_collection,
        "open_fee_receivable_cents":receivable,
        "outstanding_refund_liability_cents":refund_liability,
        "customer_net_recovery_cents":net_recovery-earned,
    }
    snap=fixture["summary"]
    check(len(snap)==1,"MISSING_POSTGRES_SNAPSHOT")
    snap=snap[0]
    for qa_key,ours in {
        "carrier_credits_cents":gross_carrier,"customer_posted_cents":gross_posted,
        "reversed_cents":reversed_cents,"invoiced_cents":invoice,
        "credited_fee_cents":credit_notes,"gross_fee_collected_cents":collection,
        "fee_refunded_cents":refund,"fee_bps":bps,
    }.items():
        check(_int(snap[qa_key],qa_key)==ours,"POSTGRES_DIVERGENCE_"+qa_key.upper())
    return {
       "status":"PASS_SIGNED_SYNTHETIC_QA_ONLY",
       "scope":"UNPUBLISHED_QA_SIGNED_FIXTURES_NOT_REAL_CUSTOMER_PROOF",
       "source_rows":len(records),"issuer_public_keys":len(keys),
       "qa_cluster":fixture["cluster"][0]["sysid"],
       "totals":independently,"real_customer_recovery_cents":0,
       "historical_findings_closed":0,
       "receipt_sha256":sha256(signed_bytes(independently)).hexdigest()
    }


def load_fixture(path:Path|None=None) -> dict:
    return json.loads((path or ROOT/"phase5c_signed_fixture.json").read_text())


if __name__=="__main__":
    print(json.dumps(verify_frozen_finances(load_fixture()),sort_keys=True,indent=2))
