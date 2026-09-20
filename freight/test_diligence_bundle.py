import json
import zipfile

import pytest

from freight.diligence_bundle import (
    build_diligence_bundle,
    verify_diligence_bundle,
)


def test_diligence_bundle_is_byte_deterministic(tmp_path):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    a=tmp_path/"a.zip"
    b=tmp_path/"b.zip"
    ra=build_diligence_bundle(root,a)
    rb=build_diligence_bundle(root,b)
    assert a.read_bytes()==b.read_bytes()
    assert ra["bundle_sha256"]==rb["bundle_sha256"]
    verify_diligence_bundle(root,a)


def test_bundle_manifest_explicitly_excludes_customer_data(tmp_path):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    bundle=tmp_path/"bundle.zip"
    build_diligence_bundle(root,bundle)
    with zipfile.ZipFile(bundle) as zf:
        manifest=json.loads(zf.read("BUNDLE_MANIFEST.json"))
    assert manifest["customer_data_included"] is False
    assert all(not x["path"].startswith("customer/") for x in manifest["entries"])


def test_tampered_bundle_entry_is_rejected(tmp_path):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    bundle=tmp_path/"bundle.zip"
    build_diligence_bundle(root,bundle)

    tampered=tmp_path/"tampered.zip"
    with zipfile.ZipFile(bundle,"r") as src, zipfile.ZipFile(tampered,"w") as dst:
        for name in src.namelist():
            data=src.read(name)
            if name=="freight/BUSINESS_MODEL.md":
                data+=b"\ntamper\n"
            dst.writestr(name,data)

    with pytest.raises(ValueError,match="differs from current checkout|hash/size mismatch"):
        verify_diligence_bundle(root,tampered)


def test_bundle_contains_rights_and_incident_diligence(tmp_path):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    bundle=tmp_path/"bundle.zip"
    build_diligence_bundle(root,bundle)
    with zipfile.ZipFile(bundle) as zf:
        names=set(zf.namelist())
        manifest=json.loads(zf.read("BUNDLE_MANIFEST.json"))
    expected={
        "freight/RIGHTS_DILIGENCE.md",
        "freight/RIGHTS_EVIDENCE_MANIFEST.json",
        "freight/INCIDENT_RESPONSE.md",
        "freight/INCIDENT_TABLETOP_TEMPLATE.md",
        "freight/PILOT_LAUNCH_GATE.md",
        "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.md",
        "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json",
        "freight/INCIDENT_TABLETOP_2026-09-20.md",
    }
    assert expected.issubset(names)
    assert expected.issubset({row["path"] for row in manifest["entries"]})
