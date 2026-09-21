import json
from dataclasses import asdict

import pytest

from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    freeze_population,
    freeze_truth,
    make_finding,
)
from freight.engagement_state import resolve_engagement
from freight.external_action_authorization import (
    ActionType,
    AuthorizationState,
    assert_action_allowed,
    evaluate_authorization,
    issue_authorization,
    revoke_authorization,
)
from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import build_charter, from_dict as charter_from_dict
from freight.pilot_reporting import FindingReview, ReviewDisposition


def ready_input():
    return {
        "authorization_documented": True,
        "read_only_access": True,
        "population_reproducible": True,
        "incumbent_output_sealable": True,
        "settlement_observable": True,
        "material_authority_reconstructable": True,
        "customer_identity_stable": True,
        "carrier_identity_stable": True,
        "retention_defined": True,
        "deletion_defined": True,
        "invoice_source_coverage": 1.0,
        "authority_source_coverage": 1.0,
        "shipment_evidence_coverage": 1.0,
    }


def charter():
    packet = build_packet(
        ready_input(),
        {
            "status": "READY",
            "route": "CONTROLLED_MANUAL_BLIND_PILOT",
            "blockers": [],
            "conditions": [],
            "warnings": [],
        },
    )
    request = charter_from_dict(
        {
            "engagement_id": "ENG-001",
            "buyer_id": "buyer-a",
            "business_unit": "bu-1",
            "population_rule": "August approved invoices",
            "source_date_start": "2026-08-01",
            "source_date_end": "2026-08-31",
            "carrier_scope": ["carrier-1"],
            "mode_scope": ["LTL"],
            "fixed_fee_usd": 20000,
            "buyer_truth_owner_role": "Truth Owner",
            "buyer_action_approver_role": "VP Supply Chain",
            "freight_engagement_owner_role": "Pilot Lead",
            "buyer_acknowledges_scope": True,
            "buyer_acknowledges_blind_protocol": True,
            "buyer_acknowledges_report_totals_separate": True,
            "buyer_acknowledges_no_guaranteed_recovery": True,
            "freight_acknowledges_no_external_action_without_buyer_approval": True,
        }
    )
    return json.loads(json.dumps(asdict(build_charter(json.loads(json.dumps(asdict(packet))), request))))


def proof():
    population = freeze_population(
        "buyer-a",
        "bu-1",
        "August approved invoices",
        (
            PopulationRow(
                invoice_id="INV-1",
                shipment_id="SHIP-1",
                customer_id="CUST-1",
                carrier_id="carrier-1",
                currency="USD",
                source_hash="1" * 64,
            ),
            PopulationRow(
                invoice_id="INV-2",
                shipment_id="SHIP-2",
                customer_id="CUST-1",
                carrier_id="carrier-1",
                currency="USD",
                source_hash="2" * 64,
            ),
        ),
    )
    authority = AuthorityRef(
        authority_id="AUTH-1",
        buyer_id="buyer-a",
        business_unit="bu-1",
        customer_id="CUST-1",
        carrier_id="carrier-1",
        currency="USD",
        source_hash="3" * 64,
    )
    findings = (
        make_finding(
            finding_id="F-1",
            buyer_id="buyer-a",
            business_unit="bu-1",
            invoice_id="INV-1",
            shipment_id="SHIP-1",
            customer_id="CUST-1",
            carrier_id="carrier-1",
            currency="USD",
            authority_id="AUTH-1",
            expected_cents=10000,
            actual_cents=12500,
            status="VALIDATED",
        ),
        make_finding(
            finding_id="F-2",
            buyer_id="buyer-a",
            business_unit="bu-1",
            invoice_id="INV-2",
            shipment_id="SHIP-2",
            customer_id="CUST-1",
            carrier_id="carrier-1",
            currency="USD",
            authority_id="AUTH-1",
            expected_cents=10000,
            actual_cents=11000,
            status="VALIDATED",
        ),
    )
    truth = freeze_truth(population, (authority,), findings)
    reviews = (
        FindingReview("F-1", ReviewDisposition.CONFIRMED, 5),
        FindingReview("F-2", ReviewDisposition.CONFIRMED, 5),
    )
    return truth, reviews


def auth(**overrides):
    c = charter()
    resolution = resolve_engagement(c)
    truth, reviews = proof()
    kwargs = dict(
        resolution=resolution,
        operative_charter=c,
        truth=truth,
        reviews=reviews,
        authorization_id="ACT-001",
        action_type=ActionType.SUBMIT_DISPUTE,
        target_carrier_id="carrier-1",
        recipient_reference_hash="4" * 64,
        action_payload_hash="5" * 64,
        finding_ids=("F-1", "F-2"),
        currency="USD",
        authorized_cents=3000,
        approver_role="VP Supply Chain",
        issued_on="2026-09-21",
        expires_on="2026-09-30",
    )
    kwargs.update(overrides)
    return issue_authorization(**kwargs)


def test_confirmed_validated_findings_can_be_narrowly_authorized():
    a = auth()
    assert a.authorized_cents == 3000
    assert a.finding_ids == ("F-1", "F-2")
    assert a.money_movement_authorized is False
    assert a.settlement_acceptance_authorized is False
    assert a.general_contact_authorized is False
    assert a.automatic_execution_authorized is False


