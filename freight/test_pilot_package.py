from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    freeze_population,
    freeze_truth,
    make_finding,
    open_incumbent_output,
    seal_incumbent_submission,
    VALIDATED,
)
from freight.deployment_security_evidence import load_current
from freight.launch_authorization import build_launch_authorization
from freight.pilot_launch_gate import DataPath, LaunchRequest
from freight.pilot_package import (
    SourceEntry,
    build_data_room_manifest,
    build_pilot_package,
)
from freight.readiness import PilotReadinessInput, assess_readiness
from freight.release_provenance import build_release_provenance
from freight.rights_evidence import load_json
from freight.separate_environment_evidence import load_environment


BUYER = "buyer-1"
BU = "bu-1"
AS_OF = "2026-09-21"
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=load_json(ROOT/"freight/COMPONENT_RIGHTS_REGISTRY.json")
RIGHTS=load_json(ROOT/"freight/RIGHTS_EVIDENCE_MANIFEST.json")
DEPLOYMENT=load_current(ROOT)
TEMPLATE=load_environment(ROOT/"freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json")


def H(text):
    return hashlib.sha256(text.encode()).hexdigest()


def readiness():
    return assess_readiness(PilotReadinessInput(
        authorization_documented=True,
        read_only_access=True,
        population_reproducible=True,
        incumbent_output_sealable=True,
        settlement_observable=True,
        material_authority_reconstructable=True,
        customer_identity_stable=True,
        carrier_identity_stable=True,
        retention_defined=True,
        deletion_defined=True,
        invoice_source_coverage=1.0,
        authority_source_coverage=1.0,
        shipment_evidence_coverage=1.0,
    ))


def verified_environment():
    e=deepcopy(TEMPLATE)
    e["evidence_status"]="VERIFIED"
    e["environment_id"]="manual-pilot-env-001"
    e["environment_evidence_ref"]="diligence-room/manual-pilot-env-001"
    e["environment_evidence_sha256"]=H("root")
    e["environment_configuration_sha256"]=H("config")
    e["provider_or_host"]="controlled-host"
    e["verified_by_role"]="security-reviewer"
    e["verified_at"]="2026-09-20"
    e["valid_until"]="2026-10-20"
    for name,control in e["controls"].items():
        control["value"]=True
        control["evidence_ref"]="evidence/"+name
        control["evidence_sha256"]=H(name)
    return e


def authorization(*, buyer=BUYER, bu=BU, engagement="ENG-001"):
    return build_launch_authorization(
        engagement_id=engagement,
        buyer_id=buyer,
        business_unit=bu,
        readiness=readiness(),
        component_registry=REGISTRY,
        rights_manifest=RIGHTS,
        deployment_evidence=DEPLOYMENT,
        request=LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        release_provenance=build_release_provenance(ROOT),
        separate_environment_evidence=verified_environment(),
        as_of_date=AS_OF,
    )


def proof_objects():
    population = freeze_population(
        BUYER,
        BU,
        "one invoice",
        [PopulationRow("inv-1","shp-1","cust","car","USD",H("invoice-row"))],
    )
    authority = AuthorityRef(
        "auth-1",BUYER,BU,"cust","car","USD",H("authority-source")
    )
    truth = freeze_truth(
        population,
        [authority],
        [
            make_finding(
                finding_id="f-1", buyer_id=BUYER, business_unit=BU,
                invoice_id="inv-1", shipment_id="shp-1",
                customer_id="cust", carrier_id="car", currency="USD",
                authority_id="auth-1", expected_cents=10000,
                actual_cents=12500, status=VALIDATED,
            )
        ],
    )
    incumbent_hash = H("incumbent-file")
    sealed = seal_incumbent_submission(population, incumbent_hash)
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        submission=sealed,
        finding_ids=[],
    )
    return population, truth, sealed, incumbent


def room_entries():
    return [
        SourceEntry("invoice-1",BUYER,BU,"invoice",H("invoice-file"),True,True,False,30),
        SourceEntry("authority-1",BUYER,BU,"authority",H("authority-file"),True,True,False,30),
        SourceEntry("incumbent-1",BUYER,BU,"incumbent_output",H("incumbent-file"),True,True,False,30),
    ]


