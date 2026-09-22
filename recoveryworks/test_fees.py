import unittest

from recoveryworks import Branch, EvidenceRef, RecoveryEngine, RuleRef
from recoveryworks.branches import from_ap_variance
from recoveryworks.fees import (
    FLOOR,
    FeeAgreement,
    assess_fee,
    calculate_fee_cents,
)


def finding():
    observation = from_ap_variance(
        client_id="client-1",
        vendor_id="vendor",
        transaction_id="inv-1",
        transaction_date="2026-06-01",
        expected_cents=10000,
        paid_cents=15000,
        rule=RuleRef(
            rule_id="r", source_hash="rh", effective_from="2026-01-01",
            effective_to=None, verified_controlling=True,
            source_locator="source://rule",
        ),
        evidence=(EvidenceRef(
            evidence_id="e", source_hash="eh", locator="source://e",
            kind="payment", verified=True,
        ),),
    )
    return RecoveryEngine().evaluate(observation)


def agreement(**overrides):
    values = dict(
        agreement_id="fee-1",
        client_id="client-1",
        fee_bps=2000,
        branches=(Branch.AP,),
        source_hash="agreementhash",
        locator="source://fee-agreement",
        verified=True,
        currency="USD",
    )
    values.update(overrides)
    return FeeAgreement(**values)


class FeeAgreementTests(unittest.TestCase):
    def test_exact_contingency_fee(self):
        assessment = assess_fee(finding(), 4000, agreement())
        self.assertEqual(assessment.fee_cents, 800)
        self.assertEqual(len(assessment.proof_hash), 64)

    def test_half_up_rounding_is_deterministic(self):
        self.assertEqual(calculate_fee_cents(999, 1250), 125)
        self.assertEqual(calculate_fee_cents(999, 1250, FLOOR), 124)

    def test_wrong_client_branch_or_currency_fails_closed(self):
        f = finding()
        with self.assertRaises(ValueError):
            assess_fee(f, 1000, agreement(client_id="other"))
        with self.assertRaises(ValueError):
            assess_fee(f, 1000, agreement(branches=(Branch.UTILITY,)))
        with self.assertRaises(ValueError):
            assess_fee(f, 1000, agreement(currency="EUR"))

    def test_unverified_agreement_fails_closed(self):
        with self.assertRaises(ValueError):
            assess_fee(finding(), 1000, agreement(verified=False))


if __name__ == "__main__":
    unittest.main()
