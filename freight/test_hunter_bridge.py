import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from freight.hunter_bridge import INPUTS, build_report, capability_evidence, digest, load_report, render_markdown


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    # Stable behavioral fixtures must not prohibit future paid buyers or new
    # Hunter capabilities. The separate CLI smoke test reads the real registry.
    capabilities = [{
        "capability_id": identity, "name": "Synthetic capability " + identity,
        "evidence_basis": "Synthetic source evidence", "evidence_state": "benchmarked",
        "source_markdown": "CAPABILITIES.md", "maturity": "BENCHMARKED",
    } for identity in ("CAP-001", "CAP-006", "CAP-016", "CAP-019")]
    edges = [{"edge_id": "EDGE:12345678", "from": "REPO:test/source", "to": "CAP-001",
              "type": "IMPLEMENTS", "evidence_ref": "CAPABILITIES.md"}]
    runs = [{"search_run_id": "RUN:test:baseline", "seed_nodes": ["CAP-001", "CAP-006", "CAP-016"],
             "durable_evidence_path": "hunters/test.md", "best_result": "Synthetic reference evidence"}]
    gaps = {"stage_gate": "EXP-001", "gaps": [{
        "gap_id": "FRT-EXP001-001", "title": "External buyer evidence", "status": "BLOCKED_EXTERNAL",
        "search_allowed": False, "allowed_triggers": [], "commercial_effect": "Demand unvalidated",
        "evidence_to_close": ["Authorized buyer evidence"], "stop_condition": "Reviewed buyer result",
    }]}
    mapping = {"schema_version": 1, "experiment_id": "EXP-001", "reviewed_source_ref": "f" * 40,
               "capabilities": [{
                   "capability_id": cap["capability_id"], "disposition": "USE", "priority": "P0",
                   "freight_use": "Review proposed evidence use", "rationale": "Synthetic application",
                   "acceptance_test": "Measurable reviewed result", "limitation": "Synthetic only",
                   "gap_ids": ["FRT-EXP001-001"],
                   "reviewed_evidence_sha256": digest(capability_evidence(cap, edges, runs)),
               } for cap in capabilities]}
    outcomes = [{
        "outcome_id": "OUT:test:synthetic", "experiment_id": "EXP-001", "result": "PARTIAL",
        "origin_search_ids": ["RUN:test:baseline"], "contributing_capability_ids": ["CAP-006", "CAP-016"],
        "evidence_location": "freight/synthetic_rehearsal.py", "freight_metrics": {"synthetic": True},
    }]
    return {"capabilities": capabilities, "edges": edges, "search_runs": runs,
            "gaps": gaps, "mapping": mapping, "outcomes": outcomes}


def report(inputs):
    return build_report(inputs["capabilities"], inputs["edges"], inputs["outcomes"],
                        inputs["search_runs"], inputs["gaps"], inputs["mapping"])


def test_report_covers_reviewed_registry_without_promoting_synthetic_results(inputs):
    result = report(inputs)
    assert result["coverage"]["mapped_capabilities"] == len(inputs["capabilities"])
    assert result["coverage"]["dispositions"] == {"DEFER": 0, "OUT_OF_SCOPE": 0, "USE": 4}
    assert result["mode"] == "REVIEW_ONLY"
    assert result["commercial_calibration"]["recommended_action"] == "KEEP_PRIOR"
    assert result["commercial_calibration"]["status"] == "NO_EXTERNAL_DATA"
    assert result["commercial_calibration"]["paid_engagements"] == 0
    assert result["outcomes"][0]["synthetic"] is True
    assert result["gap_backlog"][0]["status"] == "BLOCKED_EXTERNAL"
    assert all(not gap["search_allowed"] for gap in result["gap_backlog"])


def test_new_capability_defaults_to_review_and_defer(inputs):
    new = copy.deepcopy(inputs["capabilities"][0])
    new["capability_id"] = "CAP-999"
    inputs["capabilities"].append(new)
    result = report(inputs)
    row = next(row for row in result["capabilities"] if row["capability_id"] == "CAP-999")
    assert row["review_status"] == "UNMAPPED"
    assert row["disposition"] == "DEFER"
    assert {"capability_id": "CAP-999", "reason": "UNMAPPED"} in result["review_items"]


@pytest.mark.parametrize("source", ["capability", "edge", "search"])
def test_changed_structured_evidence_is_routed_to_review(inputs, source):
    if source == "capability":
        inputs["capabilities"][0]["evidence_basis"] += " Updated inspected evidence."
    elif source == "edge":
        edge = next(edge for edge in inputs["edges"] if "CAP-001" in (edge["from"], edge["to"]))
        edge["evidence_ref"] += "#updated-evidence"
    else:
        inputs["search_runs"].append({
            "search_run_id": "RUN:test:new-inspection", "seed_nodes": ["CAP-001"],
            "durable_evidence_path": "hunters/review.md", "best_result": "New evidence to review.",
        })
    result = report(inputs)
    assert {"capability_id": "CAP-001", "reason": "SOURCE_CHANGED"} in result["review_items"]
    assert result["commercial_calibration"]["paid_engagements"] == 0


