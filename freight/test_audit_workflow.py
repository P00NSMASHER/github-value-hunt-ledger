import pytest

from freight.audit_workflow import (
    AuditWorkflowStage,
    AuditWorkflowState,
    RuleCSVInput,
    render_workflow_summary,
    run_audit_workflow,
)
from freight.review_routing import (
    BUYER_REVIEW_READY,
    EVIDENCE_REMEDIATION_REQUIRED,
    MIXED_REVIEW_AND_REMEDIATION,
    NO_REVIEW,
)


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def rule_input(rows: str, *, verified=True, source="a"):
    return RuleCSVInput(
        filename="rules.csv",
        data=(RULE_HEADER + rows).encode(),
        customer_id="C",
        carrier_id="K",
        currency="USD",
        authority_document_id="rate",
        source_document_sha256=source * 64,
        verified_controlling_authority=verified,
    )


def run(rows: str, *, rules=()):
    return run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER + rows).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="September accepted charges",
        rule_inputs=rules,
    )


def test_single_call_returns_review_required_with_complete_artifacts():
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n"
        "I2,S2,C,K,USD,X2,MISC,2026-09-10,1,15000\n",
        rules=(
            rule_input("DETENTION,FIXED,2026-09-01,,10000,\n", verified=True),
            rule_input("MISC,FIXED,2026-09-01,,10000,\n", verified=False, source="b"),
        ),
    )
    assert result.state == AuditWorkflowState.REVIEW_REQUIRED.value
    assert result.stage == AuditWorkflowStage.COMPLETE.value
    assert result.error_code is None
    assert result.error_message is None
    assert result.summary is not None
    assert result.artifacts is not None
    assert result.summary.rule_count == 2
    assert result.summary.validated_finding_count == 1
    assert result.summary.review_finding_count == 1
    assert result.summary.review_case_count == 2
    assert result.summary.review_route == MIXED_REVIEW_AND_REMEDIATION
    assert result.summary.buyer_review_case_count == 1
    assert result.summary.evidence_remediation_case_count == 1
    assert result.summary.rerun_required is True
    assert len(result.summary.review_routing_hash) == 64
    assert len(result.summary.remediation_plan_hash) == 64
    assert result.artifacts.review_routing.routing_hash == result.summary.review_routing_hash
    assert result.artifacts.remediation_plan.plan_hash == result.summary.remediation_plan_hash
    assert result.artifacts.remediation_plan.remediation_case_count == 1
    assert result.summary.validated_discrepancy_cents == 2500
    assert result.summary.review_discrepancy_cents == 5000
    assert len(result.summary.run_hash) == 64
    assert result.summary.run_hash == result.artifacts.manifest.run_hash


def test_clean_run_is_distinct_from_review_required():
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,9000\n",
        rules=(rule_input("DETENTION,FIXED,2026-09-01,,10000,\n"),),
    )
    assert result.state == AuditWorkflowState.CLEAN.value
    assert result.summary is not None
    assert result.summary.clear_count == 1
    assert result.summary.review_case_count == 0
    assert result.summary.review_route == NO_REVIEW
    assert result.summary.buyer_review_case_count == 0
    assert result.summary.evidence_remediation_case_count == 0
    assert result.summary.rerun_required is False
    assert result.artifacts.remediation_plan.items == ()
    assert result.summary.validated_discrepancy_cents == 0


def test_no_rules_is_review_required_not_pipeline_failure():
    result = run("I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n")
    assert result.state == AuditWorkflowState.REVIEW_REQUIRED.value
    assert result.summary is not None
    assert result.summary.rule_count == 0
    assert result.summary.review_case_count == 1
    assert result.summary.review_route == EVIDENCE_REMEDIATION_REQUIRED
    assert result.summary.buyer_review_case_count == 0
    assert result.summary.evidence_remediation_case_count == 1
    assert result.summary.rerun_required is True
    assert result.artifacts.remediation_plan.remediation_case_count == 1
    assert result.artifacts.remediation_plan.items[0].remediation_action == "ADD_RULE_AND_RERUN"
    assert result.summary.unknown_expected_count == 1
    assert result.artifacts is not None
    assert result.artifacts.manifest.rule_hashes == ()
    assert result.artifacts.manifest.rule_adapter_hashes == ()




