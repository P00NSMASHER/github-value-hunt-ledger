import unittest

from recoveryworks import EvidenceRef, RecoveryEngine, RecoveryLedger, RuleRef
from recoveryworks.branches import from_ap_variance


def rule():
    return RuleRef(
        rule_id="invoice-authority",
        source_hash="invoice-rule-hash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="source://invoice/rule",
    )


def evidence(name):
    return EvidenceRef(
        evidence_id=name,
        source_hash=f"hash:{name}",
        locator=f"source://{name}",
        kind=name,
        verified=True,
    )


def add_claimed_case(ledger, reference, *, client_id="client-1", currency="USD"):
    observation = from_ap_variance(
        client_id=client_id,
        vendor_id="vendor-1",
        transaction_id=reference,
        transaction_date="2026-06-01",
        expected_cents=10000,
        paid_cents=15000,
        rule=rule(),
        evidence=(evidence(f"payment:{reference}"),),
        currency=currency,
    )
    finding = RecoveryEngine().evaluate(observation)
    ledger.add(finding)
    ledger.approve(finding.finding_id, "reviewer", "verified")
    ledger.authorize(finding.finding_id, f"auth:{reference}")
    ledger.mark_claimed(finding.finding_id, evidence(f"claim:{reference}"))
    return finding


class SettlementAllocationTests(unittest.TestCase):
    def test_one_settlement_can_be_explicitly_allocated_across_cases(self):
        ledger = RecoveryLedger()
        first = add_claimed_case(ledger, "inv-1")
        second = add_claimed_case(ledger, "inv-2")
        settlement = evidence("settlement:batch-1")

        ledger.mark_recovered(
            first.finding_id,
            4000,
            recovery_evidence=settlement,
            settlement_total_cents=6000,
        )
        ledger.mark_recovered(
            second.finding_id,
            2000,
            recovery_evidence=settlement,
            settlement_total_cents=6000,
        )

        self.assertEqual(ledger.rollup()["totals"]["recovered_cents"], 6000)
        self.assertEqual(ledger.get(first.finding_id).settlement_total_cents, 6000)
        self.assertEqual(ledger.get(second.finding_id).settlement_total_cents, 6000)

    def test_settlement_overallocation_is_rejected(self):
        ledger = RecoveryLedger()
        first = add_claimed_case(ledger, "inv-1")
        second = add_claimed_case(ledger, "inv-2")
        settlement = evidence("settlement:batch-1")

        ledger.mark_recovered(
            first.finding_id,
            4000,
            recovery_evidence=settlement,
            settlement_total_cents=6000,
        )
        with self.assertRaises(ValueError):
            ledger.mark_recovered(
                second.finding_id,
                3000,
                recovery_evidence=settlement,
                settlement_total_cents=6000,
            )

    def test_settlement_evidence_cannot_cross_clients(self):
        ledger = RecoveryLedger()
        first = add_claimed_case(ledger, "inv-1", client_id="client-1")
        second = add_claimed_case(ledger, "inv-2", client_id="client-2")
        settlement = evidence("settlement:batch-1")

        ledger.mark_recovered(
            first.finding_id,
            1000,
            recovery_evidence=settlement,
            settlement_total_cents=6000,
        )
        with self.assertRaises(ValueError):
            ledger.mark_recovered(
                second.finding_id,
                1000,
                recovery_evidence=settlement,
                settlement_total_cents=6000,
            )

    def test_settlement_evidence_cannot_cross_currencies(self):
        ledger = RecoveryLedger()
        first = add_claimed_case(ledger, "inv-1", currency="USD")
        second = add_claimed_case(ledger, "inv-2", currency="EUR")
        settlement = evidence("settlement:batch-1")

        ledger.mark_recovered(
            first.finding_id,
            1000,
            recovery_evidence=settlement,
            settlement_total_cents=6000,
        )
        with self.assertRaises(ValueError):
            ledger.mark_recovered(
                second.finding_id,
                1000,
                recovery_evidence=settlement,
                settlement_total_cents=6000,
            )


if __name__ == "__main__":
    unittest.main()
