"""Deterministic release provenance and component inventory for Freight Recovery.

This generator hashes committed Freight control files and the rights registry.
It does not provide a cryptographic signature. A deterministic CycloneDX-shaped
inventory is generated separately by freight/sbom.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
CONTROL_PATHS = (
    "freight/audit_ledger.py",
    "freight/audit_result_bundle.py",
    "freight/audit_run_manifest.py",
    "freight/audit_workflow.py",
    "freight/diligence_bundle.py",
    "freight/backup_restore.py",
    "freight/audit_store.py",
    "freight/commercial_learning.py",
    "freight/contracts.py",
    "freight/data_lifecycle.py",
    "freight/deal_economics.py",
    "freight/deployment_security_evidence.py",
    "freight/engagement_state.py",
    "freight/external_action_authorization.py",
    "freight/finding_factory.py",
    "freight/gap_registry.py",
    "freight/input_guard.py",
    "freight/invoice_csv_adapter.py",
    "freight/incident_response.py",
    "freight/launch_brief.py",
    "freight/outcome_adapter.py",
    "freight/pilot_activation_packet.py",
    "freight/pilot_amendment.py",
    "freight/pilot_charter.py",
    "freight/pilot_package.py",
    "freight/pilot_launch_gate.py",
    "freight/pilot_reporting.py",
    "freight/population_builder.py",
    "freight/readiness.py",
    "freight/remediation_plan.py",
    "freight/review_packet.py",
    "freight/review_queue.py",
    "freight/review_routing.py",
    "freight/rule_csv_adapter.py",
    "freight/release_attestation.py",
    "freight/release_gate.py",
    "freight/release_provenance.py",
    "freight/rights_evidence.py",
    "freight/separate_environment_evidence.py",
    "freight/sbom.py",
    "freight/settlement_store.py",
    "freight/settlement_report.py",
    "freight/synthetic_rehearsal.py",
    "freight/COMPONENT_RIGHTS_REGISTRY.json",
    "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json",
    "freight/RIGHTS_EVIDENCE_MANIFEST.json",
    "freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json",
    "freight/GAP_REGISTER.json",
    "intelligence/domain_search_policies.json",
    "production/requirements-ci.txt",
    ".github/workflows/freight-contracts.yml",
    ".github/workflows/technology-intelligence.yml",
)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return _hash_bytes(payload)


def validate_components(components: list[dict]) -> None:
    seen = set()
    for component in components:
        repository = component.get("repository")
        revision = component.get("revision")
        if not isinstance(repository, str) or "/" not in repository:
            raise ValueError("component repository must be owner/name")
        if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
            raise ValueError(repository + ": revision must be full lowercase 40-char SHA")
        key = (repository, revision)
        if key in seen:
            raise ValueError("duplicate component revision: " + repository + "@" + revision)
        seen.add(key)


def build_component_inventory(root: Path) -> dict:
    registry_path = root / "freight/COMPONENT_RIGHTS_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    components = registry.get("components") or []
    validate_components(components)
    normalized = [
        {
            "repository": c["repository"],
            "revision": c["revision"],
            "role": c.get("role"),
            "public_license": c.get("public_license"),
            "commercial_use_basis": c.get("commercial_use_basis"),
            "runtime_status": c.get("runtime_status"),
        }
        for c in components
    ]
    normalized.sort(key=lambda x: (x["repository"], x["revision"]))
    body = {
        "format": "freight-component-inventory-v1",
        "component_count": len(normalized),
        "components": normalized,
    }
    return body | {"inventory_hash": _canonical_hash(body)}


def build_release_provenance(root: Path) -> dict:
    missing = [path for path in CONTROL_PATHS if not (root / path).exists()]
    if missing:
        raise ValueError("missing control files: " + ",".join(missing))

    files = {
        path: _hash_file(root / path)
        for path in sorted(CONTROL_PATHS)
    }
    inventory = build_component_inventory(root)
    body = {
        "schema_version": 1,
        "product": "Freight Recovery",
        "control_file_hashes": files,
        "component_inventory": inventory,
    }
    return body | {"provenance_hash": _canonical_hash(body)}


def verify_snapshot(root: Path, snapshot_path: Path) -> None:
    expected = build_release_provenance(root)
    actual = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("release provenance snapshot does not match current checkout")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify")
    parser.add_argument("--components", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if args.verify:
        verify_snapshot(root, Path(args.verify))
        print("OK release provenance verified")
        return

    payload = (
        build_component_inventory(root)
        if args.components
        else build_release_provenance(root)
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
