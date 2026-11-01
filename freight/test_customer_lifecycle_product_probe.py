"""Tests actual RecoveryOS payment domain objects with synthetic customer flows only."""
import unittest

from freight.customer_lifecycle_product_probe import (
    SyntheticCustomerCase, run_synthetic_customer_case,
)
from hashlib import sha256


def case(**changes):
    body = dict(
        scenario_id="SC-0000001", customer_id="FCUST-00001",
        carrier_id="FICTIONAL-CARRIER-004", invoice_id="INV-0000001",
        source_sha256=sha256(b"FICTIONAL_CONTRACT_AND_INVOICE").hexdigest(),
        truth="POSITIVE", independently_validated_cents=50000,
        contract_accepted=True, claim_authorized=True,
        receipt_reconciled=True, fee_bps=2000,
    )
    body.update(changes)
    return SyntheticCustomerCase(**body)


class TestActualPaymentCustomerBridge(unittest.TestCase):
    def test_settled_and_separately_reconciled_fee(self):
        receipt = run_synthetic_customer_case(case())
        self.assertEqual(receipt.real_orchestrator_state, "SETTLED")
        self.assertEqual(receipt.provider_settled_cents, 50000)
        self.assertEqual(receipt.customer_reconciled_cents, 50000)
        self.assertEqual(receipt.fee_eligible_cents, 10000)

    def test_provider_settled_but_customer_not_reconciled(self):
        receipt = run_synthetic_customer_case(case(receipt_reconciled=False))
        self.assertEqual(receipt.provider_settled_cents, 50000)
        self.assertEqual(receipt.customer_reconciled_cents, 0)
        self.assertEqual(receipt.fee_eligible_cents, 0)

    def test_reversal_removes_fee_eligibility(self):
        receipt = run_synthetic_customer_case(case(),(
            "SUBMITTED","ACCEPTED","SETTLED","REVERSED"))
        self.assertEqual(receipt.real_orchestrator_state, "REVERSED")
        self.assertEqual(receipt.provider_settled_cents, 0)
        self.assertEqual(receipt.fee_eligible_cents, 0)

    def test_review_truth_fails_closed(self):
        receipt = run_synthetic_customer_case(case(truth="REVIEW"))
        self.assertEqual(receipt.assessment, "CLAIM_BLOCKED")
        self.assertEqual(receipt.real_orchestrator_state, "NOT_PREPARED")

    def test_negative_truth_fails_closed(self):
        receipt = run_synthetic_customer_case(case(truth="NEGATIVE"))
        self.assertEqual(receipt.provider_settled_cents, 0)

    def test_missing_contract_fails_closed(self):
        receipt = run_synthetic_customer_case(case(contract_accepted=False))
        self.assertEqual(receipt.fee_eligible_cents, 0)

    def test_revoked_authorization_fails_closed(self):
        receipt = run_synthetic_customer_case(case(authorization_revoked=True))
        self.assertEqual(receipt.real_orchestrator_state, "NOT_PREPARED")

    def test_missing_claim_authorization_fails_closed(self):
        receipt = run_synthetic_customer_case(case(claim_authorized=False))
        self.assertEqual(receipt.assessment, "CLAIM_BLOCKED")

    def test_zero_validated_amount_fails_closed(self):
        receipt = run_synthetic_customer_case(case(independently_validated_cents=0))
        self.assertEqual(receipt.provider_settled_cents, 0)

    def test_invalid_source_hash_rejected(self):
        with self.assertRaises(ValueError):
            run_synthetic_customer_case(case(source_sha256="NOT_A_HASH"))

    def test_invalid_external_identifier_rejected(self):
        with self.assertRaises(ValueError):
            run_synthetic_customer_case(case(customer_id="REAL-CUSTOMER-1234"))

    def test_fake_provider_cannot_skip_acceptance_state(self):
        with self.assertRaises(ValueError):
            run_synthetic_customer_case(case(),("SUBMITTED","SETTLED"))

    def test_fee_rate_bounds_rejected(self):
        with self.assertRaises(ValueError):
            run_synthetic_customer_case(case(fee_bps=10001))


if __name__ == "__main__":
    unittest.main()
