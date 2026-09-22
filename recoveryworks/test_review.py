import unittest

from recoveryworks import EvidenceRef, RecoveryEngine, RecoveryLedger, RuleRef
from recoveryworks.branches import from_ap_variance
from recoveryworks.review import (
    AWAITING_AUTHORIZATION,
    EVIDENCE_REVIEW,
    HUMAN_REVIEW,
    READY_TO_SUBMIT,
    build_review_queue,
    review_queue_summary,
)


def rule(verified=True):
    return RuleRef(
        rule_id="r", source_hash="rh", effective_from="2026-01-01",
        effective_to=None, verified_controlling=verified,
        source_locator="source://rule",
    )


def evidence(name, verified=True):
    return EvidenceRef(
        evidence_id=name, source_hash=f"h:{name}", locator=f"source://{name}",
        kind="payment", verified=verified,
    )


def finding(reference, *, paid=15000, currency="USD", rule_verified=True, evidence_verified=True):
    return RecoveryEngine().evaluate(from_ap_variance(
        client_id="client-1", vendor_id="vendor", transaction_id=reference,
        transaction_date="2026-06-01", expected_cents=10000,
        paid_cents=paid, rule=rule(rule_verified),
        evidence=(evidence(reference, evidence_verified),), currency=currency,
    ))


class ReviewQueueTests(unittest.TestCase):
    def test_queue_separates_evidence_review_human_review_authorization_and_ready(self):
        ledger = RecoveryLedger()
        evidence_case = finding("evidence", rule_verified=False)
        human_case = finding("human", paid=13000)
        auth_case = finding("auth", paid=14000)
        ready_case = finding("ready", paid=16000)

        for item in (evidence_case, human_case, auth_case, ready_case):
            ledger.add(item)

        ledger.approve(auth_case.finding_id, "reviewer", "checked")
        ledger.approve(ready_case.finding_id, "reviewer", "checked")
        ledger.authorize(ready_case.finding_id, "auth-ready")

        items = build_review_queue(ledger)
        by_id = {item.finding_id: item for item in items}
        self.assertEqual(by_id[evidence_case.finding_id].queue, EVIDENCE_REVIEW)
        self.assertEqual(by_id[human_case.finding_id].queue, HUMAN_REVIEW)
        self.assertEqual(by_id[auth_case.finding_id].queue, AWAITING_AUTHORIZATION)
        self.assertEqual(by_id[ready_case.finding_id].queue, READY_TO_SUBMIT)

    def test_amount_rank_is_only_within_same_queue_and_currency(self):
        ledger = RecoveryLedger()
        usd_small = finding("usd-small", paid=12000, currency="USD")
        usd_large = finding("usd-large", paid=18000, currency="USD")
        eur = finding("eur", paid=19000, currency="EUR")
        for item in (usd_small, usd_large, eur):
            ledger.add(item)

        rows = build_review_queue(ledger)
        by_ref = {ledger.get(row.finding_id).finding.reference: row for row in rows}
        self.assertEqual(by_ref["usd-large"].rank_in_queue_currency, 1)
        self.assertEqual(by_ref["usd-small"].rank_in_queue_currency, 2)
        self.assertEqual(by_ref["eur"].rank_in_queue_currency, 1)

    def test_summary_keeps_currency_amounts_separate(self):
        ledger = RecoveryLedger()
        ledger.add(finding("usd", paid=15000, currency="USD"))
        ledger.add(finding("eur", paid=17000, currency="EUR"))
        summary = review_queue_summary(build_review_queue(ledger))
        bucket = summary["queues"][HUMAN_REVIEW]["currencies"]
        self.assertEqual(bucket["USD"]["potential_recovery_cents"], 5000)
        self.assertEqual(bucket["EUR"]["potential_recovery_cents"], 7000)


if __name__ == "__main__":
    unittest.main()