def test_all_validated_review_cases_route_to_buyer_review_ready():
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n"
        "I2,S2,C,K,USD,X2,MISC,2026-09-10,1,15000\n",
        rules=(
            rule_input("DETENTION,FIXED,2026-09-01,,10000,\n", verified=True),
            rule_input("MISC,FIXED,2026-09-01,,10000,\n", verified=True, source="b"),
        ),
    )
    assert result.state == AuditWorkflowState.REVIEW_REQUIRED.value
    assert result.summary.review_route == BUYER_REVIEW_READY
    assert result.summary.buyer_review_case_count == 2
    assert result.summary.evidence_remediation_case_count == 0
    assert result.summary.rerun_required is False
    assert result.artifacts.remediation_plan.items == ()


def test_malformed_invoice_blocks_at_invoice_ingest_without_partial_artifacts():
    result = run("I1,S1,C,K,USD,X1,DETENTION,09/10/2026,1,12500\n")
    assert result.state == AuditWorkflowState.BLOCKED.value
    assert result.stage == AuditWorkflowStage.INVOICE_INGEST.value
    assert result.error_code == "INVOICE_INGEST_FAILED"
    assert result.summary is None
    assert result.artifacts is None


def test_population_identity_conflict_blocks_at_population_freeze():
    result = run(
        "I1,S1,C1,K,USD,X1,FUEL,2026-09-10,1,100\n"
        "I1,S1,C2,K,USD,X2,DETENTION,2026-09-10,1,200\n"
    )
    assert result.state == AuditWorkflowState.BLOCKED.value
    assert result.stage == AuditWorkflowStage.POPULATION_FREEZE.value
    assert result.error_code == "POPULATION_FREEZE_FAILED"
    assert "identity conflict" in result.error_message


def test_malformed_rule_blocks_at_rule_ingest_with_batch_index():
    bad = RuleCSVInput(
        filename="bad.csv",
        data=(RULE_HEADER + "DETENTION,FIXED,2026-09-01,,,\n").encode(),
        customer_id="C",
        carrier_id="K",
        currency="USD",
        authority_document_id="rate",
        source_document_sha256="a" * 64,
        verified_controlling_authority=True,
    )
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n",
        rules=(bad,),
    )
    assert result.state == AuditWorkflowState.BLOCKED.value
    assert result.stage == AuditWorkflowStage.RULE_INGEST.value
    assert result.error_code == "RULE_INGEST_FAILED"
    assert result.error_message.startswith("rule batch 1:")


def test_same_inputs_produce_same_run_hash_and_summary():
    rules = (rule_input("DETENTION,FIXED,2026-09-01,,10000,\n"),)
    a = run("I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n", rules=rules)
    b = run("I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n", rules=rules)
    assert a.summary == b.summary
    assert a.artifacts.manifest == b.artifacts.manifest


def test_summary_renderer_separates_discrepancy_from_realized_savings():
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n",
        rules=(rule_input("DETENTION,FIXED,2026-09-01,,10000,\n"),),
    )
    text = render_workflow_summary(result)
    assert "Audit run:" in text
    assert "Validated discrepancy" in text
    assert "Review route:" in text
    assert "Buyer-review-ready cases:" in text
    assert "Evidence-remediation cases:" in text
    assert "Remediation plan hash:" in text
    assert "not realized savings" in text


def test_blocked_summary_states_no_manifest_was_issued():
    result = run("broken,row\n")
    text = render_workflow_summary(result)
    assert "BLOCKED" in text
    assert "No audit-run manifest was issued" in text
