from copy import deepcopy
from pathlib import Path

from freight.rights_evidence import load_json, validate_rights_evidence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_json(ROOT / "freight/COMPONENT_RIGHTS_REGISTRY.json")
MANIFEST = load_json(ROOT / "freight/RIGHTS_EVIDENCE_MANIFEST.json")


def test_current_rights_state_is_consistent_for_controlled_pilot():
    errors, warnings = validate_rights_evidence(REGISTRY, MANIFEST, stage="pilot")
    assert errors == []
    assert any("Trenova" in x for x in warnings)
    assert any("opstrax" in x.lower() for x in warnings)


def test_current_rights_state_blocks_annual_clearance():
    errors, _ = validate_rights_evidence(REGISTRY, MANIFEST, stage="annual")
    assert any("annual diligence" in x for x in errors)


def test_resolved_scope_without_verified_evidence_fails():
    manifest = deepcopy(MANIFEST)
    manifest["entries"][0]["scopes"]["hosted_saas"] = "CONFIRMED_ALLOWED"
    errors, _ = validate_rights_evidence(REGISTRY, manifest, stage="pilot")
    assert any("resolved scope hosted_saas requires ATTACHED_VERIFIED" in x for x in errors)


def test_registry_cannot_resolve_scope_without_evidence():
    registry = deepcopy(REGISTRY)
    registry["components"][0]["hosted_saas_status"] = "CONFIRMED_ALLOWED"
    errors, _ = validate_rights_evidence(registry, MANIFEST, stage="pilot")
    assert any("registry resolves hosted_saas_status" in x for x in errors)
