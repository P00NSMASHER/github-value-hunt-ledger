"""Real RecoveryOS payment-domain integration requires fictional invoice-owner scope."""
import unittest
from dataclasses import replace
from hashlib import sha256

from freight.customer_lifecycle_product_probe import SyntheticCustomerCase
from freight.customer_scope_recovery_guard import (
    issue_fictional_binding, guard_fictional_customer_scope,
    run_guarded_synthetic_customer_case,
)


def fixtures():
    case = SyntheticCustomerCase(
        scenario_id="SC-0000001",customer_id="FCUST-00001",
        carrier_id="FICTIONAL-CARRIER-004",invoice_id="INV-0000001",
        source_sha256=sha256(b"fictional-source").hexdigest(),
        truth="POSITIVE",independently_validated_cents=50000,
        contract_accepted=True,claim_authorized=True,receipt_reconciled=True,fee_bps=2000,
    )
    binding = issue_fictional_binding(
        scenario_id=case.scenario_id,customer_id=case.customer_id,
        source_customer_id="CUSTOMER-0001",carrier_id=case.carrier_id,
        invoice_id=case.invoice_id,evidence_sha256=case.source_sha256,
        consent_reference="SYNTH-APPROVED-CASE-1",
        valid_from=10,valid_until=200,
    )
    return case,binding


class TestSyntheticScopeGuard(unittest.TestCase):
    def test_authored_binding_executes_real_payment_domain(self):
        case,binding=fixtures()
        receipt=run_guarded_synthetic_customer_case(case,binding,at_minute=100)
        self.assertEqual(receipt.real_orchestrator_state,"SETTLED")
        self.assertEqual(receipt.fee_eligible_cents,10000)

    def test_unreconciled_customer_credit_cannot_generate_fee(self):
        case,binding=fixtures()
        result=run_guarded_synthetic_customer_case(replace(case,receipt_reconciled=False),binding,at_minute=100)
        self.assertEqual(result.provider_settled_cents,50000)
        self.assertEqual(result.fee_eligible_cents,0)

    def test_expired_or_future_contract_blocked(self):
        case,binding=fixtures()
        for t in (9,200):
            with self.assertRaises(ValueError):
                guard_fictional_customer_scope(case,binding,at_minute=t)

    def test_revocation_before_claim_blocks(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(case,replace(binding,revoked_at=50),at_minute=100)

    def test_customer_mismatch_blocks(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(replace(case,customer_id="FCUST-00002"),binding,at_minute=100)

    def test_invoice_mismatch_blocks(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(replace(case,invoice_id="INV-0000002"),binding,at_minute=100)

    def test_source_hash_mismatch_blocks(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(replace(case,source_sha256="0"*64),binding,at_minute=100)

    def test_tampered_binding_checksum_blocks(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(case,replace(binding,source_customer_id="CUSTOMER-0088"),at_minute=100)

    def test_without_binding_fails_closed(self):
        case,_=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(case,None,at_minute=100)

    def test_without_signed_engagement_fails_closed(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(replace(case,contract_accepted=False),binding,at_minute=100)

    def test_unauthorized_carrier_proposal_fails_closed(self):
        case,binding=fixtures()
        with self.assertRaises(ValueError):
            guard_fictional_customer_scope(replace(case,claim_authorized=False),binding,at_minute=100)

    def test_reversed_carrier_settlement_has_no_collected_fee(self):
        case,binding=fixtures()
        response=run_guarded_synthetic_customer_case(case,binding,at_minute=100,
               provider_states=("SUBMITTED","ACCEPTED","SETTLED","REVERSED"))
        self.assertEqual(response.fee_eligible_cents,0)

if __name__=="__main__":
    unittest.main()