def test_prelaunch_engagement_cannot_issue_external_action():
    c = charter()
    c["charter_state"] = "PRELAUNCH_ACCEPTED"
    c["customer_data_authorized"] = False
    body = {k: v for k, v in c.items() if k != "charter_hash"}
    from freight.contracts import canonical_hash

    c["charter_hash"] = canonical_hash(body)
    resolution = resolve_engagement(c)
    truth, reviews = proof()
    with pytest.raises(ValueError, match="ACTIVE"):
        issue_authorization(
            resolution=resolution,
            operative_charter=c,
            truth=truth,
            reviews=reviews,
            authorization_id="ACT-001",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="4" * 64,
            action_payload_hash="5" * 64,
            finding_ids=("F-1",),
            currency="USD",
            authorized_cents=1000,
            approver_role="VP Supply Chain",
            issued_on="2026-09-21",
            expires_on="2026-09-22",
        )


def test_unconfirmed_review_cannot_be_authorized():
    c = charter()
    resolution = resolve_engagement(c)
    truth, _ = proof()
    reviews = (FindingReview("F-1", ReviewDisposition.UNRESOLVED, 1),)
    with pytest.raises(ValueError, match="CONFIRMED"):
        issue_authorization(
            resolution=resolution,
            operative_charter=c,
            truth=truth,
            reviews=reviews,
            authorization_id="ACT-001",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="4" * 64,
            action_payload_hash="5" * 64,
            finding_ids=("F-1",),
            currency="USD",
            authorized_cents=1000,
            approver_role="VP Supply Chain",
            issued_on="2026-09-21",
            expires_on="2026-09-22",
        )


def test_amount_cannot_exceed_selected_validated_findings():
    with pytest.raises(ValueError, match="cannot exceed"):
        auth(authorized_cents=999999)


def test_approver_must_match_charter_role():
    with pytest.raises(ValueError, match="approver_role"):
        auth(approver_role="Different Role")


def test_action_payload_and_recipient_are_hash_bound():
    a = auth()
    assert_action_allowed(
        a,
        as_of_date="2026-09-22",
        action_type=ActionType.SUBMIT_DISPUTE,
        target_carrier_id="carrier-1",
        recipient_reference_hash="4" * 64,
        action_payload_hash="5" * 64,
        finding_ids=("F-1", "F-2"),
        currency="USD",
        requested_cents=2500,
    )
    with pytest.raises(ValueError, match="payload"):
        assert_action_allowed(
            a,
            as_of_date="2026-09-22",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="4" * 64,
            action_payload_hash="6" * 64,
            finding_ids=("F-1", "F-2"),
            currency="USD",
            requested_cents=2500,
        )
    with pytest.raises(ValueError, match="recipient"):
        assert_action_allowed(
            a,
            as_of_date="2026-09-22",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="7" * 64,
            action_payload_hash="5" * 64,
            finding_ids=("F-1", "F-2"),
            currency="USD",
            requested_cents=2500,
        )


def test_action_cannot_exceed_amount_or_finding_set():
    a = auth()
    with pytest.raises(ValueError, match="amount"):
        assert_action_allowed(
            a,
            as_of_date="2026-09-22",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="4" * 64,
            action_payload_hash="5" * 64,
            finding_ids=("F-1", "F-2"),
            currency="USD",
            requested_cents=3001,
        )
    with pytest.raises(ValueError, match="finding set"):
        assert_action_allowed(
            a,
            as_of_date="2026-09-22",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="4" * 64,
            action_payload_hash="5" * 64,
            finding_ids=("F-1",),
            currency="USD",
            requested_cents=1000,
        )


def test_expiry_and_future_issuance_are_fail_closed():
    a = auth()
    assert evaluate_authorization(a, as_of_date="2026-09-20").state == AuthorizationState.NOT_YET_ACTIVE.value
    assert evaluate_authorization(a, as_of_date="2026-10-01").state == AuthorizationState.EXPIRED.value


def test_authorization_validity_is_bounded():
    with pytest.raises(ValueError, match="validity"):
        auth(expires_on="2026-11-30")


def test_revocation_immediately_blocks_action():
    a = auth()
    r = revoke_authorization(
        a,
        revocation_id="REV-1",
        revoked_on="2026-09-23",
        approver_role="VP Supply Chain",
        reason="Buyer withdrew approval",
    )
    assert evaluate_authorization(a, as_of_date="2026-09-22", revocations=(r,)).state == AuthorizationState.ACTIVE.value
    assert evaluate_authorization(a, as_of_date="2026-09-23", revocations=(r,)).state == AuthorizationState.REVOKED.value
    with pytest.raises(ValueError, match="REVOKED"):
        assert_action_allowed(
            a,
            as_of_date="2026-09-23",
            action_type=ActionType.SUBMIT_DISPUTE,
            target_carrier_id="carrier-1",
            recipient_reference_hash="4" * 64,
            action_payload_hash="5" * 64,
            finding_ids=("F-1", "F-2"),
            currency="USD",
            requested_cents=2500,
            revocations=(r,),
        )


def test_tampered_authorization_is_rejected():
    a = auth()
    object.__setattr__(a, "authorized_cents", 999999)
    with pytest.raises(ValueError, match="authorization hash mismatch"):
        evaluate_authorization(a, as_of_date="2026-09-22")
