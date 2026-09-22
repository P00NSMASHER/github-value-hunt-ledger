from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest

from recoveryworks import (
    AuthorityRegistry,
    AuthoritySnapshot,
    CalculationManifest,
    NegativeEvidenceSearch,
    PopulationSegment,
    RetainedSourceObject,
    ChallengeReview,
    ClientActionAuthorization,
    DeadlineAssessment,
    DurableRecoveryLedger,
    EvidenceRef,
    ExternalActionEnvelope,
    RecoveryEngine,
    RecoveryObservation,
    ReviewAttestation,
    RuleRef,
    SourceAttestation,
    authorize_case_action,
    build_hostile_examination_packet,
    build_seven_figure_authorization_dossier,
    build_seven_figure_readiness,
    create_build_provenance_attestation,
    create_proof_seal,
    create_public_verification_record,
    freeze_case_completeness,
    freeze_case_proof,
    freeze_source_retention,
    prepare_external_action,
    record_external_signature_verification,
    record_external_timestamp_verification,
    record_object_lock_verification,
    replay_case_calculation,
    replay_case_source_artifacts,
    verify_external_action,
    verify_proof_seal,
)
from recoveryworks.models import Branch, canonical_hash


FIXTURE = Path(__file__).with_name("simulated_data") / "seven_figure_freight.json"
SIM_SEAL_KEY = bytes.fromhex(
    "8f4d0f0dc0bd8d0fb95130c7ff056857"
    "f2767f72cc04f39a1f716d6a1bd9b182"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _trace_bytes(trace: dict) -> bytes:
    return json.dumps(
        trace,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _build_readiness(
    payload: dict,
    bundle,
    calculation,
    ledger,
    challenge_manifest_hash: str,
):
    authority_bytes = payload["authority_source"]["content"].encode("utf-8")
    evidence_bytes = {
        src["evidence_id"]: src["content"].encode("utf-8")
        for src in payload["evidence_sources"]
    }
    artifact_receipt = replay_case_source_artifacts(
        bundle,
        authority_bytes=authority_bytes,
        evidence_bytes=evidence_bytes,
        replayed_at="2026-09-22T16:21:00Z",
        replayed_by="sim-independent-examiner",
    )
    calculation_receipt = replay_case_calculation(
        bundle,
        artifact_receipt,
        calculator_id=calculation.calculator_id,
        calculator_version=calculation.calculator_version,
        code_commit_sha=calculation.code_commit_sha,
        input_manifest_hash=calculation.input_manifest_hash,
        expected_cents=bundle.finding.expected_cents,
        actual_cents=bundle.finding.actual_cents,
        trace_bytes=_trace_bytes(payload["calculation"]["trace"]),
        reproduced_at="2026-09-22T16:22:00Z",
        reproduced_by="sim-independent-calculation-examiner",
    )
    preauth_seal = create_proof_seal(
        bundle,
        seal_id="SIM-PREAUTH-SEAL-1",
        key_id=payload["seal"]["key_id"],
        secret_key=SIM_SEAL_KEY,
        journal_head_hash=ledger.journal.head_hash,
        sealed_at="2026-09-22T16:23:00Z",
    )
    packet = build_hostile_examination_packet(
        bundle,
        artifact_receipt,
        calculation_receipt,
        preauth_seal,
        journal_head_hash=ledger.journal.head_hash,
        secret_key=SIM_SEAL_KEY,
        key_id=payload["seal"]["key_id"],
        assembled_at="2026-09-22T16:23:30Z",
        assembled_by="sim-hostile-exam-assembler",
    )

    retention_entries = []
    authority = payload["authority_source"]
    retention_entries.append(RetainedSourceObject(
        source_id=authority["authority_id"],
        role="authority",
        source_hash=hashlib.sha256(authority_bytes).hexdigest(),
        size_bytes=len(authority_bytes),
        storage_uri="sim-private://object-lock/authority",
        retained_at=authority["acquired_at"],
        retention_mode="OBJECT_LOCK_COMPLIANCE",
        retention_control_id="SIM-LOCK-AUTH",
        provider_attestation_hash=_sha("SIM PROVIDER AUTHORITY RECEIPT"),
        immutable_storage_verified=True,
        retain_until="2033-09-22T00:00:00Z",
        metadata={"simulation_only": True},
    ))
    for index, src in enumerate(payload["evidence_sources"], start=1):
        raw = evidence_bytes[src["evidence_id"]]
        retention_entries.append(RetainedSourceObject(
            source_id=src["evidence_id"],
            role="evidence",
            source_hash=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            storage_uri=f"sim-private://object-lock/evidence-{index}",
            retained_at=src["acquired_at"],
            retention_mode="OBJECT_LOCK_COMPLIANCE",
            retention_control_id=f"SIM-LOCK-EVIDENCE-{index}",
            provider_attestation_hash=_sha(
                f"SIM PROVIDER EVIDENCE RECEIPT {index}"
            ),
            immutable_storage_verified=True,
            retain_until="2033-09-22T00:00:00Z",
            metadata={"simulation_only": True},
        ))
    retention = freeze_source_retention(
        bundle,
        entries=retention_entries,
        created_at="2026-09-22T16:24:00Z",
        created_by="sim-custody-controller",
    )

    tms_source = next(
        src for src in payload["evidence_sources"]
        if src["kind"] == "tms_shipment_population"
    )
    tms = json.loads(tms_source["content"])
    population = PopulationSegment(
        segment_id="SIM-AUG-2026-SHIPMENTS",
        source_export_hash=_sha(tms_source["content"]),
        selection_rule="All invoiced August 2026 shipments for SIM-CARRIER-A",
        record_count=tms["shipment_count"],
        included_record_count=tms["shipment_count"],
        excluded_record_count=0,
        control_total_hash=canonical_hash({
            "shipment_count": tms["shipment_count"],
            "contract_total": tms["frozen_population_total_contract_usd"],
        }),
        included_ids_hash=_sha("SIMULATED SORTED SHIPMENT IDS"),
        excluded_ids_hash=_sha("EMPTY"),
        metadata={"simulation_only": True},
    )
    negative_search = NegativeEvidenceSearch(
        search_id="SIM-NEGATIVE-SEARCH-READINESS",
        scope=payload["challenge"]["challenge"],
        method="Synthetic full-population search for contrary commercial evidence",
        searched_source_hashes=tuple(
            [bundle.authority.source_hash]
            + [item.source_hash for item in bundle.source_attestations]
            + [challenge_manifest_hash]
        ),
        contrary_evidence_hashes=(),
        searched_at=payload["challenge"]["reviewed_at"],
        searched_by=payload["challenge"]["reviewer_id"],
        conclusion=payload["challenge"]["conclusion"],
        resolved=True,
        metadata={"simulation_only": True},
    )
    completeness = freeze_case_completeness(
        bundle,
        populations=(population,),
        negative_searches=(negative_search,),
        created_at="2026-09-22T16:24:10Z",
        created_by="sim-completeness-reviewer",
    )
    build = create_build_provenance_attestation(
        bundle,
        repository="P00NSMASHER/github-value-hunt-ledger",
        build_system="github-actions",
        workflow_identity="RecoveryWorks/recoveryworks",
        workflow_run_id="SIM-READINESS-BUILD-1",
        dependency_lock_hash=_sha("SIMULATED STDLIB DEPENDENCIES"),
        source_tree_hash=_sha("SIMULATED SOURCE TREE"),
        build_artifact_hash=_sha("SIMULATED BUILD ARTIFACT"),
        tests_passed=True,
        built_at=payload["calculation"]["created_at"],
        attested_at="2026-09-22T16:24:15Z",
        attested_by="sim-ci-attestor",
    )
    public_record = create_public_verification_record(
        bundle,
        packet,
        retention,
        completeness,
        build,
        journal_head_hash=ledger.journal.head_hash,
        record_id="SIM-PUBLIC-READINESS-1",
        published_at="2026-09-22T16:24:20Z",
        publisher_id="sim-recoveryworks-transparency-log",
    )
    signature = record_external_signature_verification(
        signature_id="SIM-KMS-SIGNATURE-1",
        payload_kind="recoveryworks_public_verification_record_v1",
        payload_hash=public_record.record_hash,
        provider="SIM-KMS",
        key_id="sim-kms-asymmetric-key-1",
        algorithm="RSA_PSS_SHA256",
        public_key_fingerprint=_sha("SIMULATED PUBLIC KEY"),
        signature_hash=_sha("SIMULATED RSA PSS SIGNATURE"),
        provider_request_id="SIM-KMS-VERIFY-1",
        verification_receipt_hash=_sha("SIMULATED KMS VERIFY RESPONSE"),
        signed_at="2026-09-22T16:24:25Z",
        verified_at="2026-09-22T16:24:30Z",
        verified_by_adapter="sim-kms-adapter",
        provider_verified=True,
        metadata={"simulation_only": True},
    )
    timestamp = record_external_timestamp_verification(
        timestamp_id="SIM-RFC3161-READINESS-1",
        subject_hash=signature.signature_hash,
        authority="SIM-TSA",
        standard="RFC3161",
        token_hash=_sha("SIMULATED RFC3161 TOKEN"),
        serial_number="SIM-TSA-SERIAL-READINESS-1",
        provider_request_id="SIM-TSA-VERIFY-1",
        verification_receipt_hash=_sha("SIMULATED TSA VERIFY RESPONSE"),
        timestamped_at="2026-09-22T16:24:35Z",
        verified_at="2026-09-22T16:24:40Z",
        verified_by_adapter="sim-tsa-adapter",
        provider_verified=True,
        metadata={"simulation_only": True},
    )
    lock_receipts = tuple(
        record_object_lock_verification(
            source_id=item.source_id,
            role=item.role,
            source_hash=item.source_hash,
            provider="SIM-OBJECT-STORE",
            object_version_id=f"SIM-VERSION-{index}",
            retention_control_id=item.retention_control_id,
            retention_mode=item.retention_mode,
            retain_until=item.retain_until,
            legal_hold_status="OFF",
            checked_at="2026-09-22T16:24:30Z",
            provider_request_id=f"SIM-LOCK-VERIFY-{index}",
            provider_response_hash=item.provider_attestation_hash,
            verified_by_adapter="sim-object-lock-adapter",
            provider_verified=True,
            metadata={"simulation_only": True},
        )
        for index, item in enumerate(retention.entries, start=1)
    )
    readiness = build_seven_figure_readiness(
        bundle,
        packet,
        retention,
        completeness,
        build,
        public_record,
        signature,
        timestamp,
        lock_receipts,
        journal_head_hash=ledger.journal.head_hash,
        evaluated_at="2026-09-22T16:24:50Z",
        evaluated_by="sim-readiness-controller",
    )
    dossier = build_seven_figure_authorization_dossier(
        readiness,
        packet,
        retention,
        completeness,
        build,
        public_record,
        bundle,
        journal_head_hash=ledger.journal.head_hash,
        assembled_at="2026-09-22T16:24:55Z",
        assembled_by="sim-readiness-dossier-controller",
    )
    return readiness, dossier


def _build(payload: dict):
    self_flag = payload.get("simulation_only")
    if self_flag is not True:
        raise ValueError("hostile-exam fixture must be explicitly simulation_only")

    authority_src = payload["authority_source"]
    authority_hash = _sha(authority_src["content"])
    rule = RuleRef(
        rule_id=authority_src["authority_id"],
        source_hash=authority_hash,
        effective_from=authority_src["effective_from"],
        effective_to=authority_src["effective_to"],
        verified_controlling=True,
        source_locator=authority_src["locator"],
        jurisdiction=authority_src["jurisdiction"],
        metadata={"simulation_only": True},
    )

    evidence = []
    attestations = []
    source_manifest = {"authority": authority_hash, "evidence": []}
    for src in payload["evidence_sources"]:
        source_hash = _sha(src["content"])
        source_manifest["evidence"].append({
            "evidence_id": src["evidence_id"],
            "source_hash": source_hash,
            "locator": src["locator"],
        })
        evidence.append(EvidenceRef(
            evidence_id=src["evidence_id"],
            source_hash=source_hash,
            locator=src["locator"],
            kind=src["kind"],
            verified=True,
            metadata={"simulation_only": True},
        ))
        attestations.append(SourceAttestation(
            evidence_id=src["evidence_id"],
            source_hash=source_hash,
            locator=src["locator"],
            acquisition_method=src["acquisition_method"],
            acquired_at=src["acquired_at"],
            authenticated_by=src["authenticated_by"],
            authentication_note=src["authentication_note"],
            verified_source=True,
            metadata={"simulation_only": True},
        ))

    finding_cfg = payload["finding"]
    finding = RecoveryEngine().evaluate(RecoveryObservation(
        branch=Branch(finding_cfg["branch"]),
        client_id=payload["customer"]["client_id"],
        counterparty_id=payload["customer"]["counterparty_id"],
        reference=finding_cfg["reference"],
        currency=finding_cfg["currency"],
        expected_cents=finding_cfg["expected_cents"],
        actual_cents=finding_cfg["actual_cents"],
        rule=rule,
        evidence=tuple(evidence),
        reason=finding_cfg["reason"],
        confidence_basis=finding_cfg["confidence_basis"],
        metadata={
            "simulation_only": True,
            "business_unit": payload["customer"]["business_unit"],
        },
    ))
    if finding is None:
        raise AssertionError("simulation failed to produce recovery finding")

    authority = AuthoritySnapshot(
        authority_id=authority_src["authority_id"],
        authority_kind=authority_src["authority_kind"],
        source_hash=authority_hash,
        source_locator=authority_src["locator"],
        effective_from=authority_src["effective_from"],
        effective_to=authority_src["effective_to"],
        acquired_at=authority_src["acquired_at"],
        verified_by=authority_src["verified_by"],
        verification_note=authority_src["verification_note"],
        jurisdiction=authority_src["jurisdiction"],
        metadata={"simulation_only": True},
    )

    registry = AuthorityRegistry()
    registry.register(authority)
    registry.resolve_rule(finding.rule)

    calc_cfg = payload["calculation"]
    calculation = CalculationManifest(
        calculator_id=calc_cfg["calculator_id"],
        calculator_version=calc_cfg["calculator_version"],
        code_commit_sha=calc_cfg["code_commit_sha"],
        input_manifest_hash=canonical_hash(source_manifest),
        finding_proof_hash=finding.proof_hash,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        potential_recovery_cents=finding.potential_recovery_cents,
        trace_hash=hashlib.sha256(_trace_bytes(calc_cfg["trace"])).hexdigest(),
        created_at=calc_cfg["created_at"],
        metadata={"simulation_only": True, "trace": calc_cfg["trace"]},
    )

    reviews = tuple(
        ReviewAttestation(
            review_id=item["review_id"],
            finding_proof_hash=finding.proof_hash,
            reviewer_id=item["reviewer_id"],
            reviewer_role=item["reviewer_role"],
            decision="APPROVE",
            reviewed_at=item["reviewed_at"],
            note=item["note"],
            metadata={"simulation_only": True},
        )
        for item in payload["reviews"]
    )

    ch = payload["challenge"]
    challenge_manifest_hash = _sha(ch["contrary_evidence_manifest"])
    challenge = ChallengeReview(
        challenge_id=ch["challenge_id"],
        finding_proof_hash=finding.proof_hash,
        reviewer_id=ch["reviewer_id"],
        reviewed_at=ch["reviewed_at"],
        challenge=ch["challenge"],
        conclusion=ch["conclusion"],
        resolved=True,
        contrary_evidence_hashes=(challenge_manifest_hash,),
        metadata={"simulation_only": True},
    )

    dl = payload["deadline"]
    deadline = DeadlineAssessment(
        assessment_id=dl["assessment_id"],
        finding_proof_hash=finding.proof_hash,
        governing_source_hash=authority_hash,
        source_locator=dl["source_locator"],
        trigger=dl["trigger"],
        assessed_at=dl["assessed_at"],
        assessed_by=dl["assessed_by"],
        deadline_at=dl["deadline_at"],
        conclusion=dl["conclusion"],
        metadata={"simulation_only": True},
    )

    fr = payload["freeze"]
    bundle = freeze_case_proof(
        finding=finding,
        authority=authority,
        source_attestations=tuple(attestations),
        calculation=calculation,
        reviews=reviews,
        challenges=(challenge,),
        deadlines=(deadline,),
        created_at=fr["created_at"],
        created_by=fr["created_by"],
        scan_batch_hash=canonical_hash(source_manifest),
    )

    auth_cfg = payload["client_authorization"]
    authorization = authorize_case_action(
        bundle,
        authorization_id=auth_cfg["authorization_id"],
        client_actor_id=auth_cfg["client_actor_id"],
        approved_action_type=auth_cfg["approved_action_type"],
        authorized_at=auth_cfg["authorized_at"],
        maximum_amount_cents=auth_cfg["maximum_amount_cents"],
        note=auth_cfg["note"],
        expires_at=auth_cfg["expires_at"],
    )

    action_cfg = payload["external_action"]
    artifact = action_cfg["artifact_template"].format(
        bundle_hash=bundle.bundle_hash
    ).encode("utf-8")
    envelope = prepare_external_action(
        bundle,
        authorization,
        artifact_kind=action_cfg["artifact_kind"],
        artifact_bytes=artifact,
        artifact_locator=action_cfg["artifact_locator"],
        action_amount_cents=action_cfg["action_amount_cents"],
        prepared_by=action_cfg["prepared_by"],
        prepared_at=action_cfg["prepared_at"],
    )

    ledger = DurableRecoveryLedger()
    ledger.add(finding)
    ledger.approve(
        finding.finding_id,
        reviews[0].reviewer_id,
        reviews[0].note,
    )
    ledger.independent_approve(
        finding.finding_id,
        reviews[1].reviewer_id,
        reviews[1].note,
    )
    readiness, dossier = _build_readiness(
        payload,
        bundle,
        calculation,
        ledger,
        challenge_manifest_hash,
    )
    ledger.authorize_with_case(
        finding.finding_id,
        bundle,
        authorization,
        readiness,
        dossier,
    )
    ledger.mark_claimed(finding.finding_id, envelope)

    seal_cfg = payload["seal"]
    seal = create_proof_seal(
        bundle,
        seal_id=seal_cfg["seal_id"],
        key_id=seal_cfg["key_id"],
        secret_key=SIM_SEAL_KEY,
        journal_head_hash=ledger.journal.head_hash,
        sealed_at=seal_cfg["sealed_at"],
        authorization=authorization,
        external_action=envelope,
    )
    verify_proof_seal(
        seal,
        bundle,
        secret_key=SIM_SEAL_KEY,
        journal_head_hash=ledger.journal.head_hash,
        authorization=authorization,
        external_action=envelope,
    )

    return {
        "finding": finding,
        "authority": authority,
        "registry": registry,
        "attestations": tuple(attestations),
        "calculation": calculation,
        "reviews": reviews,
        "challenge": challenge,
        "deadline": deadline,
        "bundle": bundle,
        "authorization": authorization,
        "artifact": artifact,
        "envelope": envelope,
        "ledger": ledger,
        "seal": seal,
        "readiness": readiness,
        "dossier": dossier,
    }


class SimulatedHostileExaminationTests(unittest.TestCase):
    def test_synthetic_one_million_case_survives_full_proof_lifecycle(self):
        built = _build(_load())
        finding = built["finding"]
        self.assertEqual(finding.potential_recovery_cents, 100_000_000)
        self.assertEqual(finding.metadata["simulation_only"], True)
        self.assertEqual(built["envelope"].action_amount_cents, 100_000_000)

        exported = built["ledger"].export_bundle()
        restored = DurableRecoveryLedger.from_bundle(exported)
        self.assertEqual(
            restored.journal.head_hash,
            built["ledger"].journal.head_hash,
        )
        verify_proof_seal(
            built["seal"],
            built["bundle"],
            secret_key=SIM_SEAL_KEY,
            journal_head_hash=restored.journal.head_hash,
            authorization=built["authorization"],
            external_action=built["envelope"],
        )

    def test_review_cannot_predate_inputs_or_calculation(self):
        payload = _load()
        payload["reviews"][0]["reviewed_at"] = "2026-09-22T16:04:59Z"
        with self.assertRaisesRegex(ValueError, "review cannot predate calculation"):
            _build(payload)

    def test_client_authorization_cannot_predate_frozen_case(self):
        payload = _load()
        payload["client_authorization"]["authorized_at"] = "2026-09-22T16:19:59Z"
        with self.assertRaisesRegex(ValueError, "cannot predate frozen case"):
            _build(payload)

    def test_client_authorizer_cannot_be_adversarial_reviewer(self):
        payload = _load()
        payload["client_authorization"]["client_actor_id"] = "sim-red-team-reviewer"
        with self.assertRaisesRegex(ValueError, "independent"):
            _build(payload)

    def test_external_action_cannot_predate_client_authorization(self):
        payload = _load()
        payload["external_action"]["prepared_at"] = "2026-09-22T16:24:59Z"
        with self.assertRaisesRegex(ValueError, "cannot predate client authorization"):
            _build(payload)

    def test_one_byte_outbound_change_is_detected(self):
        built = _build(_load())
        with self.assertRaisesRegex(ValueError, "artifact"):
            verify_external_action(
                built["envelope"],
                built["bundle"],
                built["authorization"],
                artifact_bytes=built["artifact"] + b"X",
            )

    def test_rehashed_action_type_change_still_fails_cross_binding(self):
        built = _build(_load())
        tampered = replace(
            built["envelope"],
            approved_action_type="different_action",
            envelope_hash="temporary",
        )
        tampered = replace(
            tampered,
            envelope_hash=canonical_hash(tampered.integrity_body()),
        )
        with self.assertRaisesRegex(ValueError, "type differs"):
            verify_external_action(
                tampered,
                built["bundle"],
                built["authorization"],
            )

    def test_rehashed_action_amount_above_validated_amount_fails(self):
        built = _build(_load())
        tampered = replace(
            built["envelope"],
            action_amount_cents=110_000_000,
            envelope_hash="temporary",
        )
        tampered = replace(
            tampered,
            envelope_hash=canonical_hash(tampered.integrity_body()),
        )
        with self.assertRaisesRegex(ValueError, "validated recovery"):
            verify_external_action(
                tampered,
                built["bundle"],
                built["authorization"],
            )

    def test_proof_seal_rejects_wrong_key_or_journal_head(self):
        built = _build(_load())
        wrong_key = b"Z" * 32
        with self.assertRaisesRegex(ValueError, "signature"):
            verify_proof_seal(
                built["seal"],
                built["bundle"],
                secret_key=wrong_key,
                journal_head_hash=built["ledger"].journal.head_hash,
                authorization=built["authorization"],
                external_action=built["envelope"],
            )
        with self.assertRaisesRegex(ValueError, "journal head"):
            verify_proof_seal(
                built["seal"],
                built["bundle"],
                secret_key=SIM_SEAL_KEY,
                journal_head_hash="tampered-journal-head",
                authorization=built["authorization"],
                external_action=built["envelope"],
            )

    def test_proof_seal_cannot_predate_external_action(self):
        payload = _load()
        payload["seal"]["sealed_at"] = "2026-09-22T16:29:59Z"
        with self.assertRaisesRegex(ValueError, "cannot predate external action"):
            _build(payload)


if __name__ == "__main__":
    unittest.main()
