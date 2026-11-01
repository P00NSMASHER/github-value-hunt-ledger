"""Independent source-verification of Customers B and C in actual isolated QA.

The signed contracts and SQL summaries are frozen staging observations. GitHub
CI independently verifies signatures and values, but does not call live Floot.
A no-recovery outcome is NOT proof that the invoice was accurately rated.
"""
import base64
import copy
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from freight.phase5.phase5c_oracle import signed_bytes
from freight.lab_phase3_simulated_pilot import simulated_cohort

HERE=Path(__file__).parent


def verify_bc(fixture):
    if fixture.get("scope")!="TWO_ADDITIONAL_FICTIONAL_QA_CUSTOMERS":
        raise ValueError("INVALID_BC_SOURCE_CLASSIFICATION")
    if fixture.get("actual_company_revenue_cents")!=0 or fixture.get("actual_customer_recovery_cents")!=0:
        raise ValueError("UNSUPPORTED_REAL_REVENUE")
    if fixture.get("cluster")!=[{"sysid":"7694294930552894346"}]:
        raise ValueError("DIFFERENT_OR_UNKNOWN_POSTGRESQL_CLUSTER")
    cases=fixture.get("cases",[]);docs=fixture.get("documents",[])
    keys={(x["tenant_id"],x["key_id"]):x for x in fixture.get("keys",[])}
    summaries={x["case_id"]:x for x in fixture.get("summary",[])}
    if len(cases)!=2 or len(docs)!=2 or len(keys)!=2 or len(summaries)!=2:
        raise ValueError("MISSING_STAGED_CUSTOMER_EVIDENCE")
    for case in cases:
        case_id=case["case_id"];tenant=case["tenant_id"]
        contract=[x for x in docs if x["case_id"]==case_id]
        if len(contract)!=1:
            raise ValueError("DUPLICATED_CONTRACT")
        row=contract[0];body=row["body"]
        if row["kind"]!="CONTRACT" or row["amount_cents"] not in ("0",0):
            raise ValueError("NO_RECOVERY_CONTRACT_INVALID")
        if row["fee_bps"]!=3000 or body["feeBps"]!=3000 or body["amountCents"]!=0:
            raise ValueError("INVALID_HISTORICAL_FEE_RATE")
        if (row["tenant_id"],row["case_id"],row["currency"],body["tenantId"],
            body["customerId"],body["invoiceId"]) != (
            tenant,case_id,"USD",tenant,case["customer_id"],case["invoice_id"]):
            raise ValueError("CROSS_TENANT_CUSTOMER_OR_INVOICE")
        issuer=keys.get((tenant,row["issuer_key_id"]))
        if not issuer or issuer["role"]!="BUYER":
            raise ValueError("WRONG_CONTRACT_SIGNER_ROLE")
        try:
            load_pem_public_key(issuer["public_key_pem"].encode()).verify(
                base64.b64decode(row["signature_b64"],validate=True),signed_bytes(body))
        except Exception as ex:
            raise ValueError("BAD_CONTRACT_SIGNATURE") from ex
        s=summaries[case_id]
        for k in ("customer_posted_cents","reversed_cents","invoiced_cents",
                  "credited_fee_cents","gross_fee_collected_cents","fee_refunded_cents"):
            if int(s[k])!=0:
                raise ValueError("UNSUPPORTED_CUSTOMER_CASH_OR_FEE_"+k.upper())
        if int(s["fee_bps"])!=3000:
            raise ValueError("CONTRACT_RATE_AND_STAGING_DISAGREE")
    if str(fixture["negative_count"][0]["stored_negative_docs"])!="0":
        raise ValueError("REJECTED_DOCUMENT_PERSISTED")
    obs=fixture["observed_requests"]
    if len(obs)!=4 or set(x["result"] for x in obs)!={"REJECTED_NO_SETTLEMENT_EVENT",
                                                       "REJECTED_UNAUTHORIZED_FEE_INVOICE"}:
        raise ValueError("MISSING_NEGATIVE_APPLICATION_OBSERVATIONS")
    if any(x["http_status"]!=400 for x in obs):
        raise ValueError("UNVERIFIED_APPLICATION_REJECTION")
    return {"scope":"SIGNED_SYNTHETIC_QA_NO_RECOVERY_BC",
            "customers":2,"accepted_signed_historical_contracts":2,
            "rejected_unsupported_credit_and_fee_attempts":4,
            "simulated_customer_recovered_cents":0,
            "actual_retally_revenue_cents":0}


class Phase5DBCCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((HERE/"phase5d_bc_qa_fixtures.json").read_text())

    def test_staging_signed_no_recovery_evidence(self):
        r=verify_bc(self.fixture)
        self.assertEqual(r["customers"],2)

    def test_cross_tenant_contract_tamper(self):
        f=copy.deepcopy(self.fixture)
        f["documents"][0]["body"]["tenantId"]="SIM-WRONG-CUSTOMER"
        with self.assertRaises(ValueError):
            verify_bc(f)

    def test_signed_contract_fee_rate_tamper(self):
        f=copy.deepcopy(self.fixture)
        f["documents"][0]["body"]["feeBps"]=5000
        with self.assertRaises(ValueError):
            verify_bc(f)

    def test_false_earned_fee_rejected(self):
        f=copy.deepcopy(self.fixture)
        f["summary"][0]["invoiced_cents"]="1"
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_CUSTOMER_CASH_OR_FEE"):
            verify_bc(f)

    def test_customer_B_zero_claim_model(self):
        cohort=simulated_cohort()["cohort"]
        case=next(x for x in cohort if x["synthetic_customer_id"]=="SIM-PARCEL-OPERATOR")
        self.assertEqual(case["economic_scenario"]["expected_gross_fee_cents"],0)
        self.assertEqual(case["simulated_accounting"]["simulated_net_recovered_cents"],0)
        self.assertEqual(case["audit_upfront_fee_cents"],0)
        self.assertLess(case["economic_scenario"]["expected_net_margin_cents"],0)

    def test_customer_C_model_signals_economic_stop(self):
        cohort=simulated_cohort()["cohort"]
        case=next(x for x in cohort if x["synthetic_customer_id"]=="SIM-INDUSTRIAL-SHIPPER")
        self.assertLess(case["economic_scenario"]["expected_net_margin_cents"],0)
        self.assertEqual(case["observed_real_recovery_cents"],0)
        self.assertEqual(case["simulated_accounting"]["simulated_net_recovered_cents"],0)


if __name__=="__main__":
    unittest.main()
