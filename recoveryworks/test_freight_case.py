import hashlib
from dataclasses import replace
from datetime import datetime
import unittest

from freight.finding_factory import FIXED, ChargeRule
from recoveryworks.branches.freight_audit import (
    CarrierInvoice,
    FreightAuditDisposition,
    FreightAuditDomainAdapter,
    FreightAuditEvidenceBundle,
    LineItem,
    ProofOfDelivery,
    RateConfirmation,
    map_freight_audit_to_recovery,
)
from recoveryworks.branches.freight_authority import FreightAuthorityContext
from recoveryworks.branches.freight_case import (
    RESOLVE_AUTHORITY,
    REVIEW_VALIDATED_CANDIDATE,
    build_freight_review_packet,
    freight_review_packet_as_dict,
    render_freight_review_packet_markdown,
)
from recoveryworks.engine import RecoveryEngine
from recoveryworks.models import EvidenceRef, FindingState


def H(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source(name: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=name,
        source_hash=H(name),
        locator=f"memory://{name}",
        kind=name,
        verified=True,
    )


def rule(**overrides) -> ChargeRule:
    values = dict(
        buyer_id="buyer-1",
        business_unit="BU-1",
        customer_id="customer-1",
        carrier_id="carrier-1",
        currency="USD",
        authority_document_id="rate-confirmation-1",
        charge_code="LINEHAUL",
        pricing_model=FIXED,
        effective_from="2026-09-01",
        effective_to="2026-09-30",
        document_source_hash=H("rate-confirmation-source"),
        verified_controlling_authority=True,
        fixed_cents=100_000,
        unit_rate_cents=None,
    )
    values.update(overrides)
    return ChargeRule(**values)


def ready_envelope(**overrides) -> dict:
    envelope = {
        "status": "AUTHORITY_ENVELOPE_READY",
        "asserted_recovery": "0.00",
        "fmc_organization_no": "123456",
        "shipment_date": "2026-09-10",
        "lane": {
            "origin": "Chicago",
            "destination": "Dallas",
            "container_type": "40HQ",
            "currency": "USD",
        },
        "base_rate_authority": {
            "status": "RESOLVED",
            "amount_value": "1000",
            "currency": "USD",
            "rate_basis": "per container",
            "contract_candidates": [{
                "source_label": "AUTHORIZED_CONTRACT_CORPUS",
                "source_contract_reference": "C-001",
                "authority_readiness": "AUTHORITY_READY",
                "page_sha256": H("contract-page"),
                "page_url": "memory://contract-page",
            }],
        },
        "tariff_rule_authority": {
            "status": "RESOLVED",
            "rules": {
                "fuel": {
                    "status": "RESOLVED",
                    "candidates": [{
                        "source_sha256": H("fmc-fuel"),
                        "evidence_url": "memory://fmc-fuel",
                        "source_version": "REV-1",
                        "effective_from": "2026-09-01",
                        "effective_to": None,
                        "confidence": 0.95,
                    }],
                },
            },
        },
        "blockers": [],
    }
    envelope.update(overrides)
    return envelope


def context(*, rules=None, envelope=None) -> FreightAuthorityContext:
    return FreightAuthorityContext(
        buyer_id="buyer-1",
        business_unit="BU-1",
        customer_id="customer-1",
        carrier_id="carrier-1",
        currency="USD",
        service_date="2026-09-10",
        charge_rules=tuple(rules if rules is not None else [rule()]),
        fmc_envelope=envelope,
        fmc_organization_no="123456" if envelope is not None else None,
        origin="Chicago" if envelope is not None else None,
        destination="Dallas" if envelope is not None else None,
        container_type="40HQ" if envelope is not None else None,
    )


def linehaul_mapping(*, envelope=None):
    domain = FreightAuditDomainAdapter().audit(
        RateConfirmation(
            "L-1",
            "broker",
            "carrier",
            "Chicago",
            "Dallas",
            100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        ),
        CarrierInvoice(
            "INV-1",
            "L-1",
            "carrier",
            120_000,
            line_items=[LineItem("Linehaul", 120_000)],
        ),
        None,
    )
    mapping = map_freight_audit_to_recovery(
        domain,
        client_id="buyer-1",
        counterparty_id="carrier-1",
        currency="USD",
        evidence=FreightAuditEvidenceBundle(
            invoice=source("invoice"),
            rate_confirmation=source("rate"),
        ),
        authority_context=context(envelope=envelope),
    )
    findings = RecoveryEngine().scan(mapping.observations)
    return mapping, findings


class FreightCaseAssemblerTests(unittest.TestCase):
    def test_validated_case_contains_exact_calculation_authority_and_sources(self):
        mapping, findings = linehaul_mapping(envelope=ready_envelope())
        packet = build_freight_review_packet(mapping, findings)

        self.assertEqual(packet.case_count, 1)
        self.assertEqual(packet.candidate_recovery_cents, 20_000)
        self.assertEqual(packet.validated_candidate_cents, 20_000)
        self.assertEqual(packet.review_candidate_cents, 0)

        case = packet.cases[0]
        self.assertEqual(case.state, FindingState.VALIDATED.value)
        self.assertEqual(case.action_hint, REVIEW_VALIDATED_CANDIDATE)
        self.assertEqual(case.calculation.component_billed_cents, 120_000)
        self.assertEqual(case.calculation.component_expected_cents, 100_000)
        self.assertEqual(case.calculation.candidate_recovery_cents, 20_000)
        self.assertEqual(case.calculation.source_invoice_total_cents, 120_000)
        self.assertEqual(case.calculation.source_authority_total_cents, 100_000)
        self.assertEqual(
            case.calculation.expression,
            "120000 - 100000 = 20000 cents",
        )
        self.assertIsNotNone(case.authority)
        self.assertEqual(case.authority.charge_code, "LINEHAUL")
        self.assertEqual(case.authority.pricing_model, "FIXED")
        self.assertEqual(case.authority.fmc_envelope_status, "AUTHORITY_ENVELOPE_READY")
        roles = {item.role for item in case.evidence}
        self.assertIn("SOURCE_DOCUMENT", roles)
        self.assertIn("DETECTOR_OUTPUT", roles)
        self.assertIn("AUTHORITY", roles)
        self.assertFalse(case.external_action_allowed)
        self.assertFalse(case.realized_recovery_asserted)
        self.assertEqual(len(case.case_hash), 64)
        self.assertEqual(len(packet.packet_hash), 64)

    def test_fmc_conflict_renders_review_case_not_validated_claim(self):
        blocked = ready_envelope(
            status="NOT_READY_FOR_MONEY_ASSERTION",
            blockers=["AMBIGUOUS_TARIFF_AUTHORITY"],
        )
        mapping, findings = linehaul_mapping(envelope=blocked)
        packet = build_freight_review_packet(mapping, findings)

        self.assertEqual(packet.validated_candidate_cents, 0)
        self.assertEqual(packet.review_candidate_cents, 20_000)
        case = packet.cases[0]
        self.assertEqual(case.state, FindingState.REVIEW.value)
        self.assertEqual(case.action_hint, RESOLVE_AUTHORITY)
        self.assertIsNone(case.authority)
        self.assertIn(
            "FMC_AMBIGUOUS_TARIFF_AUTHORITY",
            case.authority_blockers,
        )
        self.assertIsNone(case.calculation.component_expected_cents)
        self.assertFalse(case.external_action_allowed)

    def test_overlap_findings_remain_supplemental_and_do_not_inflate_total(self):
        domain = FreightAuditDomainAdapter().audit(
            RateConfirmation(
                "L-2",
                "broker",
                "carrier",
                "Chicago",
                "Dallas",
                210_000,
                line_items=[
                    LineItem("Linehaul", 180_000),
                    LineItem("Fuel", 30_000),
                ],
            ),
            CarrierInvoice(
                "INV-2",
                "L-2",
                "carrier",
                240_000,
                line_items=[
                    LineItem("Linehaul", 180_000),
                    LineItem("Fuel", 30_000),
                    LineItem("Fuel Surcharge", 30_000),
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
                invoice=source("invoice-2"),
                rate_confirmation=source("rate-2"),
            ),
        )
        findings = RecoveryEngine().scan(mapping.observations)
        packet = build_freight_review_packet(mapping, findings)

        self.assertEqual(packet.candidate_recovery_cents, 30_000)
        self.assertEqual(packet.case_count, 1)
        dispositions = {item.disposition for item in packet.supplemental_findings}
        self.assertIn(FreightAuditDisposition.SUPPRESSED_OVERLAP.value, dispositions)
        self.assertTrue(
            any(
                item.finding_type == "total_mismatch"
                and item.disposition == FreightAuditDisposition.SUPPRESSED_OVERLAP.value
                for item in packet.supplemental_findings
            )
        )

    def test_underbilled_carrier_revenue_stays_supplemental_only(self):
        domain = FreightAuditDomainAdapter().audit(
            RateConfirmation(
                "L-3",
                "broker",
                "carrier",
                "A",
                "B",
                100_000,
                line_items=[LineItem("Linehaul", 100_000)],
                approved_accessorials={"detention": 8_000},
                free_time_hours=2.0,
            ),
            CarrierInvoice(
                "INV-3",
                "L-3",
                "carrier",
                100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            ProofOfDelivery(
                "L-3",
                True,
                arrival_time=datetime(2026, 9, 10, 8, 0),
                departure_time=datetime(2026, 9, 10, 12, 15),
            ),
        )
        mapping = map_freight_audit_to_recovery(
            domain,
            client_id="buyer-1",
            counterparty_id="carrier-1",
            currency="USD",
            evidence=FreightAuditEvidenceBundle(
                invoice=source("invoice-3"),
                rate_confirmation=source("rate-3"),
                pod=source("pod-3"),
            ),
        )
        packet = build_freight_review_packet(
            mapping,
            RecoveryEngine().scan(mapping.observations),
        )

        self.assertEqual(packet.case_count, 0)
        self.assertEqual(packet.candidate_recovery_cents, 0)
        self.assertTrue(
            any(
                item.disposition == FreightAuditDisposition.OUT_OF_SCOPE_DIRECTION.value
                for item in packet.supplemental_findings
            )
        )

    def test_packet_requires_complete_recoveryfinding_set(self):
        domain = FreightAuditDomainAdapter().audit(
            RateConfirmation(
                "L-4",
                "broker",
                "carrier",
                "Chicago",
                "Dallas",
                100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            CarrierInvoice(
                "INV-4",
                "L-4",
                "carrier",
                130_000,
                line_items=[
                    LineItem("Linehaul", 120_000),
                    LineItem("Liftgate", 10_000),
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
                invoice=source("invoice-4"),
                rate_confirmation=source("rate-4"),
            ),
            authority_context=context(),
        )
        findings = RecoveryEngine().scan(mapping.observations)
        self.assertEqual(len(findings), 2)
        with self.assertRaises(ValueError):
            build_freight_review_packet(mapping, findings[:1])

    def test_tampered_finding_binding_is_rejected(self):
        mapping, findings = linehaul_mapping(envelope=ready_envelope())
        tampered = replace(findings[0], reference="not-this-mapping")
        with self.assertRaises(ValueError):
            build_freight_review_packet(mapping, (tampered,))

    def test_packet_is_deterministic_and_serializable(self):
        mapping, findings = linehaul_mapping(envelope=ready_envelope())
        first = build_freight_review_packet(mapping, findings)
        second = build_freight_review_packet(mapping, findings)
        self.assertEqual(first, second)
        body = freight_review_packet_as_dict(first)
        self.assertEqual(body["packet_hash"], first.packet_hash)
        self.assertEqual(body["cases"][0]["case_hash"], first.cases[0].case_hash)

    def test_markdown_is_reviewer_ready_and_disclaims_external_action(self):
        mapping, findings = linehaul_mapping(envelope=ready_envelope())
        text = render_freight_review_packet_markdown(
            build_freight_review_packet(mapping, findings)
        )
        self.assertIn("Freight Evidence Packet", text)
        self.assertIn("Candidate recovery", text)
        self.assertIn("Component billed", text)
        self.assertIn("Component expected", text)
        self.assertIn("Governing authority", text)
        self.assertIn("Evidence", text)
        self.assertIn("not realized recoveries", text)
        self.assertIn("not authorization to contact a counterparty", text)
        self.assertNotIn("realized savings", text.lower())


if __name__ == "__main__":
    unittest.main()