def test_removed_capability_requires_mapping_review(inputs):
    inputs["capabilities"] = [row for row in inputs["capabilities"] if row["capability_id"] != "CAP-019"]
    assert {"capability_id": "CAP-019", "reason": "REMOVED_FROM_REGISTRY"} in report(inputs)["review_items"]


@pytest.mark.parametrize("case", ["unknown_run", "unknown_capability", "blank_location"])
def test_unattributed_external_outcome_cannot_enter_calibration(inputs, case):
    outcome = {
        "outcome_id": "OUT:test:external", "experiment_id": "EXP-001", "result": "PARTIAL",
        "origin_search_ids": [inputs["search_runs"][0]["search_run_id"]],
        "contributing_capability_ids": ["CAP-001"], "evidence_location": "controlled/evidence",
        "revenue_usd": 1000,
        "freight_metrics": {"synthetic": False, "external_commercial_evidence": True,
                            "engagement_id": "engagement-1", "buyer_cohort_key": "buyer-1", "diagnostic_paid": True},
    }
    if case == "unknown_run":
        outcome["origin_search_ids"] = ["RUN:test:missing"]
    elif case == "unknown_capability":
        outcome["contributing_capability_ids"] = ["CAP-999"]
    else:
        outcome["evidence_location"] = "  "
    inputs["outcomes"].append(outcome)
    result = report(inputs)
    assert result["commercial_calibration"]["paid_engagements"] == 0
    assert {"outcome_id": "OUT:test:external", "reason": "OUTCOME_PROVENANCE_INCOMPLETE"} in result["review_items"]


def test_external_outcomes_use_existing_calibration_thresholds(inputs):
    inputs["outcomes"].append({
        "outcome_id": "OUT:test:external", "experiment_id": "EXP-001", "result": "PARTIAL",
        "origin_search_ids": [inputs["search_runs"][0]["search_run_id"]],
        "contributing_capability_ids": ["CAP-001"], "evidence_location": "controlled/evidence",
        "revenue_usd": 1000,
        "freight_metrics": {"synthetic": False, "external_commercial_evidence": True,
                            "engagement_id": "engagement-1", "buyer_cohort_key": "buyer-1", "diagnostic_paid": True},
    })
    result = report(inputs)
    assert result["commercial_calibration"]["paid_engagements"] == 1
    assert result["commercial_calibration"]["status"] == "OBSERVE_ONLY"
    assert result["commercial_calibration"]["recommended_action"] == "KEEP_PRIOR"
    assert "buyer-1" not in json.dumps(result)


@pytest.mark.parametrize("kind,key", [("capabilities", "capability_id"), ("edges", "edge_id"), ("outcomes", "outcome_id"), ("search_runs", "search_run_id")])
def test_duplicate_registry_id_is_rejected(inputs, kind, key):
    inputs[kind].append(copy.deepcopy(inputs[kind][0]))
    with pytest.raises(ValueError, match=f"{key}: duplicate"):
        report(inputs)


def test_mapping_cannot_invent_freight_gap(inputs):
    inputs["mapping"]["capabilities"][0]["gap_ids"] = ["FRT-INVENTED-001"]
    with pytest.raises(ValueError, match="unknown gap"):
        report(inputs)


def test_report_is_deterministic_and_does_not_mutate_inputs(inputs):
    before = copy.deepcopy(inputs)
    first = report(inputs)
    assert inputs == before
    for name in ("capabilities", "edges", "outcomes", "search_runs"):
        inputs[name].reverse()
    assert report(inputs) == first
    assert "Business blockers" in render_markdown(first)


def test_catalog_change_is_detected_even_before_generated_registry_refresh(tmp_path):
    for relative in [*INPUTS.values(), "CAPABILITIES.md"]:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    mapping_path = tmp_path / INPUTS["mapping"]
    mapping = json.loads(mapping_path.read_text())
    mapping["reviewed_catalog_sha256"] = hashlib.sha256((tmp_path / "CAPABILITIES.md").read_bytes()).hexdigest()
    mapping_path.write_text(json.dumps(mapping))
    baseline = load_report(tmp_path)
    with (tmp_path / "CAPABILITIES.md").open("a") as handle:
        handle.write("\nReviewed catalog observation changed.\n")
    result = load_report(tmp_path)
    assert result["coverage"]["review_required"] == baseline["coverage"]["review_required"] + 1
    assert {"source_path": "CAPABILITIES.md", "reason": "CANONICAL_CATALOG_CHANGED"} in result["review_items"]


def test_cli_reads_and_fingerprints_sources_without_writing():
    paths = [ROOT / relative for relative in [*INPUTS.values(), "CAPABILITIES.md"]]
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    command = [sys.executable, "-m", "freight.hunter_bridge", "--format", "json"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    document = json.loads(result.stdout)
    assert len(document["input_manifest"]) == len(paths)
    assert before == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert document["source_ref"] is None
