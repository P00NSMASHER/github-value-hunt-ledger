import json
from pathlib import Path

from freight.audit_workflow import (
    AuditWorkflowRequest,
    AuditWorkflowStatus,
    RuleSourceInput,
    request_from_trusted_spec,
    run_audit_spec,
    run_audit_workflow,
    write_audit_result_package,
)


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def invoice_bytes(amount=12500, code="DETENTION"):
    return (
        INVOICE_HEADER
        + f"I1,S1,C,K,USD,X1,{code},2026-09-10,1,{amount}\n"
    ).encode()


def rule_source(*, fixed=10000, verified=True, code="DETENTION", doc=b"authority-doc"):
    return RuleSourceInput(
        rule_filename="rules.csv",
        rule_csv=(RULE_HEADER + f"{code},FIXED,2026-09-01,,{fixed},\n").encode(),
        customer_id="C",
        carrier_id="K",
        currency="USD",
        authority_document_id="rate-confirmation",
        authority_document_data=doc,
        verified_controlling_authority=verified,
    )


def request(*, amount=12500, rules=None):
    return AuditWorkflowRequest(
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="September accepted charges",
        invoice_filename="charges.csv",
        invoice_csv=invoice_bytes(amount),
        rule_sources=tuple(rules if rules is not None else (rule_source(),)),
    )


def test_one_call_workflow_produces_review_required_result_and_manifest():
    out = run_audit_workflow(request())
    assert out.status is AuditWorkflowStatus.REVIEW_REQUIRED
    assert out.run_manifest.charge_count == 1
    assert out.run_manifest.invoice_count == 1
    assert out.run_manifest.rule_count == 1
    assert out.factory.validated_count == 1
    assert out.factory.review_count == 0
    assert len(out.review_queue.items) == 1
    assert out.review_packet.cases[0].finding_proof_hash
    assert len(out.run_manifest.run_hash) == 64
    assert len(out.result_hash) == 64


def test_clean_workflow_returns_clean_without_review_cases():
    out = run_audit_workflow(request(amount=9000))
    assert out.status is AuditWorkflowStatus.CLEAN
    assert out.factory.clear_count == 1
    assert out.review_queue.items == ()
    assert out.review_packet.cases == ()
    assert out.run_manifest.review_case_count == 0


def test_missing_authority_evidence_is_a_review_state_not_a_crash():
    out = run_audit_workflow(request(rules=()))
    assert out.status is AuditWorkflowStatus.REVIEW_REQUIRED
    assert out.run_manifest.rule_count == 0
    assert out.run_manifest.rule_adapter_hashes == ()
    assert out.run_manifest.authority_document_hashes == ()
    assert out.review_packet.cases[0].action_hint == "ADD_APPLICABLE_RULE"
    assert out.review_packet.cases[0].expected_cents is None


def test_unverified_authority_remains_review_required():
    out = run_audit_workflow(request(rules=(rule_source(verified=False),)))
    assert out.status is AuditWorkflowStatus.REVIEW_REQUIRED
    assert out.factory.validated_count == 0
    assert out.factory.review_count == 1
    assert out.review_packet.cases[0].action_hint == "VERIFY_CONTROLLING_AUTHORITY"


def test_authority_document_bytes_are_hashed_into_run_provenance():
    a = run_audit_workflow(request(rules=(rule_source(doc=b"one"),)))
    b = run_audit_workflow(request(rules=(rule_source(doc=b"two"),)))
    assert a.rule_batches[0].source_document_sha256 != b.rule_batches[0].source_document_sha256
    assert a.run_manifest.run_hash != b.run_manifest.run_hash
    assert a.result_hash != b.result_hash


def test_result_package_is_deterministic_and_contains_no_raw_source_files(tmp_path):
    out = run_audit_workflow(request())
    package = write_audit_result_package(out, tmp_path / "result")
    names = sorted(p.name for p in (tmp_path / "result").iterdir())
    assert names == [
        "PACKAGE_MANIFEST.json",
        "audit-run-manifest.json",
        "audit-summary.json",
        "review-packet.md",
    ]
    assert len(package["package_hash"]) == 64
    summary = json.loads((tmp_path / "result" / "audit-summary.json").read_text())
    assert summary["status"] == "REVIEW_REQUIRED"
    assert summary["run_hash"] == out.run_manifest.run_hash
    assert "not realized savings" in summary["claim_boundary"]
    assert not (tmp_path / "result" / "charges.csv").exists()


def test_nonempty_result_directory_fails_closed(tmp_path):
    target = tmp_path / "result"
    target.mkdir()
    (target / "existing.txt").write_text("do not overwrite")
    out = run_audit_workflow(request())
    try:
        write_audit_result_package(out, target)
    except ValueError as exc:
        assert "new or empty" in str(exc)
    else:
        raise AssertionError("non-empty destination must fail closed")


def test_trusted_spec_runs_real_files_and_hashes_authority_document(tmp_path):
    (tmp_path / "charges.csv").write_bytes(invoice_bytes())
    (tmp_path / "rules.csv").write_bytes(
        (RULE_HEADER + "DETENTION,FIXED,2026-09-01,,10000,\n").encode()
    )
    (tmp_path / "rate.pdf").write_bytes(b"%PDF-synthetic-authority")
    spec = {
        "buyer_id": "buyer",
        "business_unit": "unit",
        "selection_rule": "September accepted charges",
        "invoice_csv_path": "charges.csv",
        "rule_sources": [
            {
                "rule_csv_path": "rules.csv",
                "customer_id": "C",
                "carrier_id": "K",
                "currency": "USD",
                "authority_document_id": "rate-confirmation",
                "authority_document_path": "rate.pdf",
                "verified_controlling_authority": True,
            }
        ],
    }
    spec_path = tmp_path / "audit.json"
    spec_path.write_text(json.dumps(spec))

    parsed = request_from_trusted_spec(spec_path)
    assert parsed.invoice_filename == "charges.csv"
    assert parsed.rule_sources[0].authority_document_data.startswith(b"%PDF-")

    out = run_audit_spec(spec_path, tmp_path / "out")
    assert out.status is AuditWorkflowStatus.REVIEW_REQUIRED
    assert (tmp_path / "out" / "PACKAGE_MANIFEST.json").exists()


def test_trusted_spec_requires_boolean_authority_verification(tmp_path):
    (tmp_path / "charges.csv").write_bytes(invoice_bytes())
    (tmp_path / "rules.csv").write_bytes(
        (RULE_HEADER + "DETENTION,FIXED,2026-09-01,,10000,\n").encode()
    )
    (tmp_path / "rate.pdf").write_bytes(b"%PDF-doc")
    spec = {
        "buyer_id": "buyer",
        "business_unit": "unit",
        "selection_rule": "period",
        "invoice_csv_path": "charges.csv",
        "rule_sources": [{
            "rule_csv_path": "rules.csv",
            "customer_id": "C",
            "carrier_id": "K",
            "currency": "USD",
            "authority_document_id": "rate",
            "authority_document_path": "rate.pdf",
            "verified_controlling_authority": "true",
        }],
    }
    spec_path = tmp_path / "bad.json"
    spec_path.write_text(json.dumps(spec))
    try:
        request_from_trusted_spec(spec_path)
    except ValueError as exc:
        assert "boolean" in str(exc)
    else:
        raise AssertionError("string truth value must not become authority verification")