def room(auth=None):
    return build_data_room_manifest(
        BUYER,
        BU,
        room_entries(),
        authorization=auth or authorization(),
        authorization_as_of_date=AS_OF,
    )


def test_valid_pilot_package_is_scope_hash_and_launch_bound():
    population, truth, sealed, incumbent = proof_objects()
    auth=authorization()
    data_room=room(auth)
    package = build_pilot_package(
        data_room,
        population,
        truth,
        sealed,
        incumbent,
        authorization=auth,
        authorization_as_of_date=AS_OF,
    )
    assert package.buyer_id == BUYER
    assert package.business_unit == BU
    assert package.engagement_id == "ENG-001"
    assert package.launch_authorization_hash == auth.receipt_hash
    assert package.launch_authorization_valid_until == auth.valid_until
    assert package.population_hash == population.manifest_hash
    assert package.truth_hash == truth.truth_hash
    assert package.package_hash


def test_launch_authorization_scope_must_match_data_room():
    with pytest.raises(ValueError,match="scope mismatch"):
        build_data_room_manifest(
            BUYER,
            BU,
            room_entries(),
            authorization=authorization(buyer="buyer-2"),
            authorization_as_of_date=AS_OF,
        )


def test_expired_launch_authorization_blocks_data_room():
    with pytest.raises(ValueError,match="launch_authorization_expired"):
        build_data_room_manifest(
            BUYER,
            BU,
            room_entries(),
            authorization=authorization(),
            authorization_as_of_date="2026-10-21",
        )


def test_package_rejects_substituted_launch_authorization():
    population, truth, sealed, incumbent = proof_objects()
    original=authorization(engagement="ENG-001")
    data_room=room(original)
    replacement=authorization(engagement="ENG-002")
    with pytest.raises(ValueError,match="engagement mismatch|authorization hash mismatch"):
        build_pilot_package(
            data_room,
            population,
            truth,
            sealed,
            incumbent,
            authorization=replacement,
            authorization_as_of_date=AS_OF,
        )


def test_unauthorized_source_is_rejected():
    entries = room_entries()
    entries[0] = SourceEntry(
        "invoice-1",BUYER,BU,"invoice",H("invoice-file"),True,False,False,30
    )
    with pytest.raises(ValueError,match="unauthorized source"):
        build_data_room_manifest(
            BUYER,
            BU,
            entries,
            authorization=authorization(),
            authorization_as_of_date=AS_OF,
        )


def test_cross_buyer_source_is_rejected():
    entries = room_entries()
    entries[0] = SourceEntry(
        "invoice-1","buyer-2",BU,"invoice",H("invoice-file"),True,True,False,30
    )
    with pytest.raises(ValueError,match="source scope mismatch"):
        build_data_room_manifest(
            BUYER,
            BU,
            entries,
            authorization=authorization(),
            authorization_as_of_date=AS_OF,
        )


def test_secret_bearing_source_is_rejected():
    entries = room_entries()
    entries[0] = SourceEntry(
        "invoice-1",BUYER,BU,"invoice",H("invoice-file"),True,True,True,30
    )
    with pytest.raises(ValueError,match="secret-bearing"):
        build_data_room_manifest(
            BUYER,
            BU,
            entries,
            authorization=authorization(),
            authorization_as_of_date=AS_OF,
        )


def test_incumbent_source_must_be_in_data_room():
    population, truth, sealed, incumbent = proof_objects()
    entries = room_entries()
    entries[2] = SourceEntry(
        "incumbent-1",BUYER,BU,"incumbent_output",H("other-file"),True,True,False,30
    )
    auth=authorization()
    data_room=build_data_room_manifest(
        BUYER,
        BU,
        entries,
        authorization=auth,
        authorization_as_of_date=AS_OF,
    )
    with pytest.raises(ValueError,match="sealed incumbent source missing"):
        build_pilot_package(
            data_room,
            population,
            truth,
            sealed,
            incumbent,
            authorization=auth,
            authorization_as_of_date=AS_OF,
        )
