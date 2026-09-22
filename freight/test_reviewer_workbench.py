"""Real pipeline fixtures; no customer data or actual reviewer decisions."""
import base64
import hashlib
import json
import re
from dataclasses import replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import verify_buyer_review_batch
from freight.reviewer_workbench import (
    MAX_DECISION_BYTES, MAX_DECISIONS, import_reviewer_decisions,
    render_reviewer_workbench,
)

IH = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RH = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def artifacts(*, billed=12500, verified=True, extra=True, invoice_id="INV-1"):
    rows = f"{invoice_id},S1,C,K,USD,X1,DETENTION,2026-09-10,1,{billed}\n"
    if extra:
        rows += "INV-2,S2,C,K,EUR,X2,UNKNOWN,2026-09-10,1,5000\n"
    result = run_audit_workflow(
        invoice_filename="synthetic.csv", invoice_data=(IH + rows).encode(),
        buyer_id="test-buyer", business_unit="test-unit", selection_rule="synthetic test",
        rule_inputs=(RuleCSVInput(
            filename="synthetic-rules.csv", data=(RH + "DETENTION,FIXED,2026-09-01,,10000,\n").encode(),
            customer_id="C", carrier_id="K", currency="USD", authority_document_id="Synthetic rate",
            source_document_sha256="a" * 64, verified_controlling_authority=verified,
        ),),
    )
    assert result.state != "BLOCKED", result.error_message
    return result.artifacts


def context(a):
    return dict(review_packet=a.review_packet, review_routing=a.review_routing,
                truth=a.factory.truth)


def envelope(a, *, decision=True):
    return {
        "schema_version": 1,
        "review_packet_hash": a.review_packet.packet_hash,
        "review_routing_hash": a.review_routing.routing_hash,
        "truth_hash": a.factory.truth.truth_hash,
        "decisions": [{
            "case_hash": a.review_routing.buyer_review_case_hashes[0],
            "disposition": "CONFIRMED", "reviewer_minutes": 3,
            "reviewed_at": "2026-09-21T09:00:00-04:00",
        }] if decision else [],
    }


def load(a, obj):
    return import_reviewer_decisions(data=json.dumps(obj).encode(), reviewer_role="Test Buyer Controller", **context(a))


def test_deterministic_offline_workbench_with_exact_money_strings():
    a = artifacts(billed=2**63-1)
    html = render_reviewer_workbench(**context(a))
    assert html == render_reviewer_workbench(**context(a))
    payload = json.loads(re.search(r'id="audit-data">(.*?)</script>', html, re.S).group(1))
    assert payload["cases"][0]["billed_cents"] == str(2**63-1)
    assert payload["cases"][0]["buyer_review_ready"] is True
    assert payload["cases"][1]["buyer_review_ready"] is False
    assert payload["cases"][1]["expected_cents"] is None
    assert "Offline" in html and "Draft decisions" in html
    assert "localStorage" not in html and "fetch(" not in html
    assert "<script src=" not in html and "<link " not in html
    assert "connect-src 'none'" in html and "form-action 'none'" in html
    assert "WORKBENCH_VALIDATION_ONLY" not in html


