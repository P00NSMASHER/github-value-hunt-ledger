import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.remediation_plan import (
    _money,
    ADD_RULE_AND_RERUN,
    VERIFY_AUTHORITY_AND_RERUN,
    build_remediation_plan,
    render_remediation_plan_markdown,
)


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def workflow(*, include_unverified=True, include_missing=True, clean=False):
    invoice_rows = (
        f"I1,S1,C,K,USD,X1,A,2026-09-10,1,{9000 if clean else 12000}\n"
        f"I2,S2,C,K,USD,X2,B,2026-09-10,1,{9000 if clean else 15000}\n"
        "I3,S3,C,K,USD,X3,C,2026-09-10,1,9000\n"
    )
    rules = [
        RuleCSVInput(
            filename="a.csv",
            data=(RULE_HEADER + "A,FIXED,2026-09-01,,10000,\n").encode(),
            customer_id="C", carrier_id="K", currency="USD",
            authority_document_id="doc-a", source_document_sha256="a"*64,
            verified_controlling_authority=True,
        ),
        RuleCSVInput(
            filename="b.csv",
            data=(RULE_HEADER + "B,FIXED,2026-09-01,,10000,\n").encode(),
            customer_id="C", carrier_id="K", currency="USD",
            authority_document_id="doc-b", source_document_sha256="b"*64,
            verified_controlling_authority=not include_unverified,
        ),
    ]
    if not include_missing:
        rules.append(RuleCSVInput(
            filename="c.csv",
            data=(RULE_HEADER + "C,FIXED,2026-09-01,,10000,\n").encode(),
            customer_id="C", carrier_id="K", currency="USD",
            authority_document_id="doc-c", source_document_sha256="c"*64,
            verified_controlling_authority=True,
        ))
    return run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER + invoice_rows).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="scope",
        rule_inputs=tuple(rules),
    )


def test_mixed_route_produces_exact_remediation_actions():
    result = workflow()
    plan = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    assert plan.review_route == "MIXED_REVIEW_AND_REMEDIATION"
    assert plan.buyer_review_case_count == 1
    assert plan.remediation_case_count == 2
    assert plan.rerun_required is True
    assert [item.charge_id for item in plan.items] == ["X2", "X3"]
    assert [item.remediation_action for item in plan.items] == [
        VERIFY_AUTHORITY_AND_RERUN,
        ADD_RULE_AND_RERUN,
    ]
    assert all(item.rerun_required for item in plan.items)
    assert all(len(item.item_hash) == 64 for item in plan.items)
    assert len(plan.plan_hash) == 64


def test_no_remediation_produces_empty_non_rerun_plan():
    result = workflow(include_unverified=False, include_missing=False)
    plan = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    assert plan.review_route == "BUYER_REVIEW_READY"
    assert plan.remediation_case_count == 0
    assert plan.rerun_required is False
    assert plan.items == ()


def test_clean_run_produces_no_review_no_remediation_plan():
    result = workflow(include_unverified=False, include_missing=False, clean=True)
    plan = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    assert plan.review_route == "NO_REVIEW"
    assert plan.buyer_review_case_count == 0
    assert plan.remediation_case_count == 0
    assert plan.items == ()


def test_plan_rejects_routing_from_different_packet():
    a = workflow()
    b = workflow(include_unverified=False, include_missing=False)
    with pytest.raises(ValueError, match="does not match"):
        build_remediation_plan(
            a.artifacts.review_packet,
            b.artifacts.review_routing,
        )


def test_plan_is_deterministic():
    result = workflow()
    a = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    b = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    assert a == b


def test_markdown_is_actionable_and_forbids_manual_promotion():
    result = workflow()
    plan = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    text = render_remediation_plan_markdown(plan)
    assert "Evidence Remediation Plan" in text
    assert "VERIFY_AUTHORITY_AND_RERUN" in text
    assert "ADD_RULE_AND_RERUN" in text
    assert "Do not manually promote" in text
    assert "rerun the audit workflow" in text
    assert "not realized savings" in text


def test_remediation_item_is_bound_to_original_case_hash():
    result = workflow()
    plan = build_remediation_plan(
        result.artifacts.review_packet,
        result.artifacts.review_routing,
    )
    routed_hashes = set(result.artifacts.review_routing.remediation_case_hashes)
    assert {item.case_hash for item in plan.items} == routed_hashes


def test_remediation_money_renderer_preserves_full_integer_cent_precision():
    assert _money(2**63 - 1) == "$92,233,720,368,547,758.07"
