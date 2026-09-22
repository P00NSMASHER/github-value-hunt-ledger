import unittest

from recoveryworks import (
    EvidenceRef,
    FindingState,
    RecoveryEngine,
    RecoveryLedger,
    RuleRef,
)
from recoveryworks.branches import (
    from_ap_variance,
    from_construction_entitlement,
    from_duty_variance,
    from_payer_variance,
    from_utility_variance,
)


def evidence(kind="source"):
    return EvidenceRef(
        evidence_id=f"ev:{kind}",
        source_hash=f"hash:{kind}",
        locator=f"source://{kind}#1",
        kind=kind,
        verified=True,
    )


def rule(*, start="2026-01-01", end=None):
    return RuleRef(
        rule_id="rule:test",
        source_hash="rulehash",
        effective_from=start,
        effective_to=end,
        verified_controlling=True,
        source_locator="source://rule#1",
    )


class MultiBranchAdapterTests(unittest.TestCase):
    def test_all_nonfreight_adapters_produce_validated_recovery(self):
        observations = (
            from_payer_variance(
                client_id="provider", payer_id="payer", claim_id="claim-1",
                service_date="2026-06-01", expected_cents=20000, paid_cents=15000,
                rule=rule(), evidence=(evidence("835"),),
            ),
            from_utility_variance(
                client_id="portfolio", utility_id="utility", bill_id="bill-1",
                bill_date="2026-06-01", expected_cents=10000, billed_cents=13000,
                rule=rule(), evidence=(evidence("bill"),),
            ),
            from_ap_variance(
                client_id="buyer", vendor_id="vendor", transaction_id="pay-1",
                transaction_date="2026-06-01", expected_cents=10000, paid_cents=20000,
                rule=rule(), evidence=(evidence("payment"),),
            ),
            from_construction_entitlement(
                client_id="sub", counterparty_id="gc", event_id="co-7",
                event_date="2026-06-01", entitled_cents=500000, paid_cents=200000,
                rule=rule(), evidence=(evidence("change-order"),),
            ),
            from_duty_variance(
                client_id="importer", customs_counterparty_id="customs", entry_id="entry-1",
                entry_date="2026-06-01", expected_cents=10000, paid_cents=14000,
                rule=rule(), evidence=(evidence("entry"),),
            ),
        )
        engine = RecoveryEngine()
        findings = tuple(engine.evaluate(item) for item in observations)
        self.assertTrue(all(finding is not None for finding in findings))
        self.assertTrue(all(finding.state is FindingState.VALIDATED for finding in findings))
        self.assertEqual(
            [finding.potential_recovery_cents for finding in findings],
            [5000, 3000, 10000, 300000, 4000],
        )

    def test_out_of_period_authority_is_downgraded_to_review(self):
        observation = from_utility_variance(
            client_id="c", utility_id="u", bill_id="b",
            bill_date="2026-06-01", expected_cents=10000, billed_cents=12000,
            rule=rule(start="2025-01-01", end="2025-12-31"),
            evidence=(evidence("bill"),),
        )
        finding = RecoveryEngine().evaluate(observation)
        self.assertIs(finding.state, FindingState.REVIEW)
        self.assertFalse(finding.rule.verified_controlling)
        self.assertIn("authority_date_mismatch", finding.rule.metadata)

    def test_bad_transaction_date_fails_closed(self):
        with self.assertRaises(ValueError):
            from_duty_variance(
                client_id="c", customs_counterparty_id="customs", entry_id="e",
                entry_date="06/01/2026", expected_cents=100, paid_cents=200,
                rule=rule(), evidence=(evidence("entry"),),
            )


class LedgerAuditChainTests(unittest.TestCase):
    def test_lifecycle_is_hash_chained_and_idempotent(self):
        observation = from_ap_variance(
            client_id="buyer", vendor_id="vendor", transaction_id="pay-1",
            transaction_date="2026-06-01", expected_cents=10000, paid_cents=15000,
            rule=rule(), evidence=(evidence("payment"),),
        )
        finding = RecoveryEngine().evaluate(observation)
        ledger = RecoveryLedger()
        ledger.add(finding)
        ledger.add(finding)
        self.assertEqual([event.action for event in ledger.events()], ["ADDED"])

        ledger.approve(finding.finding_id, "reviewer-1", "verified source and arithmetic")
        ledger.authorize(finding.finding_id, "customer-auth-1")
        ledger.mark_claimed(finding.finding_id)
        ledger.mark_recovered(finding.finding_id, 4000, 800)

        self.assertEqual(
            [event.action for event in ledger.events()],
            ["ADDED", "APPROVED", "AUTHORIZED", "CLAIMED", "RECOVERED"],
        )
        self.assertTrue(ledger.verify_event_chain())
        self.assertEqual(len(ledger.snapshot_hash), 64)
        self.assertEqual(ledger.rollup()["totals"]["recovered_cents"], 4000)
        self.assertEqual(ledger.rollup()["totals"]["fee_cents"], 800)


if __name__ == "__main__":
    unittest.main()
