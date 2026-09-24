import hashlib
from datetime import datetime
import unittest

from recoveryworks.branches.freight_audit import (
    CarrierInvoice,
    FindingType,
    FreightAuditDisposition,
    FreightAuditDomainAdapter,
    FreightAuditEvidenceBundle,
    LineItem,
    ProofOfDelivery,
    RateConfirmation,
    map_freight_audit_to_recovery,
)
from recoveryworks.engine import RecoveryEngine
from recoveryworks.models import EvidenceRef, FindingState, RuleRef


def H(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def evidence_ref(name: str, *, verified: bool = True) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=name,
        source_hash=H(name),
        locator=f"memory://{name}",
        kind=name,
        verified=verified,
    )


def controlling_rule() -> RuleRef:
    return RuleRef(
        rule_id="RATE-CON-1",
        source_hash=H("rate-authority"),
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="memory://rate-authority",
    )


class FreightAuditRecoveryMappingTests(unittest.TestCase):
    def test_total_line_and_duplicate_overlap_counts_only_once(self):
        rate = RateConfirmation(
            "L1",
            "broker",
            "carrier",
            "A",
            "B",
            210_000,
            line_items=[
                LineItem("Linehaul", 180_000),
                LineItem("Fuel", 30_000),
            ],
        )
        invoice = CarrierInvoice(
            "INV1",
            "L1",
            "carrier",
            240_000,
            line_items=[
                LineItem("Linehaul", 180_000),
                LineItem("Fuel", 30_000),
                LineItem("Fuel Surcharge", 30_000),
            ],
        )
        domain = FreightAuditDomainAdapter().audit(rate, invoice, None)
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice"),
                rate_confirmation=evidence_ref("rate"),
            ),
        )

        self.assertEqual(mapping.candidate_recovery_cents, 30_000)
        self.assertEqual(sum(o.actual_cents - o.expected_cents for o in mapping.observations), 30_000)
        dispositions = {item.finding_type: item.disposition for item in mapping.mapped_findings}
        self.assertIs(dispositions[FindingType.DUPLICATE_LINE], FreightAuditDisposition.OBSERVATION)
        self.assertIs(dispositions[FindingType.LINE_OVERCHARGE], FreightAuditDisposition.SUPPRESSED_OVERLAP)
        self.assertIs(dispositions[FindingType.TOTAL_MISMATCH], FreightAuditDisposition.SUPPRESSED_OVERLAP)

    def test_multiple_unauthorized_lines_same_category_still_add(self):
        rate = RateConfirmation(
            "L2", "broker", "carrier", "A", "B", 100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        invoice = CarrierInvoice(
            "INV2", "L2", "carrier", 130_000,
            line_items=[
                LineItem("Linehaul", 100_000),
                LineItem("Liftgate", 10_000),
                LineItem("Lift Gate Service", 20_000),
            ],
        )
        domain = FreightAuditDomainAdapter().audit(rate, invoice, None)
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice-2"),
                rate_confirmation=evidence_ref("rate-2"),
            ),
        )

        unauthorized = [
            item for item in mapping.mapped_findings
            if item.finding_type is FindingType.UNAUTHORIZED_ACCESSORIAL
        ]
        self.assertEqual(len(unauthorized), 2)
        self.assertTrue(all(item.disposition is FreightAuditDisposition.OBSERVATION for item in unauthorized))
        self.assertEqual(sum(item.allocated_candidate_cents for item in unauthorized), 30_000)
        self.assertEqual(mapping.candidate_recovery_cents, 30_000)

    def test_unexplained_total_mismatch_is_allocated_only_as_residual(self):
        domain = FreightAuditDomainAdapter().audit(
            RateConfirmation(
                "L3", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            CarrierInvoice(
                "INV3", "L3", "carrier", 150_000,
                line_items=[
                    LineItem("Linehaul", 130_000),
                    LineItem("Other", 20_000),
                ],
            ),
            None,
        )
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice-3"),
                rate_confirmation=evidence_ref("rate-3"),
            ),
        )

        line = next(item for item in mapping.mapped_findings if item.finding_type is FindingType.LINE_OVERCHARGE)
        total = next(item for item in mapping.mapped_findings if item.finding_type is FindingType.TOTAL_MISMATCH)
        self.assertEqual(line.allocated_candidate_cents, 30_000)
        self.assertEqual(total.allocated_candidate_cents, 20_000)
        self.assertEqual(mapping.candidate_recovery_cents, 50_000)

    def test_every_upstream_finding_gets_deterministic_evidence(self):
        rate = RateConfirmation("L4", "broker", "carrier", "A", "B", 10_000)
        invoice = CarrierInvoice("INV4", "WRONG", "carrier", 12_000)
        domain = FreightAuditDomainAdapter().audit(rate, invoice, None)
        bundle = FreightAuditEvidenceBundle(
            invoice=evidence_ref("invoice-4"),
            rate_confirmation=evidence_ref("rate-4"),
        )
        first = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=bundle,
        )
        second = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=bundle,
        )

        self.assertEqual(len(first.mapped_findings), len(domain.findings))
        self.assertEqual(
            [item.candidate_evidence.proof_hash for item in first.mapped_findings],
            [item.candidate_evidence.proof_hash for item in second.mapped_findings],
        )

    def test_verified_sources_and_authority_can_produce_validated_finding(self):
        rate = RateConfirmation(
            "L5", "broker", "carrier", "A", "B", 100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        invoice = CarrierInvoice(
            "INV5", "L5", "carrier", 120_000,
            line_items=[LineItem("Linehaul", 120_000)],
        )
        domain = FreightAuditDomainAdapter().audit(rate, invoice, None)
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice-5"),
                rate_confirmation=evidence_ref("rate-5"),
            ),
            controlling_rule=controlling_rule(),
        )

        findings = RecoveryEngine().scan(mapping.observations)
        self.assertEqual(len(findings), 1)
        self.assertIs(findings[0].state, FindingState.VALIDATED)
        self.assertEqual(findings[0].potential_recovery_cents, 20_000)

    def test_missing_required_rate_source_forces_review_even_with_authority(self):
        rate = RateConfirmation(
            "L6", "broker", "carrier", "A", "B", 100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        invoice = CarrierInvoice(
            "INV6", "L6", "carrier", 120_000,
            line_items=[LineItem("Linehaul", 120_000)],
        )
        domain = FreightAuditDomainAdapter().audit(rate, invoice, None)
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice-6"),
                rate_confirmation=None,
            ),
            controlling_rule=controlling_rule(),
        )

        findings = RecoveryEngine().scan(mapping.observations)
        self.assertEqual(len(findings), 1)
        self.assertIs(findings[0].state, FindingState.REVIEW)
        self.assertIsNone(findings[0].rule)

    def test_integrity_blocker_prevents_validated_dollars(self):
        rate = RateConfirmation(
            "L7", "broker", "carrier", "A", "B", 100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        invoice = CarrierInvoice(
            "WRONG", "WRONG", "carrier", 120_000,
            line_items=[LineItem("Linehaul", 120_000)],
        )
        domain = FreightAuditDomainAdapter().audit(rate, invoice, None)
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice-7"),
                rate_confirmation=evidence_ref("rate-7"),
            ),
            controlling_rule=controlling_rule(),
        )

        self.assertIn("load_id_mismatch", mapping.integrity_blockers)
        findings = RecoveryEngine().scan(mapping.observations)
        self.assertTrue(findings)
        self.assertTrue(all(item.state is FindingState.REVIEW for item in findings))
        self.assertTrue(all(item.rule is None for item in findings))

    def test_underbilled_detention_is_evidence_only_for_overpayment_branch(self):
        rate = RateConfirmation(
            "L8", "broker", "carrier", "A", "B", 100_000,
            line_items=[LineItem("Linehaul", 100_000)],
            approved_accessorials={"detention": 8_000},
            free_time_hours=2.0,
        )
        invoice = CarrierInvoice(
            "INV8", "L8", "carrier", 100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        pod = ProofOfDelivery(
            "L8",
            True,
            arrival_time=datetime(2026, 6, 1, 8, 0),
            departure_time=datetime(2026, 6, 1, 12, 15),
        )
        domain = FreightAuditDomainAdapter().audit(rate, invoice, pod)
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=evidence_ref("invoice-8"),
                rate_confirmation=evidence_ref("rate-8"),
                pod=evidence_ref("pod-8"),
            ),
            controlling_rule=controlling_rule(),
        )

        detention = next(
            item for item in mapping.mapped_findings
            if item.finding_type is FindingType.DETENTION_UNDERBILLED
        )
        self.assertIs(detention.disposition, FreightAuditDisposition.OUT_OF_SCOPE_DIRECTION)
        self.assertIsNone(detention.observation)
        self.assertEqual(mapping.candidate_recovery_cents, 0)


if __name__ == "__main__":
    unittest.main()
