from pathlib import Path

from freight.release_gate import load_registry, validate_registry


REGISTRY = Path(__file__).with_name("COMPONENT_RIGHTS_REGISTRY.json")


def test_current_registry_is_usable_for_controlled_pilot():
    errors, warnings = validate_registry(load_registry(REGISTRY), "pilot")
    assert errors == []
    assert any("Trenova" in warning for warning in warnings)


def test_current_registry_intentionally_blocks_annual_saas_until_rights_are_resolved():
    errors, _ = validate_registry(load_registry(REGISTRY), "annual")
    assert any("emoss08/Trenova" in error and "hosted/SaaS rights unresolved" in error for error in errors)


def test_short_revision_is_rejected():
    registry = {
        "components": [
            {
                "repository": "x/y",
                "revision": "abc",
                "role": "runtime",
                "public_license": "MIT",
                "commercial_use_basis": "PUBLIC_LICENSE",
            }
        ]
    }
    errors, _ = validate_registry(registry, "pilot")
    assert any("40-char SHA" in error for error in errors)
