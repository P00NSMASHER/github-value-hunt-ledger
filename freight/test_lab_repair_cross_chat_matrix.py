"""Prevent concurrent branches from double-claiming completion of lab defects."""
import json
from pathlib import Path

from freight.lab_repair_04_14_contract import FINDINGS

MATRIX = Path(__file__).parent / "LAB_REPAIR_CROSS_CHAT_MATRIX.json"
ORIGINAL = set([
    "LAB-P0-01","LAB-P0-02","LAB-P0-03","LAB-P0-04",
    "LAB-P1-05","LAB-P1-06","LAB-P1-07","LAB-P2-08",
    *(f"D-{i:02d}" for i in range(1,9)),
    *(f"X-{i:02d}" for i in range(1,6)),
    *(f"Y-{i:02d}" for i in range(1,5)), "Z-01",
])

def test_no_findings_dropped_or_double_owned():
    j=json.loads(MATRIX.read_text())
    rows=j["findings"]
    by_id={r["finding_id"]:r for r in rows}
    assert len(rows)==len(by_id)==28
    assert ORIGINAL.issubset(by_id)
    assert set(by_id)-ORIGINAL=={"GATE-001","GATE-002"}
    assert {k for k in ORIGINAL if by_id[k]["owner"]=="PR-287-ISOLATED-LABS-04-14"}==FINDINGS
    assert {k for k in ORIGINAL if by_id[k]["owner"]=="PR-286-ORIGINAL-UNIFIED-REVIEW"}==ORIGINAL-FINDINGS
    assert j["isolated_offline_patch_tested"]==10
    assert j["remaining_original_findings_waiting_independent_confirmation"]==16
    assert j["all_production_defects_closed"] is False

def test_repaired_offline_not_marked_staging_or_full_scale():
    j=json.loads(MATRIX.read_text())
    for row in j["findings"]:
        assert row["hosted_product_verified"] is False
        assert row["staging_verified"] is False
        assert row["full_legacy_population_regenerated"] is False
        if row["finding_id"] in FINDINGS:
            assert row["status"]=="OFFLINE_TOOLKIT_REPAIR_TESTED"
        elif row["finding_id"] in ORIGINAL:
            assert row["status"]=="AWAITING_INDEPENDENT_FIX_EVIDENCE"
        else:
            assert row["status"]=="FIXED_RESEARCH_GATE_ONLY"
