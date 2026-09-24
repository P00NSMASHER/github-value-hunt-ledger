from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from freight.rights_evidence import load_json, validate_rights_evidence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_json(ROOT / "freight/COMPONENT_RIGHTS_REGISTRY.json")
MANIFEST = load_json(ROOT / "freight/RIGHTS_EVIDENCE_MANIFEST.json")


def verified_pilot_manifest():
    manifest = deepcopy(MANIFEST)
    for entry in manifest["entries"]:
        repository = entry["repository"]
        entry["evidence_status"] = "ATTACHED_VERIFIED"
        entry["evidence_location"] = f"diligence-room/{repository}"
        entry["evidence_sha256"] = sha256(repository.encode()).hexdigest()
        entry["scopes"]["commercial_use"] = "CONFIRMED_ALLOWED"
    return manifest


def test_current_owner_attested_rights_clear_controlled_pilot():
    errors, warnings = validate_rights_evidence(REGISTRY, MANIFEST, stage="pilot")
    assert errors == []
    assert warnings == []


def test_verified_executed_commercial_permissions_clear_pilot_gate():
    errors, warnings = validate_rights_evidence(
        REGISTRY,
        verified_pilot_manifest(),
        stage="pilot",
    )
    assert errors == []
    assert warnings == []


def test_current_rights_state_blocks_annual_clearance():
    errors, _ = validate_rights_evidence(REGISTRY, MANIFEST, stage="annual")
    assert any("annual diligence" in x for x in errors)


def test_resolved_scope_without_verified_evidence_fails():
    manifest = deepcopy(MANIFEST)
    manifest["entries"][0]["evidence_status"] = "NOT_ATTACHED"
    manifest["entries"][0]["evidence_location"] = None
    manifest["entries"][0]["evidence_sha256"] = None
    manifest["entries"][0]["scopes"]["hosted_saas"] = "CONFIRMED_ALLOWED"
    errors, _ = validate_rights_evidence(REGISTRY, manifest, stage="pilot")
    assert any("resolved scope hosted_saas requires ATTACHED_VERIFIED" in x for x in errors)


def test_registry_cannot_resolve_scope_without_evidence():
    registry = deepcopy(REGISTRY)
    registry["components"][0]["hosted_saas_status"] = "CONFIRMED_ALLOWED"
    errors, _ = validate_rights_evidence(registry, MANIFEST, stage="pilot")
    assert any("registry resolves hosted_saas_status" in x for x in errors)


def test_verified_but_denied_commercial_use_still_blocks_runtime():
    manifest = verified_pilot_manifest()
    manifest["entries"][0]["scopes"]["commercial_use"] = "CONFIRMED_DENIED"
    errors, _ = validate_rights_evidence(REGISTRY, manifest, stage="pilot")
    assert any("commercial_use must be CONFIRMED_ALLOWED" in x for x in errors)
