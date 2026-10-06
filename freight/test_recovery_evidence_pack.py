import json
from pathlib import Path

import pytest

from freight.recovery_evidence_pack import build_pack, render_markdown


FIXTURE = Path("freight/fixtures/recovery_evidence_pack_synthetic.json")


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_pack_keeps_money_states_and_attribution_separate():
    pack = build_pack(payload())
    totals = pack["totals"]
    assert totals["candidate_difference_cents"] == 28500
    assert totals["validated_difference_cents"] == 24500
    assert totals["net_realized_cents"] == 18500
    assert totals["fee_eligible_realized_cents"] == 18500
    assert totals["suppressed_count"] == 2
    assert pack["findings"][2]["attribution_state"] == "SUPPRESSED"
    assert pack["findings"][2]["fee_eligible_realized_cents"] == 0
    assert pack["findings"][3]["reviewer_disposition"] == "REVIEW"


def test_pack_subtracts_reversal_from_realized_value():
    pack = build_pack(payload())
    finding = pack["findings"][1]
    assert finding["settled_credit_cents"] == 7000
    assert finding["reversal_cents"] == 1000
    assert finding["net_realized_cents"] == 6000


def test_markdown_is_buyer_legible_and_explicitly_synthetic():
    report = render_markdown(build_pack(payload()))
    assert "SYNTHETIC / FICTIONAL EXAMPLE" in report
    assert "Candidate difference" in report
    assert "Fee-eligible realized recovery" in report
    assert "SUPPRESSED" in report
    assert "Controlling rate authority is not proven." in report


def test_duplicate_finding_ids_fail_closed():
    data = payload()
    data["findings"][1]["finding_id"] = data["findings"][0]["finding_id"]
    with pytest.raises(ValueError, match="finding_id must be unique"):
        build_pack(data)


def test_unsupported_money_cannot_become_fee_eligible():
    data = payload()
    row = data["findings"][0]
    row["confidence"] = "INSUFFICIENT"
    pack = build_pack(data)
    assert pack["findings"][0]["attribution_state"] == "SUPPRESSED"
    assert pack["findings"][0]["fee_eligible_realized_cents"] == 0
