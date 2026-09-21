import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import pytest

from freight.carrier_action_execution import (
    CarrierActionDeliveryReceipt,
    CarrierActionExecutionIntent,
    CarrierActionExecutionReceipt,
)
from freight.carrier_action_execution_store import (
    ALREADY_DELIVERED,
    ALREADY_RECORDED,
    ALREADY_RESERVED,
    ALREADY_SUBMITTED,
    DELIVERED,
    DELIVERY_RECORDED,
    FAILED_ONLY,
    IN_FLIGHT,
    RECORDED,
    RESERVED,
    SUBMITTED,
    CarrierActionExecutionStore,
)
from freight.contracts import canonical_hash


def make_intent(
    *,
    buyer="buyer",
    business_unit="unit",
    prepared_at="2026-09-21T11:00:00.000000Z",
    authorization_hash="a"*64,
):
    values = dict(
        buyer_id=buyer,
        business_unit=business_unit,
        authorization_id="AUTH-1",
        authorization_hash=authorization_hash,
        proposal_hash="b"*64,
        payload_hash="c"*64,
        recipient_reference_hash="d"*64,
        action_type="REQUEST_CREDIT_REVIEW",
        target_carrier_id="carrier",
        target_customer_id="customer",
        currency="USD",
        requested_cents=2500,
        finding_ids=("f1",),
    )
    key_body = {
        "schema": 1,
        "buyer_id": values["buyer_id"],
        "business_unit": values["business_unit"],
        "authorization_hash": values["authorization_hash"],
        "proposal_hash": values["proposal_hash"],
        "payload_hash": values["payload_hash"],
        "recipient_reference_hash": values["recipient_reference_hash"],
        "action_type": values["action_type"],
        "target_carrier_id": values["target_carrier_id"],
        "target_customer_id": values["target_customer_id"],
        "currency": values["currency"],
        "finding_ids": values["finding_ids"],
        "requested_cents": values["requested_cents"],
    }
    execution_key = canonical_hash(key_body)
    body = {
        "schema": 1,
        "execution_key": execution_key,
        **values,
        "prepared_at": prepared_at,
        "subject": "Freight credit review request",
        "body_text": "Please review this freight charge.",
    }
    return CarrierActionExecutionIntent(
        execution_key=execution_key,
        **values,
        prepared_at=prepared_at,
        subject=body["subject"],
        body_text=body["body_text"],
        intent_hash=canonical_hash(body),
    )


def make_receipt(
    intent,
    *,
    outcome="FAILED",
    executed_at="2026-09-21T11:01:00.000000Z",
    external_reference_hash="e"*64,
    evidence_source_hash="f"*64,
):
    submitted = outcome in {"SUBMITTED", "DELIVERED"}
    delivered = outcome == "DELIVERED"
    fields = dict(
        execution_key=intent.execution_key,
        buyer_id=intent.buyer_id,
        business_unit=intent.business_unit,
        intent_hash=intent.intent_hash,
        authorization_id=intent.authorization_id,
        authorization_hash=intent.authorization_hash,
        proposal_hash=intent.proposal_hash,
        payload_hash=intent.payload_hash,
        recipient_reference_hash=intent.recipient_reference_hash,
        action_type=intent.action_type,
        target_carrier_id=intent.target_carrier_id,
        target_customer_id=intent.target_customer_id,
        currency=intent.currency,
        requested_cents=intent.requested_cents,
        finding_ids=intent.finding_ids,
        prepared_at=intent.prepared_at,
        executed_at=executed_at,
        channel="EMAIL",
        outcome=outcome,
        external_reference_hash=external_reference_hash,
        evidence_source_hash=evidence_source_hash,
        executor_role="Freight Operator",
        action_submitted=submitted,
        delivery_confirmed=delivered,
    )
    return CarrierActionExecutionReceipt(
        **fields,
        receipt_hash=canonical_hash({"schema": 1, **fields}),
    )


