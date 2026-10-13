"""RETALLY existing Lab 14 / M51 — dual off-bundle technical restore witnesses.

Every test creates one completely valid fictional M50 dual-SQLite backup and
two independent ephemeral Ed25519 keypairs in memory. A known-good positive
review is verified first. Then the exact SAME healthy data is presented with
one of twenty-two malicious/missing/replayed/local-only witness claims. Local
M50 integrity still passes; the separately required out-of-bundle technical
gate must fail closed on the precise issue.

No private keys, real customer invoices or signoff secrets are stored in the
repository, GitHub artifacts, reports or persistent scheduled automations.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import date,datetime,timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from freight import backup_restore as backup
from freight.audit_ledger import AuditEventType
from freight.lab_assurance import digest
from freight.recovery_witness_m51 import (
    PURPOSE,ROLES,SCOPE as WITNESS_SCOPE,signing_message,
)
from freight.test_backup_restore import populated


SCOPE="RETALLY_LAB14_M51_EXTERNAL_KEY_TWO_SIGNER_TECHNICAL_ONLY_SYNTHETIC"
NOW=datetime(2026,10,13,19,0,0,tzinfo=timezone.utc)
RESTORE_REQUEST="M51-RESTORE-REQUEST-001"
AUDIENCE="RETALLY-OFFLINE-RECOVERY-REVIEW"

SCENARIOS={
    "MISSING_BOTH_WITNESSES":"M51_WITNESS_MISSING_TWO_DISTINCT_WITNESSES",
    "ONLY_ONE_WITNESS":"M51_WITNESS_MISSING_TWO_DISTINCT_WITNESSES",
    "UNPROVISIONED_EXTERNAL_TRUST":"M51_WITNESS_TRUST_REGISTRY_NOT_PROVISIONED",
    "UNKNOWN_ATTESTER_KEY":"M51_WITNESS_UNKNOWN_EXTERNAL_WITNESS_KEY",
    "DUPLICATE_SIGNER_IDENTITY":"M51_WITNESS_DUPLICATE_ROLE_OR_SIGNER",
    "DUPLICATE_ROLE_WITH_TWO_KEYS":"M51_WITNESS_DUPLICATE_ROLE_OR_SIGNER",
    "REUSED_TRUSTED_PUBLIC_KEY":"M51_WITNESS_DUPLICATE_PUBLIC_KEY_ACROSS_WITNESSES",
    "FORGED_SIGNATURE_DIFFERENT_KEY":"M51_WITNESS_SIGNATURE_NOT_VALID",
    "INVALID_BASE64_SIGNATURE":"M51_WITNESS_INVALID_SIGNATURE_ENCODING",
    "OTHER_BUNDLE_MANIFEST_SHA":"M51_WITNESS_MANIFEST_OR_FINANCIAL_RECEIPT_REBOUND",
    "OTHER_FINANCIAL_RESULT_SHA":"M51_WITNESS_MANIFEST_OR_FINANCIAL_RECEIPT_REBOUND",
    "WRONG_CUSTOMER_BUYER":"M51_WITNESS_WRONG_RECOVERY_BUYER_SCOPE",
    "REPLAY_OTHER_RESTORE_REQUEST":"M51_WITNESS_RESTORE_REQUEST_REPLAY_OR_MISMATCH",
    "REPLAY_DIFFERENT_AUDIENCE":"M51_WITNESS_WITNESS_AUDIENCE_MISMATCH",
    "EXPIRED_WITNESS":"M51_WITNESS_EXPIRED_WITNESS",
    "STALE_TWENTY_FOUR_HOUR_WITNESS":"M51_WITNESS_STALE_WITNESS",
    "FUTURE_DATED_SIGNATURE":"M51_WITNESS_FUTURE_DATED_WITNESS",
    "OVERSIZED_SIGNATURE_VALIDITY":"M51_WITNESS_INVALID_WITNESS_LIFETIME",
    "REUSED_WITNESS_NONCE":"M51_WITNESS_DUPLICATE_RECEIPT_NONCE",
    "INJECTED_HUMAN_APPROVAL_FIELD":"M51_WITNESS_INVALID_RECEIPT_FIELDS",
    "SIGNER_ROLE_SUBSTITUTION":"M51_WITNESS_WITNESS_ROLE_MISMATCH",
    "UNREVIEWED_PUBLIC_KEY_FORMAT":"M51_WITNESS_TRUST_REGISTRY_INVALID",
}


def _make_known_good(root:Path):
    """Keypairs are created ONLY in memory inside disposable test fixtures."""
    audit,settlement=populated(root)
    target=root/"synthetic-complete-bundle"
    result=backup.run_backup_restore_drill(audit,settlement,work_dir=target)
    manifest=backup.verify_backup_bundle(target,result)
    names=("m51-recovery-ops","m51-independent-reviewer")
    keys=(Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate())
    registry={
        witness_id:{
            "role":role,
            "public_key_hex":private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            ).hex(),
        }
        for witness_id,role,private in zip(names,ROLES,keys)
    }
    receipts=[]
    for number,(witness_id,role,private) in enumerate(zip(names,ROLES,keys)):
        payload={
            "schema_version":1,
            "purpose":PURPOSE,
            "manifest_sha256":manifest["manifest_sha256"],
            "result_proof_sha256":result.proof_hash,
            "buyer_id":result.buyer_id,
            "business_unit":result.business_unit,
            "restore_request_id":RESTORE_REQUEST,
            "audience":AUDIENCE,
            "witness_id":witness_id,
            "role":role,
            "issued_at_utc":"2026-10-13T18:00:00Z",
            "expires_at_utc":"2026-10-13T20:00:00Z",
            "nonce_hex":sha256(("m51-ephemeral-nonce-"+str(number)).encode()).hexdigest(),
        }
        receipts.append({
            "payload":payload,
            "signature_b64":base64.b64encode(
                private.sign(signing_message(payload))
            ).decode("ascii"),
        })
    args={
        "trust_registry":registry,
        "witness_receipts":receipts,
        "expected_restore_request_id":RESTORE_REQUEST,
        "expected_audience":AUDIENCE,
        "as_of_utc":NOW,
    }
    return target,result,manifest,keys,args


def _resign(receipt:dict,key:Ed25519PrivateKey)->None:
    receipt["signature_b64"]=base64.b64encode(
        key.sign(signing_message(receipt["payload"]))
    ).decode("ascii")


def _attack(scenario:str,keys:tuple,args:dict)->dict:
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise ValueError("M51_UNKNOWN_EPHEMERAL_WITNESS_ATTACK")
    altered=deepcopy(args)
    receipts=altered["witness_receipts"]
    registry=altered["trust_registry"]
    first=receipts[0]["payload"]
    second=receipts[1]["payload"]
    if scenario=="MISSING_BOTH_WITNESSES":
        altered["witness_receipts"]=[]
    elif scenario=="ONLY_ONE_WITNESS":
        altered["witness_receipts"]=receipts[:1]
    elif scenario=="UNPROVISIONED_EXTERNAL_TRUST":
        altered["trust_registry"]={}
    elif scenario=="UNKNOWN_ATTESTER_KEY":
        first["witness_id"]="m51-unknown-attester"
        _resign(receipts[0],keys[0])
    elif scenario=="DUPLICATE_SIGNER_IDENTITY":
        receipts[1]=deepcopy(receipts[0])
    elif scenario=="DUPLICATE_ROLE_WITH_TWO_KEYS":
        second["role"]=ROLES[0]
        registry[second["witness_id"]]["role"]=ROLES[0]
        _resign(receipts[1],keys[1])
    elif scenario=="REUSED_TRUSTED_PUBLIC_KEY":
        registry[second["witness_id"]]["public_key_hex"] = (
            registry[first["witness_id"]]["public_key_hex"]
        )
    elif scenario=="FORGED_SIGNATURE_DIFFERENT_KEY":
        _resign(receipts[0],Ed25519PrivateKey.generate())
    elif scenario=="INVALID_BASE64_SIGNATURE":
        receipts[0]["signature_b64"]="**NOT-BASE64**"
    elif scenario=="OTHER_BUNDLE_MANIFEST_SHA":
        first["manifest_sha256"]="a"*64
        _resign(receipts[0],keys[0])
    elif scenario=="OTHER_FINANCIAL_RESULT_SHA":
        first["result_proof_sha256"]="c"*64
        _resign(receipts[0],keys[0])
    elif scenario=="WRONG_CUSTOMER_BUYER":
        first["buyer_id"]="M51-OTHER-CUSTOMER"
        _resign(receipts[0],keys[0])
    elif scenario=="REPLAY_OTHER_RESTORE_REQUEST":
        first["restore_request_id"]="M51-REPLAY-OTHER-REQUEST"
        _resign(receipts[0],keys[0])
    elif scenario=="REPLAY_DIFFERENT_AUDIENCE":
        first["audience"]="M51-DIFFERENT-APP"
        _resign(receipts[0],keys[0])
    elif scenario=="EXPIRED_WITNESS":
        first["expires_at_utc"]="2026-10-13T18:30:00Z"
        _resign(receipts[0],keys[0])
    elif scenario=="STALE_TWENTY_FOUR_HOUR_WITNESS":
        first["issued_at_utc"]="2026-10-11T18:00:00Z"
        _resign(receipts[0],keys[0])
    elif scenario=="FUTURE_DATED_SIGNATURE":
        first["issued_at_utc"]="2026-10-13T19:30:00Z"
        _resign(receipts[0],keys[0])
    elif scenario=="OVERSIZED_SIGNATURE_VALIDITY":
        first["expires_at_utc"]="2026-10-15T20:00:00Z"
        _resign(receipts[0],keys[0])
    elif scenario=="REUSED_WITNESS_NONCE":
        second["nonce_hex"]=first["nonce_hex"]
        _resign(receipts[1],keys[1])
    elif scenario=="INJECTED_HUMAN_APPROVAL_FIELD":
        first["real_customer_pilot_approved"]=True
        # Deliberately cannot be canonical signed by M51.
    elif scenario=="SIGNER_ROLE_SUBSTITUTION":
        second["role"]=ROLES[0]
        _resign(receipts[1],keys[1])
    elif scenario=="UNREVIEWED_PUBLIC_KEY_FORMAT":
        registry[first["witness_id"]]["public_key_hex"]="bad-not-ed25519"
    return altered


def replay_one(scenario:str)->dict:
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise ValueError("M51_UNKNOWN_WITNESS_TEST_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m51-two-signer-synthetic-") as tmp:
        root=Path(tmp)
        bundle,result,manifest,keys,kwargs=_make_known_good(root)
        positive=backup.verify_witnessed_recovery_bundle(bundle,result,**kwargs)
        if (positive["technical_witness_count"]!=2
            or positive["distinct_external_public_key_count"]!=2
            or positive["full_customer_restore_activation_authorized"] is not False
            or positive["historical_original_findings_closed"]!=0
            or positive["scope"]!=WITNESS_SCOPE):
            raise ValueError("M51_FICTIONAL_DUAL_SIGNATURE_POSITIVE_CONTROL_INVALID")
        # The old SHA-and-semantic-local check still passes on untouched
        # backup files; ONLY the new externally provisioned receipt boundary
        # is expected to catch forged/missing tech reviewer attestations.
        if backup.verify_backup_bundle(bundle,result)["manifest_sha256"]!=manifest["manifest_sha256"]:
            raise ValueError("M51_VALID_LOCAL_BUNDLE_CHANGED_UNEXPECTEDLY")
        before=[backup._file_hash(bundle/name) for name in backup._capture_files()]
        attacked=_attack(scenario,keys,kwargs)
        try:
            backup.verify_witnessed_recovery_bundle(bundle,result,**attacked)
        except ValueError as exc:
            if SCENARIOS[scenario] not in str(exc):
                raise ValueError(
                    "M51_EXACT_WITNESS_NEGATIVE_REASON_CHANGED:"+scenario
                ) from exc
        else:
            raise ValueError(
                "M51_FALSE_EXTERNAL_TECHNICAL_ATTESTATION_ACCEPTED:"+scenario
            )
        after=[backup._file_hash(bundle/name) for name in backup._capture_files()]
        if before!=after:
            raise ValueError("M51_WITNESS_VERIFICATION_MODIFIED_ORIGINAL_BACKUPS")
        return {
            "scenario":scenario,
            "expected_exact_denial":SCENARIOS[scenario],
            "two_independent_ephemeral_positive_signatures_verified":True,
            "original_m50_local_source_consistency_passed":True,
            "invalid_witness_request_rejected":True,
            "original_four_sqlite_artifacts_untouched":True,
            "private_signing_key_embedded_in_artifacts":False,
            "local_test_keys_establish_external_independent_customer_identity":False,
            "restoration_or_first_customer_activation_performed":False,
            "original_historical_finding_closed":False,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M51_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(scenario) for scenario in SCENARIOS]
    if (len(cases)!=22
        or any(
            c["expected_exact_denial"]!=SCENARIOS[c["scenario"]]
            or c["invalid_witness_request_rejected"] is not True
            or c["private_signing_key_embedded_in_artifacts"] is not False
            or c["original_historical_finding_closed"] is not False
            for c in cases
        )):
        raise ValueError("M51_OFF_BUNDLE_TECHNICAL_WITNESS_GAP_NOT_CLOSED")
    report={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_research_labs":14,
        "new_lab_created":False,
        "ephemeral_dual_signer_positive_controls":22,
        "different_invalid_trust_policy_or_witness_attacks":22,
        "exact_current_witness_gate_denials":22,
        "public_keys_supplied_by_caller_not_bundle":True,
        "signatures_bound_to_manifest_scope_request_audience_expiry":True,
        "both_required_roles_must_use_distinct_public_keys":True,
        "all_keypairs_ephemeral_and_not_written_to_files":True,
        "original_m50_data_source_integrity_still_required":True,
        "actual_recovery_activation_or_customer_approval":False,
        "real_carrier_bank_or_customer_money_verified":False,
        "underlying_two_sqlite_files_acid_atomic_as_one":False,
        "all_26_original_historical_findings_open":26,
        "historical_original_findings_closed":0,
        "independent_first_customer_pilot_human_gates_unmet":18,
        "actual_customer_cash_recovered":None,
        "externally_publishable_empirical_claims_approved":0,
        "no_production_merge_deploy_or_schedule_change":True,
        "cases":cases,
        "caveat":(
            "Only fictional ephemeral keys and two simulated technical "
            "reviewer roles were exercised. M51 never creates an actual "
            "trusted key registry, customer authorization, independent "
            "recovery witness service, durable one-time nonce store, "
            "bank/carrier source attestation or a real customer restore. "
            "Caller-supplied trusted public keys must be controlled "
            "outside the backup; arbitrary attacker-chosen keys provide "
            "NO security. Two valid technical signatures do not grant "
            "legal first-customer approval. Source data remain separately "
            "versioned SQLite without one distributed ACID transaction. "
            "All 26 historical findings and 18 human pilot gates remain open."
        ),
    }
    report["receipt_sha256"]=digest(report)
    return report


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(r["scenario"])+"</th><td>"
        +escape(r["expected_exact_denial"])+"</td>"
        "<td>TECHNICAL RESTORE REVIEW DENIED</td></tr>"
        for r in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | M51 Off-Bundle Witness Review</title>'
        '<style>body{font:15px/1.6 system-ui;color:#1d3c2d;'
        'background:#f5f8f4;max-width:1050px;margin:auto;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'th,td{text-align:left;border-bottom:1px solid #deeadc;padding:11px}'
        'small{color:#6a786b}</style></head><body>'
        '<small>RETALLY / ORIGINAL LAB 14 / M51 / SYNTHETIC ONLY</small>'
        '<h1>Off-bundle, dual-control technical restore witnesses</h1>'
        '<p>22 known-good fictional two-key signed backup controls; '
        '22 exact denials of counterfeit, expired, untrusted or mismatched '
        'technical witness receipts. Local file SHA is NOT a bank witness. '
        'No customer activation or legal first-customer approval.</p>'
        '<table><thead><tr><th>Attack</th><th>Exact denial</th>'
        '<th>Status</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Offline test-only Ed25519 witness attack lab")
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=run_campaign(as_of=a.as_of_date)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"off_bundle_witness_m51.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (a.out/"off_bundle_witness_m51.html").write_text(
        render_html(result),encoding="utf-8")
    print(json.dumps({
        "ephemeral_positive_controls":22,
        "current_exact_technical_denials":22,
        "historical_originals_closed":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
