from recoveryworks.test_support import source_hash as H
import hashlib
import unittest

from recoveryworks import (
    Branch,
    DurableRecoveryLedger,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    RuleRef,
    SettlementEvidence,
)
from recoveryworks.report import build_scan360_report


def make_finding(branch, client_id, expected, actual, *, verified=True, ref="r"):
    return RecoveryEngine().evaluate(RecoveryObservation(
        branch=branch,
        client_id=client_id,
        counterparty_id=f"cp-{branch.value}",
        reference=ref,
        currency="USD",
        expected_cents=expected,
        actual_cents=actual,
        rule=RuleRef(
            rule_id=f"rule-{branch.value}-{ref}",
            source_hash=H(f"rulehash-{branch.value}-{ref}"),
            effective_from="2026-01-01",
            effective_to=None,
            verified_controlling=verified,
            source_locator=f"source://rule/{branch.value}/{ref}",
        ),
        evidence=(EvidenceRef(
            evidence_id=f"ev-{branch.value}-{ref}",
            source_hash=H(f"evhash-{branch.value}-{ref}"),
            locator=f"source://evidence/{branch.value}/{ref}",
            kind="source_record",
            verified=verified,
        ),),
        reason="VARIANCE",
        confidence_basis="verified" if verified else "candidate",
    ))


def settlement(ledger, finding_id, recovered_cents):
    return SettlementEvidence(
        settlement_id="settlement-1",
        finding_id=finding_id,
        source_hash=hashlib.sha256(b"settlement-1").hexdigest(),
        source_locator="bank://remittance/settlement-1",
        observed_at=ledger.get(finding_id).updated_at,
        recovered_cents=recovered_cents,
        currency="USD",
        verified=True,
    )


class Scan360ReportTests(unittest.TestCase):
    def test_cross_branch_stage_totals_do_not_promote_review_dollars(self):
        ledger = DurableRecoveryLedger()

        freight = make_finding(Branch.FREIGHT, "c1", 10000, 15000, ref="freight")
        payer = make_finding(Branch.PAYER, "c1", 20000, 15000, ref="payer")
        utility_review = make_finding(
            Branch.UTILITY, "c1", 10000, 13000, verified=False, ref="utility"
        )
        other_client = make_finding(Branch.AP, "c2", 10000, 12000, ref="other")

        for finding in (freight, payer, utility_review, other_client):
            ledger.add(finding)

        ledger.approve(freight.finding_id, "reviewer", "verified freight")
        ledger.authorize(freight.finding_id, "auth-1")
        ledger.mark_claimed(freight.finding_id)
        ledger.mark_recovered(
            freight.finding_id,
            settlement(ledger, freight.finding_id, 4000),
            800,
        )

        ledger.approve(payer.finding_id, "reviewer", "verified payer")

        report = build_scan360_report(ledger, "c1")

        self.assertEqual(report.totals["cases"], 3)
        self.assertEqual(report.totals["potential_cents"], 13000)
        self.assertEqual(report.totals["review_cents"], 3000)
        self.assertEqual(report.totals["validated_cents"], 10000)
        self.assertEqual(report.totals["recovered_cents"], 4000)
        self.assertEqual(report.totals["fee_cents"], 800)
        self.assertEqual(report.branches["freight"]["recovered_cents"], 4000)
        self.assertEqual(report.branches["utility"]["validated_cents"], 0)
        self.assertEqual(len(report.review_backlog), 2)
        self.assertEqual(report.review_backlog[0]["potential_recovery_cents"], 5000)

    def test_mixed_currency_client_is_rejected(self):
        ledger = DurableRecoveryLedger()
        usd = make_finding(Branch.AP, "c1", 10000, 12000, ref="usd")
        ledger.add(usd)

        eur = RecoveryEngine().evaluate(RecoveryObservation(
            branch=Branch.AP,
            client_id="c1",
            counterparty_id="vendor-eu",
            reference="eur",
            currency="EUR",
            expected_cents=10000,
            actual_cents=12000,
            rule=RuleRef(
                rule_id="r-eur", source_hash=H("h"), effective_from="2026-01-01",
                effective_to=None, verified_controlling=True,
                source_locator="source://eur",
            ),
            evidence=(EvidenceRef(
                evidence_id="e-eur", source_hash=H("eh"), locator="source://eur",
                kind="payment", verified=True,
            ),),
            reason="VARIANCE", confidence_basis="verified",
        ))
        ledger.add(eur)

        with self.assertRaises(ValueError):
            build_scan360_report(ledger, "c1")


if __name__ == "__main__":
    unittest.main()
