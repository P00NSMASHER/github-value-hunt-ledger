"""Deterministic, zero-customer-data diligence bundle for Freight Recovery.

The bundle packages public/internal product-control documentation and generated
release evidence. It intentionally excludes pilot/customer source data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from freight.release_attestation import build_unsigned_dsse
from freight.release_provenance import (
    build_component_inventory,
    build_release_provenance,
)
from freight.sbom import build_cyclonedx_sbom


DOC_PATHS=(
    "freight/AUDIT_RESULT_BUNDLE.md",
    "freight/AUDIT_RUN_MANIFEST.md",
    "freight/AUDIT_WORKFLOW.md",
    "freight/BUYER_REVIEW_WORKFLOW.md",
    "freight/BUSINESS_MODEL.md",
    "freight/COMMERCIAL_QUALIFICATION.md",
    "freight/COMMERCIAL_LEARNING.md",
    "freight/DATA_READINESS_DIAGNOSTIC.md",
    "freight/PILOT_PROTOCOL.md",
    "freight/PILOT_LAUNCH_GATE.md",
    "freight/PILOT_LAUNCH_BRIEF.md",
    "freight/PILOT_ACTIVATION_PACKET.md",
    "freight/PILOT_CHARTER.md",
    "freight/PILOT_AMENDMENT.md",
    "freight/ENGAGEMENT_STATE.md",
    "freight/EXTERNAL_ACTION_AUTHORIZATION.md",
    "freight/FINDING_FACTORY.md",
    "freight/INGESTION_AND_REVIEW_QUEUE.md",
    "freight/REVIEW_PACKET.md",
    "freight/REVIEW_ROUTING.md",
    "freight/REMEDIATION_PLAN.md",
    "freight/RECOVERY_CLAIM_WORKFLOW.md",
    "freight/SEPARATE_ENVIRONMENT_EVIDENCE.md",
    "freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json",
    "freight/PILOT_DATA_ROOM.md",
    "freight/PILOT_REPORT_TEMPLATE.md",
    "freight/PILOT_AUDIT_AND_LIFECYCLE.md",
    "freight/SECURITY_AND_DATA_HANDLING.md",
    "freight/RELEASE_AND_SECURITY_GATE.md",
    "freight/RIGHTS_DILIGENCE.md",
    "freight/RIGHTS_EVIDENCE_MANIFEST.json",
    "freight/INCIDENT_RESPONSE.md",
    "freight/INCIDENT_TABLETOP_TEMPLATE.md",
    "freight/INCIDENT_TABLETOP_2026-09-20.md",
    "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json",
    "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.md",
    "freight/SBOM_AND_ATTESTATION.md",
    "freight/PERSISTENT_AUDIT_AND_BACKUP.md",
    "freight/BUYER_DILIGENCE_BUNDLE.md",
    "freight/COMPONENT_RIGHTS_REGISTRY.json",
    "freight/RELEASE_MANIFEST.md",
)

FIXED_ZIP_TIME=(1980,1,1,0,0,0)


def _sha(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object)->bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )+"\n"
    ).encode("utf-8")


def build_bundle_entries(root: Path)->dict[str,bytes]:
    entries={}
    for rel in DOC_PATHS:
        path=root/rel
        if not path.exists():
            raise ValueError("missing diligence document: "+rel)
        entries[rel]=path.read_bytes()

    entries["generated/release-provenance.json"]=_json_bytes(
        build_release_provenance(root)
    )
    entries["generated/component-inventory.json"]=_json_bytes(
        build_component_inventory(root)
    )
    entries["generated/cyclonedx-sbom.json"]=_json_bytes(
        build_cyclonedx_sbom(root)
    )
    entries["generated/unsigned-dsse-attestation.json"]=_json_bytes(
        build_unsigned_dsse(root)
    )
    return entries


def build_diligence_bundle(root: Path,destination: Path)->dict:
    entries=build_bundle_entries(root)
    manifest_entries=[
        {
            "path":path,
            "size_bytes":len(data),
            "sha256":_sha(data),
        }
        for path,data in sorted(entries.items())
    ]
    manifest={
        "schema_version":1,
        "product":"Freight Recovery",
        "customer_data_included":False,
        "claim_boundary":[
            "Bundle is deterministic documentation/evidence packaging.",
            "Unsigned attestation remains unsigned.",
            "SBOM coverage is partial as documented.",
            "No customer/pilot source data is included.",
            "No certification or deployed-control claim is implied.",
        ],
        "entries":manifest_entries,
    }
    manifest_bytes=_json_bytes(manifest)
    all_entries={**entries,"BUNDLE_MANIFEST.json":manifest_bytes}

    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,"w",compression=zipfile.ZIP_STORED) as zf:
        for path,data in sorted(all_entries.items()):
            info=zipfile.ZipInfo(path,date_time=FIXED_ZIP_TIME)
            info.compress_type=zipfile.ZIP_STORED
            info.external_attr=0o100644<<16
            zf.writestr(info,data)

    return {
        "bundle_sha256":_sha(destination.read_bytes()),
        "entry_count":len(all_entries),
        "manifest_sha256":_sha(manifest_bytes),
    }


def verify_diligence_bundle(root: Path,bundle: Path)->None:
    expected=build_bundle_entries(root)
    with zipfile.ZipFile(bundle,"r") as zf:
        names=zf.namelist()
        if len(names)!=len(set(names)):
            raise ValueError("duplicate bundle entry")
        if "BUNDLE_MANIFEST.json" not in names:
            raise ValueError("bundle manifest missing")
        manifest=json.loads(zf.read("BUNDLE_MANIFEST.json"))
        if manifest.get("customer_data_included") is not False:
            raise ValueError("diligence bundle may not include customer data")
        rows={row["path"]:row for row in manifest.get("entries",[])}
        if set(rows)!=set(expected):
            raise ValueError("bundle manifest entry set mismatch")
        if set(names)!=set(expected)|{"BUNDLE_MANIFEST.json"}:
            raise ValueError("bundle archive entry set mismatch")
        for path,data in expected.items():
            actual=zf.read(path)
            if actual!=data:
                raise ValueError("bundle entry differs from current checkout: "+path)
            row=rows[path]
            if row.get("sha256")!=_sha(actual) or row.get("size_bytes")!=len(actual):
                raise ValueError("bundle manifest hash/size mismatch: "+path)


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("destination",nargs="?")
    parser.add_argument("--verify")
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.verify:
        verify_diligence_bundle(root,Path(args.verify))
        print("OK diligence bundle verified")
        return
    if not args.destination:
        raise SystemExit("destination path required")
    result=build_diligence_bundle(root,Path(args.destination))
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
