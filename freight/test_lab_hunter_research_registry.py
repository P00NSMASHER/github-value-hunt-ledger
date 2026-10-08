"""Quality gate for the cumulative *research* finding register, not freight safety.

Do not read a passing catalog check as closure of a financial-control issue.
This suite protects historical finding IDs, source and code-donor references.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent / "research"
ORIGINAL_IDS = {
    "LAB-P0-01","LAB-P0-02","LAB-P0-03","LAB-P0-04",
    "LAB-P1-05","LAB-P1-06","LAB-P1-07","LAB-P2-08",
    *(f"D-{i:02d}" for i in range(1,9)),
    *(f"X-{i:02d}" for i in range(1,6)),
    *(f"Y-{i:02d}" for i in range(1,5)),
    "Z-01",
}

def documents():
    return (json.loads((ROOT/"LAB_FINDINGS_CUMULATIVE.json").read_text()),
            json.loads((ROOT/"HUNTED_CODE_REUSE_CANDIDATES.json").read_text()))

def test_cumulative_findings_do_not_silently_disappear():
    findings, _=documents()
    rows=findings["entries"]
    identities=[x["id"] for x in rows]
    assert len(set(identities))==len(identities)
    assert ORIGINAL_IDS.issubset(identities)
    assert findings["entries_total"]==len(rows)
    assert len(rows)>=26
    assert sum(findings["cluster_counts"].values())==len(rows)

def test_research_is_never_marked_production_approved():
    findings, _=documents()
    assert findings["status"]=="RELEASE_FINANCIAL_ASSURANCE_BLOCKED"
    for row in findings["entries"]:
        assert row["customer_or_production_impact"]=="NOT_ESTABLISHED"
        assert row["remediation"]!="FIXED"
        assert row["customer_or_production_impact"]=="NOT_ESTABLISHED"

def test_donor_reuse_is_review_only_with_exact_revisions():
    _, candidates=documents()
    rows=candidates["ranked"]
    assert len(rows)>=9
    assert len({r["id"] for r in rows})==len(rows)
    allowed={"MIT","Apache-2.0","MIT OR Apache-2.0"}
    for entry in rows:
        assert entry["license"] in allowed
        assert len(entry["revision"])==40 and all(c in "0123456789abcdef" for c in entry["revision"])
        assert entry["inspected_source"].startswith("https://github.com/")
        assert entry["code_copied"] is False and entry["package_installed"] is False
        assert entry["staging_product_equivalence"]=="NOT_TESTED"
        assert entry["addresses"]
