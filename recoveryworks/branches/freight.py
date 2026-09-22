"""Bridges FreightRecovery proof objects into the RecoveryWorks ledger.

The preferred bridge consumes the real freight.finding_factory derivation,
invoice charge, and effective-dated ChargeRule. The legacy finding-only bridge
is retained for compatibility but fails closed to REVIEW unless the caller
supplies an explicit authority window and transaction date.
"""
from __future__ import annotations

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef
from .common import observation


def from_freight_derivation(
    derivation,
    charge,
    rule,
    *,
    source_locator: str | None = None,
) -> RecoveryObservation:
    """Normalize a freight ChargeDerivation without losing rule-version provenance.

    A derivation with no discrepancy finding has nothing to enter into the
    recovery ledger. Validation is preserved only when the derivation, finding,
    authority reference, and exact ChargeRule all agree.
    """
    finding = getattr(derivation, "finding", None)
    if finding is None:
        raise ValueError("freight derivation has no recovery finding")

    rule_authority = rule.authority_ref
    derived_authority = getattr(derivation, "authority_ref", None)
    authority_matches = (
        derived_authority is not None
        and finding.authority_id == derived_authority.authority_id
        and derived_authority.authority_id == rule_authority.authority_id
    )
    verified = (
        getattr(derivation, "decision", None) == "VALIDATED"
        and getattr(finding, "status", None) == "VALIDATED"
        and bool(rule.verified_controlling_authority)
        and authority_matches
    )

    locator = source_locator or f"freight://authority/{rule.authority_document_id}"
    rule_ref = RuleRef(
        rule_id=rule_authority.authority_id,
        source_hash=rule.document_source_hash,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
        verified_controlling=verified,
        source_locator=locator,
        metadata={
            "source": "freight.finding_factory.ChargeRule",
            "authority_document_id": rule.authority_document_id,
            "freight_rule_hash": rule.rule_hash,
            "charge_code": rule.charge_code,
            "pricing_model": rule.pricing_model,
        },
    )
    evidence = (
        EvidenceRef(
            evidence_id=f"freight-charge:{charge.charge_id}",
            source_hash=charge.source_hash,
            locator=f"freight://charge/{charge.charge_id}",
            kind="freight_invoice_charge",
            verified=verified,
            metadata={
                "invoice_id": charge.invoice_id,
                "shipment_id": charge.shipment_id,
                "service_date": charge.service_date,
                "charge_code": charge.charge_code,
                "billed_cents": charge.billed_cents,
            },
        ),
        EvidenceRef(
            evidence_id=f"freight-derivation:{derivation.derivation_hash}",
            source_hash=derivation.derivation_hash,
            locator=f"freight://derivation/{charge.charge_id}",
            kind="freight_charge_derivation",
            verified=verified,
            metadata={
                "decision": derivation.decision,
                "reason": derivation.reason,
                "matched_rule_hashes": list(derivation.matched_rule_hashes),
            },
        ),
    )
    return observation(
        branch=Branch.FREIGHT,
        client_id=finding.buyer_id,
        counterparty_id=finding.carrier_id,
        reference=finding.invoice_id,
        currency=finding.currency,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        occurred_on=charge.service_date,
        rule=rule_ref,
        evidence=evidence,
        reason="FREIGHT_VERIFIED_RULE_OVERCHARGE",
        confidence_basis="freight derivation + exact effective-dated ChargeRule + proof hashes",
        metadata={
            "business_unit": finding.business_unit,
            "shipment_id": finding.shipment_id,
            "customer_id": finding.customer_id,
            "charge_id": charge.charge_id,
            "freight_finding_id": finding.finding_id,
            "freight_proof_hash": finding.proof_hash,
            "freight_derivation_hash": derivation.derivation_hash,
            "freight_rule_hash": rule.rule_hash,
        },
    )


def from_freight_finding(
    finding,
    authority=None,
    *,
    source_locator: str = "freight/",
    effective_from: str | None = None,
    effective_to: str | None = None,
    occurred_on: str | None = None,
) -> RecoveryObservation:
    """Compatibility bridge for older proof objects.

    New production paths should use from_freight_derivation(). Because the
    legacy AuthorityRef has no effective dates, this function cannot preserve
    validated status unless the caller supplies both effective_from and
    occurred_on explicitly.
    """
    rule = None
    authority_window_known = bool(authority is not None and effective_from and occurred_on)
    verified = bool(
        authority_window_known
        and getattr(finding, "status", None) == "VALIDATED"
    )

    if authority is not None:
        rule = RuleRef(
            rule_id=authority.authority_id,
            source_hash=authority.source_hash,
            effective_from=effective_from or "1970-01-01",
            effective_to=effective_to,
            verified_controlling=verified,
            source_locator=source_locator,
            metadata={
                "source": "freight.contracts.AuthorityRef",
                "compatibility_bridge": True,
                "authority_window_known": authority_window_known,
            },
        )

    evidence = (
        EvidenceRef(
            evidence_id=f"freight-proof:{finding.proof_hash}",
            source_hash=finding.proof_hash,
            locator=source_locator,
            kind="freight_finding_proof",
            verified=verified,
            metadata={
                "finding_id": finding.finding_id,
                "compatibility_bridge": True,
            },
        ),
    )

    kwargs = dict(
        branch=Branch.FREIGHT,
        client_id=finding.buyer_id,
        counterparty_id=finding.carrier_id,
        reference=finding.invoice_id,
        currency=finding.currency,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        rule=rule,
        evidence=evidence,
        reason="LEGACY_FREIGHT_PROOF",
        confidence_basis=(
            "legacy freight proof + explicit authority window"
            if authority_window_known
            else "legacy freight proof; authority effective window unknown"
        ),
        metadata={
            "shipment_id": finding.shipment_id,
            "customer_id": finding.customer_id,
            "freight_finding_id": finding.finding_id,
            "freight_proof_hash": finding.proof_hash,
            "compatibility_bridge": True,
            "authority_window_known": authority_window_known,
        },
    )
    if occurred_on is not None:
        return observation(occurred_on=occurred_on, **kwargs)
    return RecoveryObservation(**kwargs)
