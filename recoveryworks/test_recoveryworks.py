from types import SimpleNamespace
import hashlib
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
    SettlementEvidence,
    SourceManifestEntry,
    freeze_scan,
    run_scan,
)
from recoveryworks.branches.freight import from_freight_finding
from recoveryworks.branches.registry import BRANCHES
from recoveryworks.test_support import source_hash as H


def evidence(verified=True):
    return EvidenceRef(
        evidence_id="ev:1",
        source_hash=hashlib.sha256(b"evidence-1").hexdigest(),
        locator="source://doc#p1",
        kind="invoice",
        verified=verified,
    )


def rule(verified=True):
    return RuleRef(
        rule_id="rule:1",
        source_hash=hashlib.sha256(b"rule-1").hexdigest(),
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=verified,
        source_locator="source://contract#7.4",
    )


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


class RecoveryWorksTests(unittest.TestCase):
    def test_all_six_branches_registered(self):
        self.assertEqual(set(BRANCHES), set(Branch))

    def test_proof_references_require_real_sha256_source_digests(self):
        with self.assertRaisesRegex(ValueError, "64-character SHA-256"):
            EvidenceRef(
                evidence_id="ev:bad-hash",
                source_hash="not-a-digest",
                locator="source://bad-hash",
                kind="invoice",
                verified=False,
            )
        with self.assertRaisesRegex(ValueError, "64-character SHA-256"):
            RuleRef(
                rule_id="rule:bad-hash",
                source_hash="not-a-digest",
                effective_from="2026-01-01",
                effective_to=None,
                verified_controlling=False,
                source_locator="source://bad-hash",
            )
        with self.assertRaisesRegex(ValueError, "64-character SHA-256"):
            SourceManifestEntry(
                "source:bad-hash",
                Branch.FREIGHT,
                "not-a-digest",
                "source://bad-hash",
                "invoice_export",
            )

    def test_nested_proof_metadata_is_detached_and_immutable(self):
        raw_metadata = {"trace": [{"amount_cents": 100}]}
        reference = EvidenceRef(
            evidence_id="ev:immutable",
            source_hash=hashlib.sha256(b"immutable-source").hexdigest(),
            locator="source://doc#1",
            kind="invoice",
            verified=True,
            metadata=raw_metadata,
        )
        proof_hash = reference.proof_hash

        raw_metadata["trace"][0]["amount_cents"] = 999
        self.assertEqual(reference.metadata["trace"][0]["amount_cents"], 100)
        self.assertEqual(reference.proof_hash, proof_hash)
        with self.assertRaises(TypeError):
            reference.metadata["trace"].append({"amount_cents": 1})

    def test_non_finite_proof_metadata_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "NaN or infinity"):
            EvidenceRef(
                evidence_id="ev:nan",
                source_hash=hashlib.sha256(b"nan-source").hexdigest(),
                locator="source://doc#1",
                kind="invoice",
                verified=True,
                metadata={"score": float("nan")},
            )

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
        recovered = ledger.mark_recovered(
            finding.finding_id,
            settlement(ledger, finding.finding_id, 3000),
            600,
        )
        self.assertIs(recovered.case_state, CaseState.RECOVERED)
        self.assertEqual(ledger.rollup()["totals"]["fee_cents"], 600)

    def test_ledger_actor_fields_are_typed_and_reject_control_characters(self):
        finding = RecoveryEngine().evaluate(RecoveryObservation(
            branch=Branch.DUTY, client_id="c", counterparty_id="customs",
            reference="entry-typed", currency="USD", expected_cents=10000,
            actual_cents=14000, rule=rule(), evidence=(evidence(),),
            reason="DUTY_VARIANCE", confidence_basis="verified tariff",
        ))
        ledger = RecoveryLedger()
        ledger.add(finding)
        with self.assertRaisesRegex(ValueError, "reviewer_id is required"):
            ledger.approve(finding.finding_id, None, "reviewed")
        with self.assertRaisesRegex(ValueError, "control characters"):
            ledger.approve(finding.finding_id, "reviewer\nadmin", "reviewed")

    def test_settlement_evidence_cannot_be_reused_across_findings(self):
        engine = RecoveryEngine()
        findings = tuple(
            engine.evaluate(RecoveryObservation(
                branch=Branch.FREIGHT,
                client_id="client-1",
                counterparty_id="carrier-1",
                reference=reference,
                currency="USD",
                expected_cents=10_000,
                actual_cents=14_000,
                rule=rule(),
                evidence=(evidence(),),
                reason="OVERCHARGE",
                confidence_basis="verified contract",
            ))
            for reference in ("invoice-1", "invoice-2")
        )
        ledger = RecoveryLedger()
        for index, finding in enumerate(findings, start=1):
            ledger.add(finding)
            ledger.approve(finding.finding_id, f"reviewer-{index}", "verified")
            ledger.authorize(finding.finding_id, f"customer-auth-{index}")
            ledger.mark_claimed(finding.finding_id)

        first_evidence = settlement(ledger, findings[0].finding_id, 4_000)
        with self.assertRaisesRegex(ValueError, "finding_id does not match"):
            ledger.mark_recovered(findings[1].finding_id, first_evidence)

        ledger.mark_recovered(findings[0].finding_id, first_evidence)
        relabeled_evidence = SettlementEvidence(
            settlement_id=first_evidence.settlement_id,
            finding_id=findings[1].finding_id,
            source_hash=first_evidence.source_hash,
            source_locator=first_evidence.source_locator,
            observed_at=ledger.get(findings[1].finding_id).updated_at,
            recovered_cents=first_evidence.recovered_cents,
            currency=first_evidence.currency,
            verified=True,
        )
        with self.assertRaisesRegex(ValueError, "already allocated"):
            ledger.mark_recovered(findings[1].finding_id, relabeled_evidence)
        self.assertIs(ledger.get(findings[1].finding_id).case_state, CaseState.CLAIMED)

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
            finding_id="f1", proof_hash=H("proof"), buyer_id="buyer",
            carrier_id="carrier", invoice_id="inv", currency="USD",
            expected_cents=1000, actual_cents=1500, status="VALIDATED",
            shipment_id="ship", customer_id="customer",
        )
        authority = SimpleNamespace(authority_id="a1", source_hash=H("authorityhash"))
        obs = from_freight_finding(f, authority)
        finding = RecoveryEngine().evaluate(obs)
        self.assertIs(finding.state, FindingState.VALIDATED)
        downgraded = RecoveryEngine().evaluate(from_freight_finding(f, None))
        self.assertIs(downgraded.state, FindingState.REVIEW)

    def test_recovery_scan_360_freezes_scope_and_batch(self):
        manifest = freeze_scan(
            scan_id="scan-1",
            client_id="c",
            branches=(Branch.FREIGHT, Branch.AP),
            selection_rule="all records in supplied historical period",
            sources=(
                SourceManifestEntry("s1", Branch.FREIGHT, H("h1"), "file://freight.csv", "invoice_export"),
                SourceManifestEntry("s2", Branch.AP, H("h2"), "file://payments.csv", "payment_export"),
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
