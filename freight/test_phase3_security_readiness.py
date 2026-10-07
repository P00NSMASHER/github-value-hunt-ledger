import json
from pathlib import Path

import pytest

from freight.security_readiness import (
    PENDING_EXTERNAL,
    PROVEN,
    load_current,
    summarize_security_readiness,
    validate_security_readiness,
)


ROOT = Path(__file__).resolve().parents[1]


def test_current_phase3_security_readiness_is_valid_and_conservative():
    payload = load_current(ROOT)
    assert validate_security_readiness(payload) == []
    summary = summarize_security_readiness(payload)
    assert summary.proven >= 7
    assert summary.pending_external == 7
    assert set(summary.external_required) == {
        "enterprise_sso",
        "independent_penetration_test",
        "iso27001",
        "mfa",
        "provider_backup_restore_evidence",
        "provider_encryption_evidence",
        "soc2_type2",
    }


def test_external_assurance_cannot_be_self_promoted_to_proven():
    payload = load_current(ROOT)
    payload["controls"]["soc2_type2"]["state"] = PROVEN
    errors = validate_security_readiness(payload)
    assert any("soc2_type2 must remain PENDING_EXTERNAL" in error for error in errors)


def test_proven_tenant_isolation_requires_a_real_negative_probe():
    payload = load_current(ROOT)
    payload["controls"]["cross_tenant_isolation"]["facts"]["negative_cross_tenant_insert_rejected"] = False
    errors = validate_security_readiness(payload)
    assert any("rejected negative probe" in error for error in errors)


def test_proven_audit_chain_requires_zero_hash_and_link_failures():
    payload = load_current(ROOT)
    payload["controls"]["tamper_evident_audit_chain"]["facts"]["broken_links"] = 1
    errors = validate_security_readiness(payload)
    assert any("zero broken links" in error for error in errors)


def test_authentication_claim_fails_if_session_is_relaxed_past_24_hours():
    payload = load_current(ROOT)
    payload["controls"]["authentication"]["facts"]["session_max_hours"] = 168
    errors = validate_security_readiness(payload)
    assert any("session exceeds 24 hours" in error for error in errors)


def test_readiness_file_contains_no_certification_claim():
    payload = json.loads((ROOT / "freight" / "PHASE3_SECURITY_READINESS_2026-10-07.json").read_text())
    assert payload["controls"]["soc2_type2"]["state"] == PENDING_EXTERNAL
    assert payload["controls"]["iso27001"]["state"] == PENDING_EXTERNAL
    assert payload["controls"]["independent_penetration_test"]["state"] == PENDING_EXTERNAL
