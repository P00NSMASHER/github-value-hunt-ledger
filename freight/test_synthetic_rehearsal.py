from freight.synthetic_rehearsal import run_rehearsal


def test_full_synthetic_rehearsal_matches_persistent_settlement_store():
    out = run_rehearsal()
    assert out["synthetic"] is True
    assert out["buyer_id"] == "buyer-synthetic"
    assert out["business_unit"] == "bu-synthetic"
    assert out["readiness_status"] == "READY"
    assert out["deal_route"] == "BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST"
    assert out["pilot_gross_margin"] == 0.60
    assert out["incumbent_submission_hash"]
    assert out["audit_workflow_state"] == "REVIEW_REQUIRED"
    assert "Audit run:" in out["audit_workflow_summary"]
    assert "not realized savings" in out["audit_workflow_summary"]
    assert out["audit_run_hash"]
    assert len(out["audit_result_bundle_sha256"]) == 64
    assert len(out["audit_result_bundle_manifest_sha256"]) == 64
    assert out["audit_result_bundle_entry_count"] == 14
    assert out["population_builder_hash"]
    assert out["population_invoice_count"] == 3
    assert out["population_charge_count"] == 3
    assert out["invoice_csv_adapter_hash"]
    assert out["invoice_csv_file_sha256"]
    assert out["review_queue_hash"]
    assert out["review_packet_hash"]
    assert out["review_route"] == "MIXED_REVIEW_AND_REMEDIATION"
    assert len(out["review_routing_hash"]) == 64
    assert out["buyer_review_case_count"] == 2
    assert out["evidence_remediation_case_count"] == 1
    assert out["rerun_required"] is True
    assert len(out["remediation_plan_hash"]) == 64
    assert out["remediation_plan_item_count"] == 1
    assert out["buyer_review_state"] == "COMPLETE"
    assert len(out["buyer_review_batch_hash"]) == 64
    assert out["buyer_review_submitted_decision_count"] == 2
    assert out["buyer_review_confirmed_count"] == 2
    assert out["buyer_review_pending_case_count"] == 0
    assert len(out["recovery_claim_batch_hash"]) == 64
    assert out["recovery_claim_count"] == 2
    assert out["recovery_claim_fee_disqualified_count"] == 1
    assert len(out["recovery_claim_persistence_receipt_hash"]) == 64
    assert out["recovery_claim_persisted_count"] == 2
    assert out["recovery_claim_already_present_count"] == 0
    assert len(out["carrier_action_proposal_batch_hash"]) == 64
    assert out["carrier_action_proposal_count"] == 1
    assert len(out["carrier_action_proposal_hash"]) == 64
    assert out["carrier_action_target_customer_id"] == "cust"
    assert len(out["carrier_action_payload_hash"]) == 64
    assert "Freight credit review request" in out["carrier_action_payload_subject"]
    assert len(out["external_action_authorization_hash"]) == 64
    assert out["external_action_authorized_cents"] == 5000
    assert out["external_action_automatic_execution_authorized"] is False
    assert len(out["carrier_action_execution_key"]) == 64
    assert len(out["carrier_action_execution_intent_hash"]) == 64
    assert len(out["carrier_action_execution_receipt_hash"]) == 64
    assert out["carrier_action_execution_outcome"] == "SUBMITTED"
    assert out["carrier_action_submitted"] is True
    assert out["carrier_action_delivery_confirmed"] is False
    assert len(out["carrier_action_delivery_receipt_hash"]) == 64
    assert out["carrier_action_async_delivery_confirmed"] is True
    assert out["carrier_execution_store_reservation_status"] == "RESERVED"
    assert out["carrier_execution_store_receipt_status"] == "RECORDED"
    assert out["carrier_execution_store_delivery_status"] == "DELIVERY_RECORDED"
    assert out["carrier_execution_store_submitted_state"] == "SUBMITTED"
    assert out["carrier_execution_store_final_state"] == "DELIVERED"
    assert len({
        out["carrier_execution_store_initial_snapshot"],
        out["carrier_execution_store_reserved_snapshot"],
        out["carrier_execution_store_final_snapshot"],
    }) == 3
    assert out["carrier_action_delivered_at"] == "2026-09-21T08:05:00.000000Z"
    assert len(out["settlement_csv_adapter_hash"]) == 64
    assert len(out["settlement_csv_file_sha256"]) == 64
    assert out["settlement_event_count"] == 2
    assert out["settlement_lifecycle_state"] == "REVIEW_REQUIRED"
    assert len(out["settlement_lifecycle_state_hash"]) == 64
    assert len(out["settlement_lifecycle_execution_hash"]) == 64
    assert len(out["settlement_review_case_hash"]) == 64
    assert out["settlement_review_candidate_count"] == 1
    assert len(out["settlement_review_hash"]) == 64
    assert len(out["settlement_review_receipt_hash"]) == 64
    assert out["settlement_review_allocation_id"].startswith("review:")
    assert out["settlement_review_allocation_status"] == "ALLOCATED"
    assert len(out["counter_csv_adapter_hash"]) == 64
    assert len(out["counter_csv_file_sha256"]) == 64
    assert out["counter_event_count"] == 1
    assert out["counter_lifecycle_state"] == "COMPLETE"
    assert len(out["counter_lifecycle_state_hash"]) == 64
    assert len(out["counter_lifecycle_execution_hash"]) == 64
    assert "Reviewer Work Packet" in out["review_packet_markdown"]
    assert "not realized savings" in out["review_packet_markdown"]
    assert out["verified_rule_adapter_hash"]
    assert out["review_rule_adapter_hash"]
    assert [item["charge_id"] for item in out["review_queue"]] == ["charge-1", "charge-2", "charge-3"]
    assert [item["priority_class"] for item in out["review_queue"]] == [
        "VALIDATED_MONEY", "VALIDATED_MONEY", "REVIEW_MONEY",
    ]
    assert all(out["buyer_review_hashes"])
    assert out["metrics"]["reviewed_discrepancy_cents"] == 10000
    assert out["metrics"]["validated_finding_cents"] == 5000
    assert out["metrics"]["challenger_only_validated_cents"] == 2500
    assert out["metrics"]["realized_cents"] == 4000
    assert out["metrics"]["fee_eligible_realized_cents"] == 1500
    assert out["persistent_store"]["realized_cents"] == 4000
    assert out["persistent_store"]["fee_eligible_cents"] == 1500
    assert out["commercial_value_claimed"] is False


def test_rehearsal_report_explicitly_separates_scope_and_discrepancy_from_savings():
    report = run_rehearsal()["report_markdown"]
    assert "Buyer scope: **buyer-synthetic**" in report
    assert "Business unit: **bu-synthetic**" in report
    assert "Reviewed discrepancy" in report
    assert "Discrepancy and validated dollars are not realized savings" in report
    assert "Persistent settlement provenance" in report
    assert "net of applied returns/reversals" in report


def test_rehearsal_return_changes_provenance_and_blocks_old_report_reuse():
    out = run_rehearsal()
    proof = out["persistent_reporting"]
    assert proof["pre_return_realized_cents"] == 4500
    assert proof["pre_return_fee_eligible_cents"] == 2000
    assert proof["return_cents"] == 500
    assert proof["stale_report_rejected"] is True
    assert proof["settlement_snapshot_hash"] != proof["pre_return_snapshot_hash"]
    assert proof["report_hash"] != proof["pre_return_report_hash"]
    assert proof["settlement_snapshot_hash"] in out["report_markdown"]


def test_persistent_rehearsal_report_is_deterministic():
    assert run_rehearsal() == run_rehearsal()
