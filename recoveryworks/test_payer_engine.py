import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.engines.payer import (
    FeeScheduleRate,
    PayerServiceLine,
    detect_payer_underpayments,
)


def rate(*, verified=True, amount=10000, rate_id="r1", start="2026-01-01", end=None):
    return FeeScheduleRate(
        payer_id="payer-1", rate_id=rate_id, procedure_code="99214",
        effective_from=start, effective_to=end, allowed_cents_per_unit=amount,
        source_hash=f"ratehash:{rate_id}", locator=f"source://rate#{rate_id}",
        verified=verified,
    )


def line(*, verified=True, paid=7500, units=1, service_date="2026-06-01"):
    return PayerServiceLine(
        claim_id="claim-1", service_line_id="1", service_date=service_date,
        procedure_code="99214", units=units, paid_cents=paid, currency="USD",
        source_hash="835hash", locator="source://835#claim-1/1", verified=verified,
    )


class PayerRecoveryEngineTests(unittest.TestCase):
    def test_exact_rate_underpayment_is_validated(self):
        obs = detect_payer_underpayments(
            client_id="provider-1", payer_id="payer-1",
            rates=(rate(),), service_lines=(line(),),
        )
        self.assertEqual(len(obs), 1)
        finding = RecoveryEngine().evaluate(obs[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 2500)

    def test_units_are_deterministic_integer_multiplier(self):
        obs = detect_payer_underpayments(
            client_id="provider-1", payer_id="payer-1",
            rates=(rate(amount=5000),), service_lines=(line(paid=7000, units=2),),
        )
        finding = RecoveryEngine().evaluate(obs[0])
        self.assertEqual(finding.expected_cents, 10000)
        self.assertEqual(finding.potential_recovery_cents, 3000)

    def test_unverified_835_evidence_keeps_review(self):
        obs = detect_payer_underpayments(
            client_id="provider-1", payer_id="payer-1",
            rates=(rate(),), service_lines=(line(verified=False),),
        )
        self.assertIs(RecoveryEngine().evaluate(obs[0]).state, FindingState.REVIEW)

    def test_rate_outside_service_date_is_not_used(self):
        obs = detect_payer_underpayments(
            client_id="provider-1", payer_id="payer-1",
            rates=(rate(start="2025-01-01", end="2025-12-31"),),
            service_lines=(line(service_date="2026-06-01"),),
        )
        self.assertEqual(obs, ())

    def test_conflicting_applicable_rates_fail_closed(self):
        with self.assertRaises(ValueError):
            detect_payer_underpayments(
                client_id="provider-1", payer_id="payer-1",
                rates=(rate(amount=10000, rate_id="a"), rate(amount=11000, rate_id="b")),
                service_lines=(line(),),
            )

    def test_no_underpayment_produces_no_observation(self):
        obs = detect_payer_underpayments(
            client_id="provider-1", payer_id="payer-1",
            rates=(rate(amount=10000),), service_lines=(line(paid=10000),),
        )
        self.assertEqual(obs, ())


if __name__ == "__main__":
    unittest.main()
