"""Bridge existing FreightRecovery proof objects into the RecoveryWorks ledger."""
from __future__ import annotations

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef


def from_freight_finding(finding, authority=None, *, source_locator: str = "freight/") -> RecoveryObservation:
    """Normalize an existing freight.contracts.Finding without weakening its proof gate.

    authority should be the matching freight.contracts.AuthorityRef. A validated
    freight finding without that authority is deliberately downgraded to REVIEW
    by the common RecoveryEngine because RecoveryOS must preserve source provenance.
    """
    rule = None
    evidence_verified = False
    if authority is not None:
        rule = RuleRef(
            rule_id=authority.authority_id,
            source_hash=authority.source_hash,
            effective_from="1970-01-01",
            effective_to=None,
            verified_controlling=(getattr(finding, "status", None) == "VALIDATED"),
            source_locator=source_locator,
            metadata={"source": "freight.contracts.AuthorityRef"},
        )
        evidence_verified = rule.verified_controlling

    evidence = (
        EvidenceRef(
            evidence_id=f"freight-proof:{finding.proof_hash}",
            source_hash=finding.proof_hash,
            locator=source_locator,
            kind="freight_finding_proof",
            verified=evidence_verified,
            metadata={"finding_id": finding.finding_id},
        ),
    )
    return RecoveryObservation(
        branch=Branch.FREIGHT,
        client_id=finding.buyer_id,
        counterparty_id=finding.carrier_id,
        reference=finding.invoice_id,
        currency=finding.currency,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        rule=rule,
        evidence=evidence,
        reason="EXISTING_FREIGHT_PROOF",
        confidence_basis="existing freight proof hash + verified authority when supplied",
        metadata={
            "shipment_id": finding.shipment_id,
            "customer_id": finding.customer_id,
            "freight_finding_id": finding.finding_id,
            "freight_proof_hash": finding.proof_hash,
        },
    )
