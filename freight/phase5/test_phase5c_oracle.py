"""Adversarial checks of exact signed QA financial snapshots.

Generated private keys live in memory ONLY inside tests. No private key,
real client record or credential is saved in the repository.
"""
import copy
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from freight.phase5.phase5c_oracle import (
    IndependentProofRejected, load_fixture, signed_bytes, verify_frozen_finances,
)


def resigned(fixture):
    """Fictional distinct offline signers for every role, including altered facts."""
    original=copy.deepcopy(fixture)
    keys={}
    for pub in original["keys"]:
        private=Ed25519PrivateKey.generate()
        pub["public_key_pem"]=private.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        keys[(pub["tenant_id"],pub["key_id"])]=private
    for row in original["documents"]:
        body=row["body"]
        for prop,column in [
            ("tenantId","tenant_id"),("caseId","case_id"),("recordId","record_id"),
            ("kind","kind"),("economicKey","economic_key"),("referenceId","reference_id"),
            ("amountCents","amount_cents"),("currency","currency"),("feeBps","fee_bps"),
            ("sourceHash","source_sha256"),("issuerKeyId","issuer_key_id"),
        ]:
            if prop in {"amountCents","feeBps"}:
                body[prop]=None if row[column] is None else int(row[column])
            else:
                body[prop]=row[column]
        row["signature_b64"]=__import__("base64").b64encode(
            keys[(row["tenant_id"],row["issuer_key_id"])].sign(signed_bytes(body))
        ).decode()
    return original


