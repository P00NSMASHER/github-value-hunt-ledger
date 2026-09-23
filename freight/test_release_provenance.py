from pathlib import Path

from freight.release_provenance import (
    build_component_inventory,
    build_release_provenance,
    validate_components,
)


ROOT = Path(__file__).resolve().parents[1]


def test_current_component_inventory_uses_full_revisions():
    inventory = build_component_inventory(ROOT)
    assert inventory["component_count"] >= 1
    assert inventory["inventory_hash"]
    for component in inventory["components"]:
        assert len(component["revision"]) == 40


def test_current_release_provenance_is_deterministic():
    a = build_release_provenance(ROOT)
    b = build_release_provenance(ROOT)
    assert a == b
    assert a["provenance_hash"]
    assert "freight/contracts.py" in a["control_file_hashes"]
    assert "production/requirements-ci.txt" in a["control_file_hashes"]
    assert "freight/rights_evidence.py" in a["control_file_hashes"]
    assert "freight/incident_response.py" in a["control_file_hashes"]
    assert "freight/deployment_security_evidence.py" in a["control_file_hashes"]
    assert "freight/pilot_launch_gate.py" in a["control_file_hashes"]
    assert "freight/separate_environment_evidence.py" in a["control_file_hashes"]
    assert "freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json" in a["control_file_hashes"]
    assert "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json" in a["control_file_hashes"]
    assert "freight/RIGHTS_EVIDENCE_MANIFEST.json" in a["control_file_hashes"]
    assert "freight/settlement_schema.sql" in a["control_file_hashes"]
    assert ".github/workflows/technology-intelligence.yml" in a["control_file_hashes"]
    assert ".github/workflows/recoveryworks.yml" in a["control_file_hashes"]
    assert ".github/workflows/public-repo-hunter.yml" in a["control_file_hashes"]


def test_invalid_component_revision_fails_closed():
    try:
        validate_components([
            {
                "repository": "x/y",
                "revision": "abc",
            }
        ])
    except ValueError as exc:
        assert "40-char SHA" in str(exc)
    else:
        raise AssertionError("short revision should fail")