def test_script_and_style_hashes_match_exact_csp_allowlist():
    html = render_reviewer_workbench(**context(artifacts()))
    for pattern in (r"<style>(.*?)</style>", r'<script id="workbench-code">(.*?)</script>'):
        content = re.search(pattern, html, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()
        assert "'sha256-" + digest + "'" in html
    assert "unsafe-inline" not in html and "unsafe-eval" not in html


def test_untrusted_evidence_cannot_close_json_script_element():
    # Synthetic marker only: verify output encoding, not exploit a target.
    a = artifacts(invoice_id="<review-marker>")
    html = render_reviewer_workbench(**context(a))
    assert "<review-marker>" not in html
    assert "\\u003creview-marker\\u003e" in html
    assert "innerHTML" not in html


def test_import_round_trip_uses_existing_bound_buyer_review_workflow():
    a = artifacts()
    result = load(a, envelope(a))
    assert result.confirmed_count == 1
    assert result.state == "COMPLETE"  # only eligible buyer cases, not remediation
    assert result.reviewer_role == "Test Buyer Controller"
    assert result.finding_reviews[0].review_hash
    assert result.finding_reviews[0].reviewed_at == "2026-09-21T13:00:00.000000Z"
    verify_buyer_review_batch(batch=result, **context(a))


def test_empty_decisions_preserve_pending_cases():
    a = artifacts()
    result = load(a, envelope(a, decision=False))
    assert result.state == "PARTIAL"
    assert result.confirmed_count == 0 and len(result.pending_case_hashes) == 1


@pytest.mark.parametrize("disposition", ["CONFIRMED", "FALSE_POSITIVE", "UNRESOLVED"])
def test_explicit_decisions_only(disposition):
    a = artifacts()
    obj = envelope(a); obj["decisions"][0]["disposition"] = disposition
    assert load(a, obj).records[0].disposition == disposition


@pytest.mark.parametrize("field", ["review_packet_hash", "review_routing_hash", "truth_hash"])
def test_stale_context_rejected(field):
    a = artifacts(); obj = envelope(a); obj[field] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        load(a, obj)


def test_changed_audit_cannot_consume_old_decision_export():
    old, current = artifacts(), artifacts(billed=12501)
    with pytest.raises(ValueError, match="stale"):
        load(current, envelope(old))


def test_remediation_case_cannot_be_promoted_by_export_edit():
    a = artifacts(); obj = envelope(a)
    obj["decisions"][0]["case_hash"] = a.review_routing.remediation_case_hashes[0]
    with pytest.raises(ValueError, match="remediation"):
        load(a, obj)


@pytest.mark.parametrize("bad", [True, -1, 1.5, "3", None])
def test_minutes_require_non_negative_integer(bad):
    a = artifacts(); obj = envelope(a); obj["decisions"][0]["reviewer_minutes"] = bad
    with pytest.raises(ValueError):
        load(a, obj)


@pytest.mark.parametrize("bad", ["2026-09-21T09:00:00", "not-a-time", ""])
def test_review_timestamp_requires_timezone(bad):
    a = artifacts(); obj = envelope(a); obj["decisions"][0]["reviewed_at"] = bad
    with pytest.raises(ValueError):
        load(a, obj)


def test_duplicate_decisions_rejected():
    a = artifacts(); obj = envelope(a); obj["decisions"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        load(a, obj)


@pytest.mark.parametrize("mutation", ["root-extra", "row-extra", "missing", "boolean-version", "unknown-decision"])
def test_strict_schema_rejects_self_asserted_identity_and_bad_fields(mutation):
    a = artifacts(); obj = envelope(a)
    if mutation == "root-extra": obj["reviewer_role"] = "Self-asserted controller"
    if mutation == "row-extra": obj["decisions"][0]["approved"] = True
    if mutation == "missing": del obj["truth_hash"]
    if mutation == "boolean-version": obj["schema_version"] = True
    if mutation == "unknown-decision": obj["decisions"][0]["disposition"] = "AUTO_APPROVE"
    with pytest.raises(ValueError):
        load(a, obj)


@pytest.mark.parametrize("raw", [b'{"schema_version":1,"schema_version":1}', b'{"value":NaN}', b'\xff', b'[[['])
def test_ambiguous_or_invalid_json_rejected(raw):
    a = artifacts()
    with pytest.raises(ValueError):
        import_reviewer_decisions(data=raw, reviewer_role="Test", **context(a))


def test_decision_file_and_row_limits():
    a = artifacts()
    with pytest.raises(ValueError, match="size limit"):
        import_reviewer_decisions(data=b" "*(MAX_DECISION_BYTES+1), reviewer_role="Test", **context(a))
    obj = envelope(a); obj["decisions"] = [{}] * (MAX_DECISIONS+1)
    with pytest.raises(ValueError, match="row limit"):
        load(a, obj)


def test_clean_workbench_has_no_eligible_decisions():
    a = artifacts(billed=9000, extra=False)
    html = render_reviewer_workbench(**context(a))
    payload = json.loads(re.search(r'id="audit-data">(.*?)</script>', html, re.S).group(1))
    assert payload["cases"] == []
    assert payload["buyer_review_case_count"] == 0
    assert load(a, envelope(a, decision=False)).state == "NO_BUYER_REVIEW_READY"


def test_renderer_rejects_changed_routing_proof():
    a = artifacts(); ctx = context(a)
    ctx["review_routing"] = replace(a.review_routing, routing_hash="0" * 64)
    with pytest.raises(ValueError):
        render_reviewer_workbench(**ctx)


def test_all_three_decision_options_are_present_and_none_is_preselected():
    html = render_reviewer_workbench(**context(artifacts()))
    for value in ("", "CONFIRMED", "FALSE_POSITIVE", "UNRESOLVED"):
        assert f'<option value="{value}">' in html
    assert '<option value="CONFIRMED" selected' not in html
