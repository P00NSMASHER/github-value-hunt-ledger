from pathlib import Path

from freight.sbom import build_cyclonedx_sbom, verify_sbom


ROOT = Path(__file__).resolve().parents[1]


def test_sbom_is_deterministic_and_valid():
    a = build_cyclonedx_sbom(ROOT)
    b = build_cyclonedx_sbom(ROOT)
    assert a == b
    verify_sbom(a)
    assert a["bomFormat"] == "CycloneDX"
    assert a["specVersion"] == "1.6"
    assert len(a["components"]) >= 10


def test_sbom_contains_pinned_github_and_pypi_components():
    sbom = build_cyclonedx_sbom(ROOT)
    refs = {c["bom-ref"] for c in sbom["components"]}
    assert any(ref.startswith("github:emoss08/Trenova@") for ref in refs)
    assert any(ref.startswith("pkg:pypi/pytest@") for ref in refs)
