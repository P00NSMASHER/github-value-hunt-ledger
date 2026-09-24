import hashlib
import unittest

from freight.finding_factory import FIXED, ChargeRule
from recoveryworks.branches.freight_audit import (
    CarrierInvoice,
    FreightAuditDomainAdapter,
    FreightAuditEvidenceBundle,
    LineItem,
    RateConfirmation,
    map_freight_audit_to_recovery,
)
from recoveryworks.branches.freight_authority import (
    FreightAuthorityContext,
    resolve_freight_authority,
)
from recoveryworks.branches.freight_audit_vendor import FindingType
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


def context(*, rules=None, envelope=None, **overrides) -> FreightAuthorityContext:
    values = dict(
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
    values.update(overrides)
    return FreightAuthorityContext(**values)


class FreightAuthorityTests(unittest.TestCase):
    def test_unique_verified_charge_rule_becomes_recoveryos_rule(self):
        out = resolve_freight_authority(
            context(),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )

        self.assertEqual(out.blockers, ())
        self.assertIsNotNone(out.rule)
        self.assertTrue(out.rule.verified_controlling)
        self.assertEqual(out.rule.metadata["charge_code"], "LINEHAUL")
        self.assertEqual(out.matched_rule_hashes, (rule().rule_hash,))
        self.assertTrue(any(item.kind == "freight_authority_document" for item in out.evidence))

    def test_ambiguous_charge_rules_fail_closed(self):
        out = resolve_freight_authority(
            context(rules=[
                rule(authority_document_id="rate-a"),
                rule(
                    authority_document_id="rate-b",
                    document_source_hash=H("rate-b"),
                ),
            ]),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )

        self.assertIsNone(out.rule)
        self.assertIn("AMBIGUOUS_APPLICABLE_CHARGE_RULE", out.blockers)

    def test_unverified_or_unhashed_authority_cannot_validate(self):
        unverified = resolve_freight_authority(
            context(rules=[rule(verified_controlling_authority=False)]),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIsNone(unverified.rule)
        self.assertIn("CHARGE_RULE_AUTHORITY_NOT_VERIFIED", unverified.blockers)

        unhashed = resolve_freight_authority(
            context(rules=[rule(document_source_hash="not-a-sha256")]),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIsNone(unhashed.rule)
        self.assertIn("AUTHORITY_DOCUMENT_HASH_INVALID", unhashed.blockers)

    def test_effective_date_and_scope_are_exact(self):
        expired = resolve_freight_authority(
            context(service_date="2026-10-01"),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIn("NO_APPLICABLE_CHARGE_RULE", expired.blockers)

        wrong_carrier = resolve_freight_authority(
            context(carrier_id="carrier-2"),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIn("NO_APPLICABLE_CHARGE_RULE", wrong_carrier.blockers)

    def test_ready_fmc_envelope_adds_provenance_without_becoming_rule(self):
        out = resolve_freight_authority(
            context(envelope=ready_envelope()),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )

        self.assertEqual(out.blockers, ())
        self.assertIsNotNone(out.rule)
        kinds = {item.kind for item in out.evidence}
        self.assertIn("freight_authority_envelope", kinds)
        self.assertIn("freight_contract_rate_page", kinds)
        self.assertIn("fmc_tariff_rule_source", kinds)
        self.assertEqual(
            out.rule.metadata["fmc_envelope_status"],
            "AUTHORITY_ENVELOPE_READY",
        )

    def test_not_ready_or_mismatched_fmc_envelope_blocks_money(self):
        blocked = ready_envelope(
            status="NOT_READY_FOR_MONEY_ASSERTION",
            blockers=["AMBIGUOUS_TARIFF_AUTHORITY"],
        )
        out = resolve_freight_authority(
            context(envelope=blocked),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIsNone(out.rule)
        self.assertIn("FMC_ENVELOPE_NOT_READY_FOR_MONEY_ASSERTION", out.blockers)
        self.assertIn("FMC_AMBIGUOUS_TARIFF_AUTHORITY", out.blockers)

        wrong_lane = ready_envelope()
        wrong_lane["lane"] = dict(wrong_lane["lane"], origin="Memphis")
        out = resolve_freight_authority(
            context(envelope=wrong_lane),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIsNone(out.rule)
        self.assertIn("FMC_ORIGIN_MISMATCH", out.blockers)

    def test_base_rate_ready_rule_gaps_only_allows_base_rate_category(self):
        envelope = ready_envelope(status="BASE_RATE_READY_RULE_GAPS")
        linehaul = resolve_freight_authority(
            context(envelope=envelope),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        self.assertIsNotNone(linehaul.rule)
        self.assertNotIn("FMC_TARIFF_RULE_GAPS", linehaul.blockers)

        fuel = resolve_freight_authority(
            context(
                envelope=envelope,
                rules=[rule(charge_code="FUEL")],
            ),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="fuel",
        )
        self.assertIsNone(fuel.rule)
        self.assertIn("FMC_TARIFF_RULE_GAPS", fuel.blockers)

    def test_mapper_uses_existing_authority_layer_end_to_end(self):
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
            authority_context=context(envelope=ready_envelope()),
        )

        findings = RecoveryEngine().scan(mapping.observations)
        self.assertEqual(len(findings), 1)
        self.assertIs(findings[0].state, FindingState.VALIDATED)
        self.assertEqual(findings[0].potential_recovery_cents, 20_000)
        self.assertTrue(
            any(
                item.kind == "freight_authority_envelope"
                for item in findings[0].evidence
            )
        )

    def test_mapper_keeps_fmc_conflict_in_review_metadata(self):
        domain = FreightAuditDomainAdapter().audit(
            RateConfirmation(
                "L-2",
                "broker",
                "carrier",
                "Chicago",
                "Dallas",
                100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            CarrierInvoice(
                "INV-2",
                "L-2",
                "carrier",
                120_000,
                line_items=[LineItem("Linehaul", 120_000)],
            ),
            None,
        )
        blocked = ready_envelope(
            status="NOT_READY_FOR_MONEY_ASSERTION",
            blockers=["AMBIGUOUS_TARIFF_AUTHORITY"],
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
            authority_context=context(envelope=blocked),
        )

        findings = RecoveryEngine().scan(mapping.observations)
        self.assertEqual(len(findings), 1)
        self.assertIs(findings[0].state, FindingState.REVIEW)
        self.assertIsNone(findings[0].rule)
        self.assertIn(
            "FMC_AMBIGUOUS_TARIFF_AUTHORITY",
            findings[0].metadata["authority_blockers"],
        )

    def test_mapper_rejects_two_authority_paths_at_once(self):
        domain = FreightAuditDomainAdapter().audit(
            RateConfirmation("L-3", "broker", "carrier", "A", "B", 100),
            CarrierInvoice("INV-3", "L-3", "carrier", 200),
            None,
        )
        resolved = resolve_freight_authority(
            context(),
            finding_type=FindingType.LINE_OVERCHARGE,
            normalized_category="linehaul",
        )
        with self.assertRaises(ValueError):
            map_freight_audit_to_recovery(
                domain,
                client_id="buyer-1",
                counterparty_id="carrier-1",
                currency="USD",
                evidence=FreightAuditEvidenceBundle(
                    invoice=source("invoice-3"),
                    rate_confirmation=source("rate-3"),
                ),
                controlling_rule=resolved.rule,
                authority_context=context(),
            )


if __name__ == "__main__":
    unittest.main()
