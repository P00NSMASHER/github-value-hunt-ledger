from __future__ import annotations

from recoveryworks.engine import RecoveryEngine, RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, FindingState, RuleRef
from recoveryworks.source_coverage import SourceCoverageReceipt, SourceState


def evidence() -> tuple[EvidenceRef, ...]:
    return (
        EvidenceRef(
            evidence_id="ev-1",
            source_hash="a" * 64,
            locator="fixture://invoice/1",
            kind="invoice",
            verified=True,
        ),
    )


def rule() -> RuleRef:
    return RuleRef(
        rule_id="rule-1",
        source_hash="b" * 64,
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="fixture://contract/1",
    )


def observation(*, receipts: tuple[SourceCoverageReceipt, ...] = ()) -> RecoveryObservation:
    return RecoveryObservation(
        branch=Branch.AP,
        client_id="client",
        counterparty_id="vendor",
        reference="invoice-1",
        currency="USD",
        expected_cents=9000,
        actual_cents=10000,
        rule=rule(),
        evidence=evidence(),
        reason="test overpayment",
        confidence_basis="deterministic fixture",
        source_coverage=receipts,
    )


def receipt(state: SourceState) -> SourceCoverageReceipt:
    return SourceCoverageReceipt(
        source_id="vendor_statement",
        object_type="statement",
        window="2026-01",
        state=state,
        source_hash="c" * 64,
        locator="fixture://statement/2026-01",
        observed_at="2026-02-01T00:00:00Z",
    )


def test_legacy_observation_remains_validated_without_receipts():
    finding = RecoveryEngine().evaluate(observation())
    assert finding is not None
    assert finding.state is FindingState.VALIDATED
    assert "source_coverage_hashes" not in finding.metadata


def test_present_source_receipt_allows_validation_and_enters_identity():
    legacy = RecoveryEngine().evaluate(observation())
    finding = RecoveryEngine().evaluate(observation(receipts=(receipt(SourceState.PRESENT),)))
    assert finding is not None and legacy is not None
    assert finding.state is FindingState.VALIDATED
    assert finding.finding_id != legacy.finding_id
    assert len(finding.metadata["source_coverage_hashes"]) == 1


def test_verified_empty_is_conclusive_source_observation():
    finding = RecoveryEngine().evaluate(observation(receipts=(receipt(SourceState.VERIFIED_EMPTY),)))
    assert finding is not None
    assert finding.state is FindingState.VALIDATED


def test_partial_source_forces_review_and_records_blocker():
    finding = RecoveryEngine().evaluate(observation(receipts=(receipt(SourceState.PARTIAL),)))
    assert finding is not None
    assert finding.state is FindingState.REVIEW
    assert finding.metadata["source_coverage_blockers"] == [
        "vendor_statement:statement:2026-01:PARTIAL"
    ]


def test_unavailable_source_forces_review():
    finding = RecoveryEngine().evaluate(observation(receipts=(receipt(SourceState.UNAVAILABLE),)))
    assert finding is not None
    assert finding.state is FindingState.REVIEW
