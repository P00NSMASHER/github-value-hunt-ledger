import unittest

from freight.finding_factory import ChargeRule, InvoiceCharge, derive_charge
from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.freight import from_freight_derivation


def charge():
    return InvoiceCharge(
        buyer_id="buyer-1",
        business_unit="bu-1",
        invoice_id="inv-1",
        shipment_id="ship-1",
        customer_id="cust-1",
        carrier_id="carrier-1",
        currency="USD",
        charge_id="charge-1",
        charge_code="LIFTGATE",
        service_date="2026-06-15",
        quantity_units=1,
        billed_cents=15000,
        source_hash="invoice-source-hash",
    )


def rule(*, document_hash="contract-source-hash", verified=True):
    return ChargeRule(
        buyer_id="buyer-1",
        business_unit="bu-1",
        customer_id="cust-1",
        carrier_id="carrier-1",
        currency="USD",
        authority_document_id="contract-2026",
        charge_code="LIFTGATE",
        pricing_model="FIXED",
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        document_source_hash=document_hash,
        verified_controlling_authority=verified,
        fixed_cents=10000,
    )


class FreightRecoveryIntegrationTests(unittest.TestCase):
    def test_real_freight_derivation_preserves_rule_window_and_source(self):
        c = charge()
        r = rule()
        derivation = derive_charge(c, (r,))
        observation = from_freight_derivation(derivation, c, r)
        finding = RecoveryEngine().evaluate(observation)

        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 5000)
        self.assertEqual(finding.rule.effective_from, "2026-01-01")
        self.assertEqual(finding.rule.effective_to, "2026-12-31")
        self.assertEqual(finding.rule.source_hash, "contract-source-hash")
        self.assertEqual(finding.metadata["freight_rule_hash"], r.rule_hash)

    def test_different_rule_cannot_validate_existing_derivation(self):
        c = charge()
        original = rule()
        derivation = derive_charge(c, (original,))
        tampered = rule(document_hash="different-contract-source")
        observation = from_freight_derivation(derivation, c, tampered)
        finding = RecoveryEngine().evaluate(observation)
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_unverified_freight_rule_stays_review(self):
        c = charge()
        r = rule(verified=False)
        derivation = derive_charge(c, (r,))
        self.assertIsNotNone(derivation.finding)
        observation = from_freight_derivation(derivation, c, r)
        finding = RecoveryEngine().evaluate(observation)
        self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
