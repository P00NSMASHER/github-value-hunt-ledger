"""Deterministic CycloneDX-shaped SBOM for Freight Recovery diligence.

The SBOM covers pinned repository components in the Freight rights registry and
pinned direct CI Python dependencies. It does not claim complete transitive
runtime/deployment inventory.
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path

from freight.release_provenance import build_component_inventory, _canonical_hash


REQ_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s#]+)$")


def _requirements(root: Path) -> list[dict]:
    path = root / "production/requirements-ci.txt"
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = REQ_RE.fullmatch(line)
        if not match:
            raise ValueError("unrecognized pinned requirement: " + line)
        name, version = match.groups()
        out.append({
            "type": "library",
            "bom-ref": f"pkg:pypi/{name.lower()}@{version}",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower()}@{version}",
            "properties": [
                {"name": "freight:component-class", "value": "direct-ci-python-dependency"}
            ],
        })
    return sorted(out, key=lambda x: x["bom-ref"])


def build_cyclonedx_sbom(root: Path) -> dict:
    inventory = build_component_inventory(root)
    components = []
    for c in inventory["components"]:
        repository = c["repository"]
        revision = c["revision"]
        properties = [
            {"name": "freight:component-class", "value": "github-repository"},
            {"name": "freight:repository", "value": repository},
            {"name": "freight:revision", "value": revision},
            {"name": "freight:public-license-record", "value": str(c.get("public_license"))},
            {"name": "freight:commercial-use-basis", "value": str(c.get("commercial_use_basis"))},
            {"name": "freight:runtime-status", "value": str(c.get("runtime_status"))},
        ]
        components.append({
            "type": "library",
            "bom-ref": f"github:{repository}@{revision}",
            "name": repository,
            "version": revision,
            "externalReferences": [
                {"type": "vcs", "url": f"https://github.com/{repository}"}
            ],
            "properties": properties,
        })

    components.extend(_requirements(root))
    components.sort(key=lambda x: x["bom-ref"])

    body = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "Freight Recovery",
                "version": "15.7-diligence",
            },
            "properties": [
                {
                    "name": "freight:coverage-note",
                    "value": "Pinned Freight rights-registry repositories plus direct pinned CI Python dependencies; not a complete transitive deployment SBOM.",
                }
            ],
        },
        "components": components,
    }
    digest = _canonical_hash(body)
    body["serialNumber"] = "urn:uuid:" + str(
        uuid.uuid5(uuid.NAMESPACE_URL, "freight-sbom:" + digest)
    )
    body["properties"] = [
        {"name": "freight:sbom-content-sha256", "value": digest}
    ]
    return body


def verify_sbom(sbom: dict) -> None:
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.6":
        raise ValueError("unexpected SBOM format/version")
    refs = [c.get("bom-ref") for c in sbom.get("components", [])]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise ValueError("SBOM component references missing or duplicated")
    if not str(sbom.get("serialNumber", "")).startswith("urn:uuid:"):
        raise ValueError("SBOM serialNumber missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.verify:
        actual = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        expected = build_cyclonedx_sbom(root)
        verify_sbom(actual)
        if actual != expected:
            raise SystemExit("SBOM snapshot does not match current checkout")
        print("OK CycloneDX SBOM verified")
        return
    print(json.dumps(build_cyclonedx_sbom(root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