def make_delivery(
    submitted,
    *,
    delivered_at="2026-09-21T11:05:00.000000Z",
    delivery_reference_hash="1"*64,
    evidence_source_hash="2"*64,
):
    fields = dict(
        execution_key=submitted.execution_key,
        buyer_id=submitted.buyer_id,
        business_unit=submitted.business_unit,
        submitted_receipt_hash=submitted.receipt_hash,
        authorization_hash=submitted.authorization_hash,
        proposal_hash=submitted.proposal_hash,
        payload_hash=submitted.payload_hash,
        recipient_reference_hash=submitted.recipient_reference_hash,
        action_type=submitted.action_type,
        target_carrier_id=submitted.target_carrier_id,
        target_customer_id=submitted.target_customer_id,
        currency=submitted.currency,
        requested_cents=submitted.requested_cents,
        finding_ids=submitted.finding_ids,
        submitted_at=submitted.executed_at,
        delivered_at=delivered_at,
        channel=submitted.channel,
        submission_external_reference_hash=submitted.external_reference_hash,
        delivery_reference_hash=delivery_reference_hash,
        delivery_evidence_source_hash=evidence_source_hash,
        verifier_role="Delivery Verifier",
        delivery_confirmed=True,
    )
    return CarrierActionDeliveryReceipt(
        **fields,
        delivery_receipt_hash=canonical_hash({"schema": 1, **fields}),
    )


def store(tmp_path, buyer="buyer", business_unit="unit"):
    return CarrierActionExecutionStore(
        tmp_path / "execution.sqlite3",
        buyer_id=buyer,
        business_unit=business_unit,
    )


def test_file_backed_store_required():
    with pytest.raises(ValueError, match="file-backed"):
        CarrierActionExecutionStore(":memory:", buyer_id="b", business_unit="u")


