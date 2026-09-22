import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.payer import (
    PayerRate,
    PayerServiceLine,
    audit_payer_lines,
)


def line(
    *,
    paid=12000,
    billed_code="99214",
    paid_code="99213",
    verified=True,
    modifier=None,
    pos="11",
):
    return PayerServiceLine(
        line_id="L1",
        claim_surrogate_id="claim-sur-1",
        payer_id="Payer A",
        service_date="2026-08-01",
        billed_procedure=billed_code,
        paid_procedure=paid_code,
        paid_cents=paid,
        units=1,
        modifier=modifier,
        place_of_service=pos,
        source_hash="remit-hash",
        source_locator="file://remit.csv#row=2",
        verified=verified,
    )


def rate(
    *,
    allowed=20000,
    verified=True,
    modifier=None,
    pos=None,
    source="rate-hash",
):
    return PayerRate(
        payer_id="Payer A",
        procedure_code="99214",
        allowed_cents_per_unit=allowed,
        effective_from="2026-01-01",
        effective_to=None,
        modifier=modifier,
        place_of_service=pos,
        source_hash=source,
        source_locator=f"file://rates.csv#{source}",
        verified=verified,
        jurisdiction="US",
    )


class PayerBranchTests(unittest.TestCase):
    def test_verified_downcode_underpayment_is_validated(self):
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(),),
            rates=(rate(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 8000)
        self.assertEqual(finding.reason, "PAYER_DOWNCODE_UNDERPAYMENT")
        self.assertTrue(finding.metadata["downcoded"])

    def test_same_code_underpayment_has_generic_reason(self):
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(paid=15000, paid_code="99214"),),
            rates=(rate(allowed=20000),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.reason, "PAYER_UNDERPAYMENT")
        self.assertFalse(finding.metadata["downcoded"])

    def test_unverified_rate_or_remittance_stays_review(self):
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(verified=True),),
            rates=(rate(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_more_specific_modifier_and_pos_rate_wins(self):
        generic = rate(allowed=18000, source="generic")
        specific = rate(
            allowed=22000,
            modifier="25",
            pos="11",
            source="specific",
        )
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(modifier="25", pos="11"),),
            rates=(generic, specific),
        )
        self.assertEqual(batch.observations[0].expected_cents, 22000)

    def test_equally_specific_overlapping_rates_fail_closed(self):
        a = rate(allowed=20000, source="a")
        b = rate(allowed=21000, source="b")
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(),),
            rates=(a, b),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "AMBIGUOUS_RATE")

    def test_missing_rate_is_exception_not_guessed(self):
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(billed_code="99999"),),
            rates=(rate(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "NO_RATE")

    def test_paid_at_or_above_expected_produces_no_recovery(self):
        batch = audit_payer_lines(
            client_id="provider",
            lines=(line(paid=20000),),
            rates=(rate(allowed=20000),),
        )
        self.assertEqual(batch.observations, ())

    def test_direct_identifier_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            PayerServiceLine(
                line_id="L1",
                claim_surrogate_id="claim-sur-1",
                payer_id="Payer A",
                service_date="2026-08-01",
                billed_procedure="99214",
                paid_cents=10000,
                units=1,
                source_hash="h",
                source_locator="file://x",
                verified=True,
                metadata={"member_id": "do-not-store-here"},
            )


if __name__ == "__main__":
    unittest.main()
