import json
from pathlib import Path

import pytest

from freight.recovery_evidence_pack import build_pack, render_markdown


FIXTURE = Path("freight/fixtures/recovery_evidence_pack_synthetic.json")


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None, [], {}])
def test_pack_rejects_non_boolean_synthetic_classification(value):
    data = payload()
    data["synthetic"] = value
    with pytest.raises(ValueError, match="synthetic must be an explicit boolean"):
        build_pack(data)


def test_pack_requires_synthetic_classification_to_be_present():
    data = payload()
    data.pop("synthetic")
    with pytest.raises(ValueError, match="synthetic must be an explicit boolean"):
        build_pack(data)


def test_pack_keeps_money_states_and_attribution_separate():
    pack = build_pack(payload())
    totals = pack["totals"]
    assert totals["candidate_difference_cents"] == 28500
    assert totals["validated_difference_cents"] == 19500
    assert totals["observed_net_settlement_cents"] == 18500
    assert totals["net_realized_cents"] == 18500
    assert totals["fee_eligible_realized_cents"] == 18500
    assert totals["suppressed_count"] == 2
    assert pack["findings"][2]["attribution_state"] == "SUPPRESSED"
    assert pack["findings"][2]["fee_eligible_realized_cents"] == 0
    assert pack["findings"][3]["reviewer_disposition"] == "REVIEW"
    assert pack["claim_boundary"]["synthetic_classification_is_explicit_boolean"] is True
    assert pack["claim_boundary"]["realized_requires_settled_claim_and_reference"] is True
    assert pack["claim_boundary"]["realized_cannot_exceed_candidate_difference"] is True
    assert pack["claim_boundary"]["positive_settlement_reference_is_unique"] is True
    assert pack["claim_boundary"]["positive_settlement_reference_bound_to_evidence"] is True
    assert pack["claim_boundary"]["economic_opportunity_identity_is_unique"] is True
    assert pack["claim_boundary"]["validated_difference_excludes_suppressed_findings"] is True
    assert pack["claim_boundary"]["validated_supported_findings_require_evidence"] is True
    assert pack["claim_boundary"]["validated_supported_findings_bind_authority_evidence"] is True
    assert pack["claim_boundary"]["validated_supported_authority_not_after_invoice"] is True
    assert pack["claim_boundary"]["buyer_visible_realized_excludes_suppressed_findings"] is True


@pytest.mark.parametrize(
    "suppression_flag",
    ("incumbent_known", "automatic_credit", "preexisting_claim", "duplicate_opportunity"),
)
def test_validated_difference_excludes_suppressed_findings(suppression_flag):
    data = payload()
    data["findings"][0][suppression_flag] = True
    pack = build_pack(data)
    assert pack["findings"][0]["attribution_state"] == "SUPPRESSED"
    assert pack["totals"]["validated_difference_cents"] == 7000


def test_pack_subtracts_reversal_from_realized_value():
    pack = build_pack(payload())
    finding = pack["findings"][1]
    assert finding["settled_credit_cents"] == 7000
    assert finding["reversal_cents"] == 1000
    assert finding["net_realized_cents"] == 6000


def test_pack_accepts_full_reversal_as_zero_realized_value():
    data = payload()
    row = data["findings"][1]
    row["reversal_cents"] = row["settled_credit_cents"]
    pack = build_pack(data)
    assert pack["findings"][1]["net_realized_cents"] == 0


def test_pack_rejects_reversal_above_settled_credit():
    data = payload()
    row = data["findings"][1]
    row["reversal_cents"] = row["settled_credit_cents"] + 1
    with pytest.raises(ValueError, match="reversal_cents cannot exceed settled_credit_cents"):
        build_pack(data)


@pytest.mark.parametrize("claim_status", ["NOT_SUBMITTED", "SUBMITTED", "PENDING", "DENIED"])
def test_pack_rejects_positive_credit_without_settled_claim_status(claim_status):
    data = payload()
    data["findings"][0]["claim_status"] = claim_status
    with pytest.raises(
        ValueError,
        match="positive settled_credit_cents requires APPROVED or CLOSED claim status",
    ):
        build_pack(data)


def test_pack_rejects_positive_credit_without_settlement_reference():
    data = payload()
    data["findings"][0]["settlement_reference"] = ""
    with pytest.raises(
        ValueError,
        match="positive settled_credit_cents requires settlement_reference",
    ):
        build_pack(data)


def test_pack_rejects_positive_credit_when_settlement_reference_is_not_evidence_bound():
    data = payload()
    row = data["findings"][0]
    row["supporting_evidence"].remove(row["settlement_reference"])
    with pytest.raises(
        ValueError,
        match="positive settled_credit_cents requires settlement_reference in supporting_evidence",
    ):
        build_pack(data)


def test_pack_rejects_settled_credit_above_candidate_difference():
    data = payload()
    row = data["findings"][0]
    row["settled_credit_cents"] = row["billed_cents"] - row["expected_cents"] + 1
    with pytest.raises(
        ValueError,
        match="settled_credit_cents cannot exceed candidate difference",
    ):
        build_pack(data)


def test_pack_rejects_duplicate_positive_settlement_reference():
    data = payload()
    duplicate_reference = data["findings"][0]["settlement_reference"]
    data["findings"][1]["settlement_reference"] = duplicate_reference
    data["findings"][1]["supporting_evidence"].append(duplicate_reference)
    with pytest.raises(
        ValueError,
        match="positive settlement_reference must be unique across findings",
    ):
        build_pack(data)


def test_validated_supported_finding_requires_supporting_evidence():
    data = payload()
    data["findings"][0]["supporting_evidence"] = []
    with pytest.raises(
        ValueError,
        match="validated supported finding requires supporting evidence",
    ):
        build_pack(data)


