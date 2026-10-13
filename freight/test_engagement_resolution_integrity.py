"""Adversarial resolver tests: a self-hash is not approval for scope changes.

All inputs are fictional. These tests do not represent customer consent,
hosted authorization, completed filings, or live financial operations.
"""
from copy import deepcopy
from dataclasses import asdict
import pytest

from freight.engagement_state import _hash, resolve_engagement
from freight.pilot_amendment import build_amendment, from_dict as amendment_request
from freight.test_engagement_state import charter, amendment, activation, charter_req


def seal(document, key):
    document[key] = _hash({k: v for k, v in document.items() if k != key})
    return document


def role_chain():
    base = charter()
    replacement = charter(buyer_action_approver_role="New Approver")
    request = amendment_request({
        "amendment_id": "AMD-001", "reason": "Approved role change",
        "buyer_acknowledges_change": True, "freight_acknowledges_change": True,
        "buyer_action_approver_role": "New Approver",
    })
    doc = asdict(build_amendment(base, request, replacement))
    return deepcopy(base), deepcopy(replacement), deepcopy(doc)


def scope_chain():
    base = charter()
    replacement = charter(
        population_rule="Approved September invoices",
        warnings=["source-scope-reviewed"],
    )
    request = amendment_request({
        "amendment_id": "AMD-001", "reason": "Approved scope change",
        "buyer_acknowledges_change": True, "freight_acknowledges_change": True,
        "population_rule": "Approved September invoices",
    })
    doc = asdict(build_amendment(base, request, replacement))
    return deepcopy(base), deepcopy(replacement), deepcopy(doc)


def change_replacement(base, replacement, doc, **changes):
    replacement.update(changes)
    seal(replacement, "charter_hash")
    doc["replacement_charter_hash"] = replacement["charter_hash"]
    seal(doc, "amendment_hash")
    return base, doc, replacement


def resolve_chain(triplet):
    base, doc, replacement = triplet
    return resolve_engagement(base, [doc], [replacement])


def test_control_valid_role_and_material_scope_paths():
    assert resolve_chain(role_chain()).engagement_state == "ACTIVE"
    assert resolve_chain(scope_chain()).engagement_state == "ACTIVE"


@pytest.mark.parametrize("field, value", [
    ("population_rule", "September and October paid invoices"),
    ("source_date_start", "2026-07-01"),
    ("source_date_end", "2026-09-30"),
    ("carrier_scope", ["carrier-1", "unapproved-carrier"]),
    ("mode_scope", ["LTL", "unapproved-mode"]),
    ("fixed_fee_usd", 23000),
    ("buyer_truth_owner_role", "Unapproved truth owner"),
    ("freight_engagement_owner_role", "Unapproved pilot lead"),
])
def test_self_rehashed_role_amendment_cannot_expand_unapproved_fields(field, value):
    base, replacement, doc = role_chain()
    with pytest.raises(ValueError, match="replacement.*changed|changed_fields"):
        resolve_chain(change_replacement(base, replacement, doc, **{field: value}))


@pytest.mark.parametrize("changed_fields", [
    [], ["fixed_fee_usd"], ["buyer_action_approver_role", "fixed_fee_usd"],
    ["buyer_action_approver_role", "buyer_action_approver_role"],
    ["unknown_field"], "buyer_action_approver_role", [1],
])
def test_rehashed_superseded_record_cannot_fake_declared_changes(changed_fields):
    base, replacement, doc = role_chain()
    doc["changed_fields"] = changed_fields
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match="changed_fields"):
        resolve_engagement(base, [doc], [replacement])


@pytest.mark.parametrize("name", [
    "requires_readiness_revalidation", "requires_launch_revalidation",
    "requires_new_activation", "requires_reacknowledgment",
])
def test_rehashed_role_amendment_cannot_forge_required_review_flags(name):
    base, replacement, doc = role_chain()
    doc[name] = not doc[name]
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match=name):
        resolve_engagement(base, [doc], [replacement])


@pytest.mark.parametrize("name", [
    "requires_readiness_revalidation", "requires_launch_revalidation",
    "requires_new_activation", "requires_reacknowledgment",
])
def test_rehashed_material_amendment_cannot_downgrade_required_review_flags(name):
    base, replacement, doc = scope_chain()
    assert doc[name] is True
    doc[name] = False
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match=name):
        resolve_engagement(base, [doc], [replacement])


@pytest.mark.parametrize("field", ["customer_data_authorized", "kickoff_suspended"])
def test_superseded_amendment_must_match_actual_replacement_authorization(field):
    base, replacement, doc = role_chain()
    doc[field] = not doc[field]
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match=field):
        resolve_engagement(base, [doc], [replacement])


def test_material_scope_change_rejects_reused_activation_evidence():
    base, replacement, doc = scope_chain()
    with pytest.raises(ValueError, match="Activation Packet|activation_hash"):
        resolve_chain(change_replacement(
            base, replacement, doc, activation_hash=base["activation_hash"]
        ))


@pytest.mark.parametrize("field, value", [
    ("kickoff_suspended", True),
    ("customer_data_authorized", True),
    ("requires_reacknowledgment", False),
    ("requires_new_activation", True),
])
def test_pending_amendment_cannot_claim_impossible_execution_or_review_state(field, value):
    base = charter()
    doc = amendment(base, buyer_acknowledges_change=False)
    doc[field] = value
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match=field):
        resolve_engagement(base, [doc])


@pytest.mark.parametrize("field, value", [
    ("customer_data_authorized", True),
    ("requires_reacknowledgment", False),
    ("requires_new_activation", True),
])
def test_accepted_amendment_cannot_claim_impossible_execution_or_review_state(field, value):
    base = charter()
    doc = amendment(base)
    doc[field] = value
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match=field):
        resolve_engagement(base, [doc])


def test_amendment_cannot_be_supplied_with_nonexistent_base():
    base = charter()
    doc = amendment(base)
    doc["base_charter_hash"] = "0" * 64
    seal(doc, "amendment_hash")
    with pytest.raises(ValueError, match="unknown base Charter"):
        resolve_engagement(base, [doc])


@pytest.mark.parametrize("field, value", [
    ("activation_hash", "not-a-sha"),
    ("fixed_fee_usd", -20),
    ("fixed_fee_usd", True),
    ("fixed_fee_usd", "free"),
    ("source_date_start", "2026-09-05"),
    ("source_date_end", "not-a-date"),
    ("carrier_scope", []),
    ("mode_scope", ["", "LTL"]),
    ("buyer_truth_owner_role", ""),
    ("selected_offer", ""),
])
def test_self_hashed_charter_cannot_launder_invalid_operating_fields(field, value):
    base = charter()
    base[field] = value
    seal(base, "charter_hash")
    with pytest.raises(ValueError, match=field):
        resolve_engagement(base)


def test_valid_prelaunch_and_pending_amendment_still_supported():
    base = charter(status="BLOCKED", route="DEPLOYED_PILOT_BLOCKED")
    assert resolve_engagement(base).engagement_state == "PRELAUNCH"
    active = charter()
    pending = amendment(active, buyer_acknowledges_change=False)
    assert resolve_engagement(active, [pending]).engagement_state == "ACTIVE_WITH_PENDING_AMENDMENT"