def test_store_rejects_tampered_execution_intent_proof(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    bad = replace(intent, intent_hash="0" * 64)
    with pytest.raises(ValueError, match="intent hash mismatch"):
        s.reserve_send_attempt(
            bad,
            attempt_id="attempt-bad",
            started_at="2026-09-21T11:00:10Z",
        )


def test_store_rejects_noncanonical_finding_order(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    bad = replace(intent, finding_ids=("z-finding", "a-finding"))
    with pytest.raises(ValueError, match="canonical sorted order"):
        s.reserve_send_attempt(
            bad,
            attempt_id="attempt-order",
            started_at="2026-09-21T11:00:10Z",
        )


def test_store_rejects_invalid_self_hashed_intent_semantics(tmp_path):
    s = store(tmp_path)
    intent = make_intent()

    bad_action = replace(intent, action_type="WIRE_MONEY")
    with pytest.raises(ValueError, match="action_type"):
        s.reserve_send_attempt(
            bad_action,
            attempt_id="attempt-bad-action",
            started_at="2026-09-21T11:00:10Z",
        )

    bad_amount = replace(intent, requested_cents=2**63)
    with pytest.raises(ValueError, match="within range"):
        s.reserve_send_attempt(
            bad_amount,
            attempt_id="attempt-bad-amount",
            started_at="2026-09-21T11:00:10Z",
        )

    bad_finding = replace(intent, finding_ids=("",))
    with pytest.raises(ValueError, match="finding_id"):
        s.reserve_send_attempt(
            bad_finding,
            attempt_id="attempt-bad-finding",
            started_at="2026-09-21T11:00:10Z",
        )


def test_new_send_attempt_reserves_exclusive_slot(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    decision = s.reserve_send_attempt(
        intent,
        attempt_id="attempt-1",
        started_at="2026-09-21T11:00:10Z",
    )
    assert decision.status == RESERVED
    assert decision.execution_key == intent.execution_key
    assert decision.attempt_id == "attempt-1"
    assert len(decision.reservation_hash) == 64
    state = s.execution_state(intent.execution_key)
    assert state.state == IN_FLIGHT
    assert state.active_attempt_id == "attempt-1"


def test_exact_attempt_replay_is_idempotent_but_second_worker_is_blocked(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    first = s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    same = s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    other = s.reserve_send_attempt(
        intent, attempt_id="attempt-2", started_at="2026-09-21T11:00:11Z"
    )
    assert first.status == RESERVED
    assert same.status == ALREADY_RESERVED
    assert same.reservation_hash == first.reservation_hash
    assert other.status == IN_FLIGHT
    assert other.attempt_id == "attempt-1"


def test_active_send_lock_survives_process_restart(tmp_path):
    s1 = store(tmp_path)
    intent = make_intent()
    s1.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    s2 = store(tmp_path)
    blocked = s2.reserve_send_attempt(
        intent, attempt_id="attempt-2", started_at="2026-09-21T11:01:00Z"
    )
    assert blocked.status == IN_FLIGHT
    assert blocked.attempt_id == "attempt-1"


def test_failed_attempt_releases_slot_and_allows_new_attempt(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    failed = make_receipt(intent, outcome="FAILED")
    assert s.record_execution_receipt(attempt_id="attempt-1", receipt=failed) == RECORDED
    assert s.record_execution_receipt(attempt_id="attempt-1", receipt=failed) == ALREADY_RECORDED
    state = s.execution_state(intent.execution_key)
    assert state.state == FAILED_ONLY
    assert state.failed_attempt_count == 1
    retry = s.reserve_send_attempt(
        intent, attempt_id="attempt-2", started_at="2026-09-21T11:02:00Z"
    )
    assert retry.status == RESERVED


def test_terminal_attempt_id_cannot_be_reused_for_send(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    s.record_execution_receipt(
        attempt_id="attempt-1",
        receipt=make_receipt(intent, outcome="FAILED"),
    )
    with pytest.raises(ValueError, match="terminal state"):
        s.reserve_send_attempt(
            intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
        )


def test_submitted_attempt_permanently_blocks_new_send_slot(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    submitted = make_receipt(intent, outcome="SUBMITTED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=submitted)
    assert s.execution_state(intent.execution_key).state == SUBMITTED
    blocked = s.reserve_send_attempt(
        intent, attempt_id="attempt-2", started_at="2026-09-21T11:02:00Z"
    )
    assert blocked.status == ALREADY_SUBMITTED
    assert blocked.attempt_id is None


def test_immediate_delivered_receipt_sets_delivered_state(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    delivered = make_receipt(intent, outcome="DELIVERED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=delivered)
    state = s.execution_state(intent.execution_key)
    assert state.state == DELIVERED
    assert state.delivery_receipt_hash is None
    assert state.successful_receipt_hash == delivered.receipt_hash


def test_async_delivery_is_persisted_once_and_is_idempotent(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    submitted = make_receipt(intent, outcome="SUBMITTED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=submitted)
    delivery = make_delivery(submitted)
    assert s.record_delivery_receipt(delivery) == DELIVERY_RECORDED
    assert s.record_delivery_receipt(delivery) == ALREADY_DELIVERED
    state = s.execution_state(intent.execution_key)
    assert state.state == DELIVERED
    assert state.delivery_receipt_hash == delivery.delivery_receipt_hash


def test_different_second_delivery_is_rejected(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    submitted = make_receipt(intent, outcome="SUBMITTED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=submitted)
    first = make_delivery(submitted)
    s.record_delivery_receipt(first)
    second = make_delivery(
        submitted,
        delivered_at="2026-09-21T11:06:00.000000Z",
        delivery_reference_hash="3"*64,
        evidence_source_hash="4"*64,
    )
    with pytest.raises(ValueError, match="different delivery"):
        s.record_delivery_receipt(second)


def test_delivery_requires_persisted_submitted_receipt(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    submitted = make_receipt(intent, outcome="SUBMITTED")
    with pytest.raises(ValueError, match="unknown submitted receipt"):
        s.record_delivery_receipt(make_delivery(submitted))


def test_scope_isolation_prevents_cross_tenant_persistence(tmp_path):
    first = store(tmp_path, buyer="buyer-a", business_unit="unit")
    second = store(tmp_path, buyer="buyer-b", business_unit="unit")
    intent_a = make_intent(buyer="buyer-a")
    first.reserve_send_attempt(
        intent_a, attempt_id="attempt-a", started_at="2026-09-21T11:00:10Z"
    )
    with pytest.raises(ValueError, match="scope"):
        second.reserve_send_attempt(
            intent_a, attempt_id="attempt-b", started_at="2026-09-21T11:00:10Z"
        )
    assert second.execution_state(intent_a.execution_key).state == "NOT_FOUND"


def test_same_business_action_in_different_buyer_gets_different_execution_key():
    a = make_intent(buyer="buyer-a")
    b = make_intent(buyer="buyer-b")
    assert a.execution_key != b.execution_key


def test_changed_preparation_cannot_replay_same_execution_key_as_new_intent(tmp_path):
    s = store(tmp_path)
    first = make_intent()
    s.reserve_send_attempt(
        first, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    changed = make_intent(prepared_at="2026-09-21T11:00:05.000000Z")
    assert changed.execution_key == first.execution_key
    assert changed.intent_hash != first.intent_hash
    with pytest.raises(ValueError, match="immutable execution intent"):
        s.reserve_send_attempt(
            changed,
            attempt_id="attempt-2",
            started_at="2026-09-21T11:00:10Z",
        )


def test_execution_receipt_requires_active_slot_and_correct_attempt(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    receipt = make_receipt(intent, outcome="FAILED")
    with pytest.raises(ValueError, match="unknown send attempt"):
        s.record_execution_receipt(attempt_id="missing", receipt=receipt)

    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    with pytest.raises(ValueError, match="unknown send attempt"):
        s.record_execution_receipt(attempt_id="attempt-2", receipt=receipt)


def test_execution_receipt_cannot_predate_attempt(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:30Z"
    )
    early = make_receipt(
        intent,
        outcome="FAILED",
        executed_at="2026-09-21T11:00:20.000000Z",
    )
    with pytest.raises(ValueError, match="predates send attempt"):
        s.record_execution_receipt(attempt_id="attempt-1", receipt=early)


def test_direct_sql_second_successful_submission_is_blocked(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    first = make_receipt(intent, outcome="SUBMITTED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=first)

    conn = sqlite3.connect(s.path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """INSERT INTO carrier_execution_attempts
           (buyer_id,business_unit,attempt_id,execution_key,intent_hash,started_at,attempt_hash)
           VALUES(?,?,?,?,?,?,?)""",
        (
            "buyer","unit","attempt-direct",intent.execution_key,intent.intent_hash,
            "2026-09-21T11:02:00.000000Z","9"*64,
        ),
    )
    second = make_receipt(
        intent,
        outcome="SUBMITTED",
        executed_at="2026-09-21T11:03:00.000000Z",
        external_reference_hash="7"*64,
        evidence_source_hash="8"*64,
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO carrier_execution_receipts
               (buyer_id,business_unit,receipt_hash,execution_key,attempt_id,intent_hash,
                outcome,action_submitted,delivery_confirmed,executed_at,receipt_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "buyer","unit",second.receipt_hash,intent.execution_key,"attempt-direct",
                intent.intent_hash,second.outcome,1,0,second.executed_at,
                CarrierActionExecutionStore._json(asdict(second)),
            ),
        )
    conn.rollback()
    conn.close()


@pytest.mark.parametrize(
    "table",
    [
        "carrier_execution_intents",
        "carrier_execution_attempts",
        "carrier_execution_receipts",
        "carrier_delivery_receipts",
    ],
)
def test_proof_tables_are_immutable(tmp_path, table):
    s = store(tmp_path)
    intent = make_intent()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    submitted = make_receipt(intent, outcome="SUBMITTED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=submitted)
    s.record_delivery_receipt(make_delivery(submitted))

    conn = sqlite3.connect(s.path)
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        conn.execute(f"DELETE FROM {table}")
    conn.close()


def test_concurrent_workers_get_one_send_slot(tmp_path):
    intent = make_intent()
    s1 = store(tmp_path)
    s2 = store(tmp_path)

    def reserve(args):
        s, attempt = args
        return s.reserve_send_attempt(
            intent,
            attempt_id=attempt,
            started_at="2026-09-21T11:00:10Z",
        ).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(reserve, [(s1, "attempt-1"), (s2, "attempt-2")]))
    assert sorted(statuses) == sorted([RESERVED, IN_FLIGHT])


def test_snapshot_changes_at_each_material_state_transition(tmp_path):
    s = store(tmp_path)
    intent = make_intent()
    initial = s.snapshot_hash()
    s.reserve_send_attempt(
        intent, attempt_id="attempt-1", started_at="2026-09-21T11:00:10Z"
    )
    reserved = s.snapshot_hash()
    submitted = make_receipt(intent, outcome="SUBMITTED")
    s.record_execution_receipt(attempt_id="attempt-1", receipt=submitted)
    sent = s.snapshot_hash()
    delivery = make_delivery(submitted)
    s.record_delivery_receipt(delivery)
    delivered = s.snapshot_hash()
    assert len({initial, reserved, sent, delivered}) == 4
