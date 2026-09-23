from recoveryworks.test_support import source_hash as H
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.rebate import (
    RebateMeasurementBasis,
    RebateProgram,
    RebatePurchaseLine,
    RebateSettlement,
    RebateTier,
    RebateTierMode,
    audit_rebates,
    calculate_rebate,
)


def program(mode=RebateTierMode.INCREMENTAL, basis=RebateMeasurementBasis.UNITS, *, verified=True):
    return RebateProgram(
        supplier_id="Supplier A",
        program_id="2026-Q3",
        period_start="2026-07-01",
        period_end="2026-09-30",
        tier_mode=mode,
        measurement_basis=basis,
        tiers=(
            RebateTier("0", "100", 0),
            RebateTier("100", "200", 500),
            RebateTier("200", None, 1000),
        ),
        source_hash=H("program-hash"),
        source_locator="file://program.json#0",
        verified=verified,
    )


def purchase(pid="P-1", *, qty="250", spend=250000, verified=True, when="2026-08-01"):
    return RebatePurchaseLine(
        purchase_id=pid,
        supplier_id="Supplier A",
        program_id="2026-Q3",
        purchase_date=when,
        quantity=qty,
        net_spend_cents=spend,
        source_hash=H(f"purchase-{pid}"),
        source_locator=f"file://purchases.csv#{pid}",
        verified=verified,
    )


def settlement(amount=7500, *, verified=True, sid="S-1"):
    return RebateSettlement(
        settlement_id=sid,
        supplier_id="Supplier A",
        program_id="2026-Q3",
        amount_received_cents=amount,
        settlement_date="2026-10-15",
        source_hash=H(f"settlement-{sid}"),
        source_locator=f"file://settlements.csv#{sid}",
        verified=verified,
    )


class RebateBranchTests(unittest.TestCase):
    def test_retroactive_and_incremental_tiers_are_materially_different(self):
        lines = (purchase(),)
        retro = calculate_rebate(
            program(mode=RebateTierMode.RETROACTIVE),
            lines,
        )
        incremental = calculate_rebate(
            program(mode=RebateTierMode.INCREMENTAL),
            lines,
        )
        self.assertEqual(retro.expected_cents, 25000)
        self.assertEqual(incremental.expected_cents, 10000)

    def test_incremental_spend_basis(self):
        spend_program = RebateProgram(
            supplier_id="Supplier A",
            program_id="2026-Q3",
            period_start="2026-07-01",
            period_end="2026-09-30",
            tier_mode=RebateTierMode.INCREMENTAL,
            measurement_basis=RebateMeasurementBasis.SPEND,
            tiers=(
                RebateTier("0", "1000", 0),
                RebateTier("1000", "2000", 500),
                RebateTier("2000", None, 1000),
            ),
            source_hash=H("program-spend-hash"),
            source_locator="file://program-spend.json#0",
            verified=True,
        )
        result = calculate_rebate(
            spend_program,
            (purchase(qty="25", spend=250000),),
        )
        self.assertEqual(result.expected_cents, 10000)

    def test_verified_underpayment_becomes_validated_recovery(self):
        batch = audit_rebates(
            client_id="client",
            programs=(program(),),
            purchases=(purchase(),),
            settlements=(settlement(7500),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 10000)
        self.assertEqual(finding.actual_cents, 7500)
        self.assertEqual(finding.potential_recovery_cents, 2500)
        self.assertEqual(finding.reason, "REBATE_UNDERPAYMENT")

    def test_unverified_settlement_keeps_candidate_in_review(self):
        batch = audit_rebates(
            client_id="client",
            programs=(program(),),
            purchases=(purchase(),),
            settlements=(settlement(7500, verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_missing_settlement_evidence_fails_closed(self):
        batch = audit_rebates(
            client_id="client",
            programs=(program(),),
            purchases=(purchase(),),
            settlements=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "NO_SETTLEMENT_EVIDENCE")

    def test_duplicate_purchase_blocks_program(self):
        batch = audit_rebates(
            client_id="client",
            programs=(program(),),
            purchases=(purchase("P-1"), purchase("P-1")),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.observations, ())
        codes = {item.code for item in batch.exceptions}
        self.assertIn("DUPLICATE_PURCHASE_ID", codes)
        self.assertIn("PROGRAM_BLOCKED_BY_DUPLICATE_PURCHASE", codes)

    def test_out_of_period_purchase_is_not_counted(self):
        batch = audit_rebates(
            client_id="client",
            programs=(program(),),
            purchases=(
                purchase("P-IN", qty="250", spend=250000),
                purchase("P-OUT", qty="100", spend=100000, when="2026-10-01"),
            ),
            settlements=(settlement(7500),),
        )
        self.assertEqual(len(batch.observations), 1)
        self.assertEqual(batch.exceptions[0].code, "OUT_OF_PERIOD_PURCHASE")
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.potential_recovery_cents, 2500)

    def test_noncontiguous_tiers_are_rejected(self):
        with self.assertRaises(ValueError):
            RebateProgram(
                supplier_id="S",
                program_id="P",
                period_start="2026-01-01",
                period_end="2026-12-31",
                tier_mode=RebateTierMode.RETROACTIVE,
                measurement_basis=RebateMeasurementBasis.UNITS,
                tiers=(
                    RebateTier("0", "100", 0),
                    RebateTier("101", None, 500),
                ),
                source_hash=H("h"),
                source_locator="file://x",
                verified=True,
            )


if __name__ == "__main__":
    unittest.main()
