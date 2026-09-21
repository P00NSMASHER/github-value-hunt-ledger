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
    assert out["audit_result_bundle_entry_count"] == 12
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
    assert out["review_route"] == "MIXED_REVIEW_AND_REMEDIATION"
    assert len(out["review_routing_hash"]) == 64
    assert out["buyer_review_case_count"] == 2
    assert out["evidence_remediation_case_count"] == 1
    assert out["rerun_required"] is True
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
