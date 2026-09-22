from types import SimpleNamespace
import unittest

from recoveryworks import (
    Branch,
    CaseState,
    EvidenceRef,
    FindingState,
    RecoveryEngine,
    RecoveryLedger,
    RecoveryObservation,
    RuleRef,
    SourceManifestEntry,
    freeze_scan,
    run_scan,
)
from recoveryworks.branches.freight import from_freight_finding
from recoveryworks.branches.registry import BRANCHES


def evidence(verified=True):
    return EvidenceRef(
        evidence_id="ev:1",
        source_hash="abc123",
        locator="source://doc#p1",
        kind="invoice",
        verified=verified,
    )


def rule(verified=True):
    return RuleRef(
        rule_id="rule:1",
        source_hash="rulehash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=verified,
        source_locator="source://contract#7.4",
    )


class RecoveryWorksTests(unittest.TestCase):
    def test_all_six_branches_registered(self):
        self.assertEqual(set(BRANCHES), set(Branch))

    def test_overpayment_and_underpayment_modes(self):
        engine = RecoveryEngine()
        freight = engine.evaluate(RecoveryObservation(
            branch=Branch.FREIGHT, client_id="c", counterparty_id="carrier",
            reference="i1", currency="USD", expected_cents=10000,
            actual_cents=12500, rule=rule(), evidence=(evidence(),),
            reason="OVERCHARGE", confidence_basis="verified contract",
        ))
        payer = engine.evaluate(RecoveryObservation(
            branch=Branch.PAYER, client_id="c", counterparty_id="payer",
            reference="clm1", currency="USD", expected_cents=20000,
            actual_cents=15000, rule=rule(), evidence=(evidence(),),
            reason="UNDERPAYMENT", confidence_basis="verified schedule",
        ))
        self.assertEqual(freight.potential_recovery_cents, 2500)
        self.assertEqual(payer.potential_recovery_cents, 5000)
        self.assertIs(freight.state, FindingState.VALIDATED)
        self.assertIs(payer.state, FindingState.VALIDATED)

    def test_unverified_authority_stays_review(self):
        finding = RecoveryEngine().evaluate(RecoveryObservation(
            branch=Branch.UTILITY, client_id="c", counterparty_id="utility",
            reference="bill1", currency="USD", expected_cents=10000,
            actual_cents=13000, rule=rule(False), evidence=(evidence(),),
            reason="TARIFF_VARIANCE", confidence_basis="candidate tariff",
        ))
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_no_variance_produces_no_finding(self):
        finding = RecoveryEngine().evaluate(RecoveryObservation(
            branch=Branch.AP, client_id="c", counterparty_id="vendor",
            reference="inv1", currency="USD", expected_cents=10000,
            actual_cents=10000, rule=rule(), evidence=(evidence(),),
            reason="NO_VARIANCE", confidence_basis="ledger",
        ))
        self.assertIsNone(finding)

    def test_ledger_requires_review_and_authorization_before_claim(self):
        finding = RecoveryEngine().evaluate(RecoveryObservation(
            branch=Branch.DUTY, client_id="c", counterparty_id="customs",
            reference="entry1", currency="USD", expected_cents=10000,
            actual_cents=14000, rule=rule(), evidence=(evidence(),),
            reason="DUTY_VARIANCE", confidence_basis="verified tariff",
        ))
        ledger = RecoveryLedger()
        rec = ledger.add(finding)
        self.assertIs(rec.case_state, CaseState.VALIDATED)
        with self.assertRaises(ValueError):
            ledger.mark_claimed(finding.finding_id)
        ledger.approve(finding.finding_id, "reviewer-1", "Checked source and calculation")
        ledger.authorize(finding.finding_id, "customer-auth-1")
        claimed = ledger.mark_claimed(finding.finding_id)
        self.assertIs(claimed.case_state, CaseState.CLAIMED)
        recovered = ledger.mark_recovered(finding.finding_id, 3000, 600)
        self.assertIs(recovered.case_state, CaseState.RECOVERED)
        self.assertEqual(ledger.rollup()["totals"]["fee_cents"], 600)

    def test_ledger_dedupes_identical_proof(self):
        finding = RecoveryEngine().evaluate(RecoveryObservation(
            branch=Branch.CONSTRUCTION, client_id="c", counterparty_id="owner",
            reference="co-7", currency="USD", expected_cents=500000,
            actual_cents=200000, rule=rule(), evidence=(evidence(),),
            reason="UNPAID_ENTITLEMENT", confidence_basis="contract + schedule",
        ))
        ledger = RecoveryLedger()
        a = ledger.add(finding)
        b = ledger.add(finding)
        self.assertEqual(a.finding.finding_id, b.finding.finding_id)
        self.assertEqual(ledger.rollup()["totals"]["cases"], 1)

    def test_freight_bridge_preserves_authority_gate(self):
        f = SimpleNamespace(
            finding_id="f1", proof_hash="proof", buyer_id="buyer",
            carrier_id="carrier", invoice_id="inv", currency="USD",
            expected_cents=1000, actual_cents=1500, status="VALIDATED",
            shipment_id="ship", customer_id="customer",
        )
        authority = SimpleNamespace(authority_id="a1", source_hash="authorityhash")
        obs = from_freight_finding(f, authority)
        finding = RecoveryEngine().evaluate(obs)
        self.assertIs(finding.state, FindingState.REVIEW)
        dated = RecoveryEngine().evaluate(from_freight_finding(
            f, authority, effective_from="2026-01-01", occurred_on="2026-06-01"
        ))
        self.assertIs(dated.state, FindingState.VALIDATED)
        downgraded = RecoveryEngine().evaluate(from_freight_finding(f, None))
        self.assertIs(downgraded.state, FindingState.REVIEW)

    def test_recovery_scan_360_freezes_scope_and_batch(self):
        manifest = freeze_scan(
            scan_id="scan-1",
            client_id="c",
            branches=(Branch.FREIGHT, Branch.AP),
            selection_rule="all records in supplied historical period",
            sources=(
                SourceManifestEntry("s1", Branch.FREIGHT, "h1", "file://freight.csv", "invoice_export"),
                SourceManifestEntry("s2", Branch.AP, "h2", "file://payments.csv", "payment_export"),
                SourceManifestEntry("s3", Branch.AP, "rulehash", "source://contract#7.4", "controlling_rule"),
                SourceManifestEntry("s4", Branch.AP, "abc123", "source://doc#p1", "evidence"),
            ),
        )
        observation = RecoveryObservation(
            branch=Branch.AP, client_id="c", counterparty_id="vendor",
            reference="inv-1", currency="USD", expected_cents=10000,
            actual_cents=12000, rule=rule(), evidence=(evidence(),),
            reason="DUPLICATE_PAYMENT", confidence_basis="verified ledger",
        )
        first = run_scan(manifest, (observation,))
        second = run_scan(manifest, (observation,))
        self.assertEqual(first.batch_hash, second.batch_hash)
        self.assertEqual(len(first.findings), 1)
        with self.assertRaises(ValueError):
            run_scan(manifest, (RecoveryObservation(
                branch=Branch.UTILITY, client_id="c", counterparty_id="u",
                reference="b", currency="USD", expected_cents=1, actual_cents=2,
                rule=rule(), evidence=(evidence(),), reason="x", confidence_basis="x",
            ),))


if __name__ == "__main__":
    unittest.main()
