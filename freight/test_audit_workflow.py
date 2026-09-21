import hashlib

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


def rule_input(rows: str, *, verified=True, source="a", currency="USD", source_data=None):
    return RuleCSVInput(
        filename="rules.csv",
        data=(RULE_HEADER + rows).encode(),
        customer_id="C",
        carrier_id="K",
        currency=currency,
        authority_document_id="rate",
        source_document_sha256=(source * 64 if source is not None else None),
        verified_controlling_authority=verified,
        source_document_data=source_data,
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
    assert result.artifacts.review_routing.routing_hash == result.summary.review_routing_hash
    assert result.summary.summary_currency == "USD"
    assert result.summary.validated_discrepancy_cents == 2500
    assert result.summary.review_discrepancy_cents == 5000
    assert [(item.currency, item.validated_discrepancy_cents, item.review_discrepancy_cents)
            for item in result.summary.currency_discrepancies] == [("USD", 2500, 5000)]
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
    assert "not realized savings" in text


def test_blocked_summary_states_no_manifest_was_issued():
    result = run("broken,row\n")
    text = render_workflow_summary(result)
    assert "BLOCKED" in text
    assert "No audit-run manifest was issued" in text


def test_mixed_currency_summary_never_adds_cents_across_currencies():
    usd = rule_input(
        "DETENTION,FIXED,2026-09-01,,10000,\n",
        verified=True,
        source="a",
        currency="USD",
    )
    eur = RuleCSVInput(
        filename="eur-rules.csv",
        data=(RULE_HEADER + "MISC,FIXED,2026-09-01,,7000,\n").encode(),
        customer_id="C",
        carrier_id="K",
        currency="EUR",
        authority_document_id="eur-rate",
        source_document_sha256="b" * 64,
        verified_controlling_authority=True,
    )
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER
                      + "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n"
                      + "I2,S2,C,K,EUR,X2,MISC,2026-09-10,1,10000\n").encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="mixed currencies",
        rule_inputs=(usd, eur),
    )
    assert result.summary is not None
    assert result.summary.summary_currency is None
    assert result.summary.validated_discrepancy_cents is None
    assert result.summary.review_discrepancy_cents is None
    assert [
        (item.currency, item.validated_discrepancy_cents, item.review_discrepancy_cents)
        for item in result.summary.currency_discrepancies
    ] == [("EUR", 3000, 0), ("USD", 2500, 0)]
    text = render_workflow_summary(result)
    assert "EUR 30.00" in text
    assert "USD 25.00" in text
    assert "$55.00" not in text


def test_authority_document_bytes_can_supply_the_provenance_hash():
    doc = b"exact authority document bytes"
    spec = rule_input(
        "DETENTION,FIXED,2026-09-01,,10000,\n",
        source=None,
        source_data=doc,
    )
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n",
        rules=(spec,),
    )
    assert result.state == AuditWorkflowState.REVIEW_REQUIRED.value
    assert result.artifacts is not None
    assert result.artifacts.rule_batches[0].source_document_sha256 == hashlib.sha256(doc).hexdigest()


def test_authority_document_hash_mismatch_blocks_rule_ingest():
    spec = rule_input(
        "DETENTION,FIXED,2026-09-01,,10000,\n",
        source="a",
        source_data=b"different actual document",
    )
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n",
        rules=(spec,),
    )
    assert result.state == AuditWorkflowState.BLOCKED.value
    assert result.stage == AuditWorkflowStage.RULE_INGEST.value
    assert result.error_code == "RULE_INGEST_FAILED"
    assert "does not match source_document_data" in result.error_message


def test_authority_document_requires_hash_or_bytes():
    spec = rule_input(
        "DETENTION,FIXED,2026-09-01,,10000,\n",
        source=None,
        source_data=None,
    )
    result = run(
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n",
        rules=(spec,),
    )
    assert result.state == AuditWorkflowState.BLOCKED.value
    assert result.stage == AuditWorkflowStage.RULE_INGEST.value
    assert "source_document_sha256 or source_document_data is required" in result.error_message