def test_validated_supported_finding_requires_named_authority_evidence():
    data = payload()
    row = data["findings"][0]
    row["supporting_evidence"] = [
        reference
        for reference in row["supporting_evidence"]
        if reference != row["authority_reference"]
    ]
    with pytest.raises(
        ValueError,
        match="validated supported finding requires authority_reference in supporting_evidence",
    ):
        build_pack(data)


def test_unresolved_finding_can_enter_remediation_without_supporting_evidence():
    data = payload()
    data["findings"][3]["supporting_evidence"] = []
    pack = build_pack(data)
    assert pack["findings"][3]["reviewer_disposition"] == "REVIEW"
    assert pack["findings"][3]["confidence"] == "INSUFFICIENT"
    assert pack["findings"][3]["attribution_state"] == "SUPPRESSED"


def test_validated_supported_finding_rejects_future_authority():
    data = payload()
    data["findings"][0]["authority_effective_date"] = "2026-02-13"
    with pytest.raises(
        ValueError,
        match="validated supported finding authority cannot postdate invoice",
    ):
        build_pack(data)


def test_authority_effective_on_invoice_date_is_valid():
    data = payload()
    data["findings"][0]["authority_effective_date"] = data["findings"][0]["invoice_date"]
    pack = build_pack(data)
    assert (
        pack["findings"][0]["authority_effective_date"]
        == pack["findings"][0]["invoice_date"]
    )


def test_unresolved_future_authority_can_enter_remediation():
    data = payload()
    row = data["findings"][3]
    row["authority_effective_date"] = "2026-02-21"
    pack = build_pack(data)
    assert pack["findings"][3]["attribution_state"] == "SUPPRESSED"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("invoice_date", "2026-02-30"),
        ("authority_effective_date", "2026-1-1"),
    ),
)
def test_pack_rejects_invalid_or_noncanonical_dates(field, value):
    data = payload()
    data["findings"][0][field] = value
    with pytest.raises(ValueError, match=f"{field} must be a valid YYYY-MM-DD date"):
        build_pack(data)


def test_markdown_is_buyer_legible_and_explicitly_synthetic():
    report = render_markdown(build_pack(payload()))
    assert "SYNTHETIC / FICTIONAL EXAMPLE" in report
    assert "Candidate difference" in report
    assert "Validated attributable difference: **$195.00**" in report
    assert "Fee-eligible realized recovery" in report
    assert "SUPPRESSED" in report
    assert "Controlling rate authority is not proven." in report
    assert "Positive settled credits require an approved or closed claim" in report
    assert "Settled credit cannot exceed the candidate invoice difference" in report
    assert "Each positive settlement reference must appear in supporting evidence" in report
    assert "One positive settlement reference can support only one finding" in report
    assert "One carrier/invoice/shipment/category identity can support only one economic opportunity" in report
    assert "validated supported finding requires at least one supporting-evidence reference" in report
    assert "exact authority reference must appear in supporting evidence" in report
    assert "cannot rely on authority effective after its invoice date" in report


def test_duplicate_finding_ids_fail_closed():
    data = payload()
    data["findings"][1]["finding_id"] = data["findings"][0]["finding_id"]
    with pytest.raises(ValueError, match="finding_id must be unique"):
        build_pack(data)


def test_duplicate_economic_opportunity_fails_closed():
    data = payload()
    original = data["findings"][0]
    duplicate = dict(original)
    duplicate["finding_id"] = "FR-DUPLICATE"
    duplicate["settlement_reference"] = "CREDIT-DUPLICATE"
    duplicate["supporting_evidence"] = [
        *original["supporting_evidence"],
        duplicate["settlement_reference"],
    ]
    data["findings"].append(duplicate)
    with pytest.raises(
        ValueError,
        match="must identify one economic opportunity",
    ):
        build_pack(data)


def test_same_invoice_can_hold_distinct_finding_categories():
    data = payload()
    original = data["findings"][0]
    separate_charge = dict(original)
    separate_charge["finding_id"] = "FR-ACCESSORIAL"
    separate_charge["finding_category"] = "Unsupported detention charge"
    separate_charge["settlement_reference"] = "CREDIT-ACCESSORIAL"
    separate_charge["supporting_evidence"] = [
        *original["supporting_evidence"],
        separate_charge["settlement_reference"],
    ]
    data["findings"].append(separate_charge)
    pack = build_pack(data)
    assert pack["totals"]["findings_count"] == len(data["findings"])


def test_unsupported_money_cannot_become_fee_eligible():
    data = payload()
    row = data["findings"][0]
    row["confidence"] = "INSUFFICIENT"
    pack = build_pack(data)
    assert pack["findings"][0]["attribution_state"] == "SUPPRESSED"
    assert pack["findings"][0]["fee_eligible_realized_cents"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("reviewer_disposition", "REJECTED"),
        ("confidence", "INSUFFICIENT"),
        ("incumbent_known", True),
        ("automatic_credit", True),
        ("preexisting_claim", True),
        ("duplicate_opportunity", True),
    ),
)
def test_suppressed_money_cannot_inflate_buyer_visible_realized_recovery(field, value):
    data = payload()
    data["findings"][0][field] = value
    pack = build_pack(data)
    assert pack["findings"][0]["net_realized_cents"] == 12500
    assert pack["findings"][0]["attribution_state"] == "SUPPRESSED"
    assert pack["totals"]["observed_net_settlement_cents"] == 18500
    assert pack["totals"]["net_realized_cents"] == 6000
    report = render_markdown(pack)
    assert "Observed net settlement across all findings: **$185.00**" in report
    assert "Attributable net realized recovery: **$60.00**" in report
