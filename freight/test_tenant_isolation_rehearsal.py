from freight.tenant_isolation_rehearsal import run_tenant_isolation_rehearsal


def test_tenant_isolation_rehearsal_passes_all_internal_negative_checks():
    evidence = run_tenant_isolation_rehearsal()
    assert evidence.gap_id == "FRT-SEC-001"
    assert evidence.scope_model == "buyer_id + business_unit"
    assert evidence.check_count >= 10
    assert evidence.passed_count == evidence.check_count
    assert all(check.passed for check in evidence.checks)
    assert len(evidence.evidence_hash) == 64


def test_tenant_isolation_rehearsal_covers_buyer_and_business_unit_boundaries():
    evidence = run_tenant_isolation_rehearsal()
    ids = {check.check_id for check in evidence.checks}
    assert "SETTLEMENT_CROSS_BUYER_MATCH_DENIED" in ids
    assert "SETTLEMENT_CROSS_BUYER_REVIEW_DENIED" in ids
    assert "SETTLEMENT_CROSS_BU_READ_DENIED" in ids
    assert "SETTLEMENT_DIRECT_SQL_CROSS_SCOPE_DENIED" in ids
    assert "AUDIT_SCOPE_BOUND_RECORDS" in ids


def test_internal_rehearsal_does_not_overclaim_deployed_multi_tenant_proof():
    evidence = run_tenant_isolation_rehearsal()
    assert evidence.deployed_multi_tenant_claimed is False
    assert evidence.denied_attempt_audit_log_claimed is False
    assert len(evidence.remaining_evidence) == 3


def test_tenant_isolation_evidence_is_deterministic():
    assert run_tenant_isolation_rehearsal() == run_tenant_isolation_rehearsal()
