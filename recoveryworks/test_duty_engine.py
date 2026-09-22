from decimal import Decimal
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.engines.duty import (
    DutyRate,
    ImportEntryLine,
    detect_duty_overpayments,
    expected_duty_cents,
)


def rate(*, verified=True, bps=500, specific="0", rate_id="r1"):
    return DutyRate(
        rate_id=rate_id, hts_code="1234.56.7890",
        effective_from="2026-01-01", effective_to=None,
        ad_valorem_bps=bps, specific_cents_per_unit=Decimal(specific),
        source_hash=f"ratehash:{rate_id}", locator=f"source://hts#{rate_id}",
        verified=verified,
    )


def line(*, verified=True, paid=6000, value=100000, quantity="0"):
    return ImportEntryLine(
        entry_id="entry-1", line_id="1", entry_date="2026-06-01",
        hts_code="1234.56.7890", customs_value_cents=value,
        quantity=Decimal(quantity), paid_duty_cents=paid, currency="USD",
        source_hash="entryhash", locator="source://entry#1", verified=verified,
    )


class DutyRecoveryEngineTests(unittest.TestCase):
    def test_ad_valorem_overpayment_is_validated(self):
        r = rate(bps=500)
        l = line(value=100000, paid=6000)
        self.assertEqual(expected_duty_cents(r, l), 5000)
        obs = detect_duty_overpayments(
            client_id="importer", customs_counterparty_id="CBP",
            rates=(r,), lines=(l,),
        )
        finding = RecoveryEngine().evaluate(obs[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 1000)

    def test_specific_duty_component_is_added(self):
        r = rate(bps=0, specific="12.5")
        l = line(value=0, quantity="10", paid=200)
        self.assertEqual(expected_duty_cents(r, l), 125)

    def test_unverified_entry_stays_review(self):
        obs = detect_duty_overpayments(
            client_id="importer", customs_counterparty_id="CBP",
            rates=(rate(),), lines=(line(verified=False),),
        )
        self.assertIs(RecoveryEngine().evaluate(obs[0]).state, FindingState.REVIEW)

    def test_no_overpayment_produces_no_observation(self):
        obs = detect_duty_overpayments(
            client_id="importer", customs_counterparty_id="CBP",
            rates=(rate(bps=500),), lines=(line(paid=5000),),
        )
        self.assertEqual(obs, ())

    def test_conflicting_rates_fail_closed(self):
        with self.assertRaises(ValueError):
            detect_duty_overpayments(
                client_id="importer", customs_counterparty_id="CBP",
                rates=(rate(bps=500, rate_id="a"), rate(bps=700, rate_id="b")),
                lines=(line(),),
            )


if __name__ == "__main__":
    unittest.main()