class Phase5CIndependentOracleTests(unittest.TestCase):
    def setUp(self):
        self.fixture=load_fixture()

    def test_positive_exact_staged_financial_replay(self):
        actual=verify_frozen_finances(self.fixture)
        self.assertEqual(actual["status"],"PASS_SIGNED_SYNTHETIC_QA_ONLY")
        t=actual["totals"]
        self.assertEqual(t["carrier_credits_cents"],1000)
        self.assertEqual(t["customer_posted_cents"],1000)
        self.assertEqual(t["reversed_cents"],500)
        self.assertEqual(t["net_recovered_cents"],500)
        self.assertEqual(t["contract_fee_bps"],3000)
        self.assertEqual(t["net_earned_fee_cents"],150)
        self.assertEqual(t["gross_invoiced_fee_cents"],300)
        self.assertEqual(t["fee_credit_cents"],150)
        self.assertEqual(t["gross_fee_collected_cents"],250)
        self.assertEqual(t["fee_refunded_cents"],100)
        self.assertEqual(t["customer_net_recovery_cents"],350)
        self.assertEqual(t["open_fee_receivable_cents"],0)
        self.assertEqual(t["outstanding_refund_liability_cents"],0)
        self.assertEqual(actual["real_customer_recovery_cents"],0)

    def test_mutated_amount_breaks_original_signature(self):
        bad=copy.deepcopy(self.fixture)
        d=next(x for x in bad["documents"] if x["kind"]=="CUSTOMER_POST")
        d["body"]["amountCents"]+=1
        with self.assertRaises(IndependentProofRejected):
            verify_frozen_finances(bad)

    def test_forged_signature_rejected(self):
        bad=copy.deepcopy(self.fixture)
        bad["documents"][2]["signature_b64"]="A"*88
        with self.assertRaisesRegex(IndependentProofRejected,"SIGNATURE_VERIFICATION_FAILED"):
            verify_frozen_finances(bad)

    def test_wrong_role_rejected_even_with_resigning(self):
        bad=copy.deepcopy(self.fixture)
        d=next(x for x in bad["documents"] if x["kind"]=="CUSTOMER_POST")
        buyer=next(x for x in bad["keys"] if x["role"]=="BUYER")
        d["issuer_key_id"]=buyer["key_id"]
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"WRONG_SIGNER_ROLE"):
            verify_frozen_finances(bad)

    def test_expired_signer_rejected(self):
        bad=copy.deepcopy(self.fixture)
        k=next(x for x in bad["keys"] if x["role"]=="CARRIER")
        k["expires_at"]="2026-10-01T00:00:00Z"
        with self.assertRaisesRegex(IndependentProofRejected,"EXPIRED_OR_REVOKED_ISSUER"):
            verify_frozen_finances(bad)

    def test_cross_tenant_record_rejected_even_if_resigned(self):
        bad=copy.deepcopy(self.fixture)
        bad["documents"][1]["tenant_id"]="SIM-OTHER-TENANT"
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"CROSS_TENANT_CASE_OR_CURRENCY"):
            verify_frozen_finances(bad)

    def test_wrong_currency_posting_rejected(self):
        bad=copy.deepcopy(self.fixture)
        bad["documents"][2]["currency"]="EUR"
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"CROSS_TENANT_CASE_OR_CURRENCY"):
            verify_frozen_finances(bad)

    def test_orphan_reversal_rejected_even_with_valid_new_signature(self):
        bad=copy.deepcopy(self.fixture)
        reversal=next(x for x in bad["documents"] if x["kind"]=="CUSTOMER_REVERSAL")
        reversal["reference_id"]="SIM-NO-SUCH-POSTING"
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"ORPHAN_RECOVERY_REVERSAL"):
            verify_frozen_finances(bad)

    def test_double_post_of_one_carrier_credit_rejected(self):
        bad=copy.deepcopy(self.fixture)
        post=next(x for x in bad["documents"] if x["kind"]=="CUSTOMER_POST")
        extra=copy.deepcopy(post)
        extra["record_id"]="SIM-P5C-DUP-POST"
        extra["economic_key"]="SIM-P5C-ECO-DUP-POST"
        extra["source_sha256"]="f"*64
        extra["body"]["recordId"]=extra["record_id"]
        extra["body"]["economicKey"]=extra["economic_key"]
        extra["body"]["sourceHash"]=extra["source_sha256"]
        bad["documents"].append(extra)
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"DUPLICATE_CUSTOMER_POST"):
            verify_frozen_finances(bad)

    def test_carrier_credit_relabel_using_same_source_rejected(self):
        bad=copy.deepcopy(self.fixture)
        c=next(x for x in bad["documents"] if x["kind"]=="CARRIER_CREDIT")
        dup=copy.deepcopy(c)
        dup["record_id"]="SIM-P5C-CARRIER-RELABEL"
        dup["economic_key"]="SIM-P5C-ECO-CARRIER-RELABEL"
        bad["documents"].append(dup)
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"RELABELLED_DUPLICATE_DOCUMENT"):
            verify_frozen_finances(bad)

    def test_wrong_historical_fee_percentage_rejected(self):
        bad=copy.deepcopy(self.fixture)
        contract=next(x for x in bad["documents"] if x["kind"]=="CONTRACT")
        contract["fee_bps"]=5000
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"FEE_INVOICED_BALANCE_WRONG"):
            verify_frozen_finances(bad)

    def test_hidden_refund_or_cash_balance_rejected(self):
        bad=copy.deepcopy(self.fixture)
        bad["summary"][0]["fee_refunded_cents"]="0"
        with self.assertRaisesRegex(IndependentProofRejected,"POSTGRES_DIVERGENCE_FEE_REFUNDED_CENTS"):
            verify_frozen_finances(bad)

    def test_fake_production_cash_label_rejected(self):
        bad=copy.deepcopy(self.fixture)
        bad["actualCustomerRecoveryProven"]=True
        with self.assertRaisesRegex(IndependentProofRejected,"FAKE_PRODUCTION_CERTIFICATION"):
            verify_frozen_finances(bad)

    def test_wrong_provider_event_rejected(self):
        bad=copy.deepcopy(self.fixture)
        c=next(x for x in bad["documents"] if x["kind"]=="CARRIER_CREDIT")
        c["body"]["providerEventId"]="pe_unverified"
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"UNSUPPORTED_CARRIER_CREDIT_EVENT"):
            verify_frozen_finances(bad)

    def test_excess_carrier_credit_rejected_with_resigned_facts(self):
        bad=copy.deepcopy(self.fixture)
        c=next(x for x in bad["documents"] if x["kind"]=="CARRIER_CREDIT")
        c["amount_cents"]="800"
        bad=resigned(bad)
        with self.assertRaisesRegex(IndependentProofRejected,"UNSUPPORTED_CARRIER_CREDIT_EVENT"):
            verify_frozen_finances(bad)


if __name__=="__main__":
    unittest.main()
