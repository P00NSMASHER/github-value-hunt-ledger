"""Bridge existing FreightRecovery proof objects into the RecoveryWorks ledger."""
from __future__ import annotations

import re
from freight.contracts import AuthorityRef, Finding, make_finding

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef



_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_freight_finding(finding: Finding) -> Finding:
    """Rebuild the amount- and scope-bound finding proof before treating it as evidence.

    A raw object with a caller-selected status or proof hash is not a trusted
    FreightRecovery proof. This gate also protects direct RecoveryOS callers
    that bypass the JSON importer.
    """
    if not isinstance(finding, Finding):
        raise ValueError("freight finding must be a typed, proof-bearing Finding")
    rebuilt = make_finding(
        finding_id=finding.finding_id,
        buyer_id=finding.buyer_id,
        business_unit=finding.business_unit,
        invoice_id=finding.invoice_id,
        shipment_id=finding.shipment_id,
        customer_id=finding.customer_id,
        carrier_id=finding.carrier_id,
        currency=finding.currency,
        authority_id=finding.authority_id,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        status=finding.status,
    )
    if rebuilt.proof_hash != finding.proof_hash:
        raise ValueError(f"freight finding proof hash mismatch: {finding.finding_id}")
    return finding


def verify_freight_authority(finding: Finding, authority: AuthorityRef | None) -> AuthorityRef | None:
    """Require exact authority, buyer, business unit, customer, carrier and currency identity."""
    if authority is None:
        return None
    if not isinstance(authority, AuthorityRef):
        raise ValueError("freight authority must be a typed AuthorityRef")
    observed = (
        authority.authority_id, authority.buyer_id, authority.business_unit,
        authority.customer_id, authority.carrier_id, authority.currency,
    )
    required = (
        finding.authority_id, finding.buyer_id, finding.business_unit,
        finding.customer_id, finding.carrier_id, finding.currency,
    )
    if observed != required:
        raise ValueError("freight authority identity mismatch: authority, buyer, unit, customer, carrier and currency must match finding")
    if not _SHA256_RE.fullmatch(str(authority.source_hash or "")):
        raise ValueError("freight authority source hash invalid")
    return authority


def from_freight_finding(finding, authority=None, *, source_locator: str = "freight/") -> RecoveryObservation:
    """Normalize an existing freight.contracts.Finding without weakening its proof gate.

    authority should be the matching freight.contracts.AuthorityRef. A validated
    freight finding without that authority is deliberately downgraded to REVIEW
    by the common RecoveryEngine because RecoveryOS must preserve source provenance.
    """
    finding = verify_freight_finding(finding)
    authority = verify_freight_authority(finding, authority)
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
            "business_unit": getattr(finding, "business_unit", ""),
            "customer_id": finding.customer_id,
            "freight_finding_id": finding.finding_id,
            "freight_proof_hash": finding.proof_hash,
        },
    )
