"""M51 real off-bundle Ed25519 two-witness recovery technical review tests.

All signers are fictional, generated in memory. Nothing here gives RETALLY
business authority, legal customer consent, independently attested funds, or
permission to deploy/restore a production system.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import base64
import json
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from freight import backup_restore as backup
from freight import lab_recovery_witness_m51 as lab
from freight import recovery_witness_m51 as witness
from freight.lab_assurance import digest


class M51OffBundleTechnicalRestoreReview(unittest.TestCase):
    def test_twenty_two_exact_fictional_adversarial_source_negatives(self):
        self.assertEqual(len(lab.SCENARIOS),22)
        for scenario,code in lab.SCENARIOS.items():
            with self.subTest(scenario=scenario):
                x=lab.replay_one(scenario)
                self.assertEqual(x["scenario"],scenario)
                self.assertEqual(x["expected_exact_denial"],code)
                self.assertTrue(x["two_independent_ephemeral_positive_signatures_verified"])
                self.assertTrue(x["original_m50_local_source_consistency_passed"])
                self.assertTrue(x["invalid_witness_request_rejected"])
                self.assertTrue(x["original_four_sqlite_artifacts_untouched"])
                self.assertFalse(x["private_signing_key_embedded_in_artifacts"])
                self.assertFalse(x["local_test_keys_establish_external_independent_customer_identity"])
                self.assertFalse(x["restoration_or_first_customer_activation_performed"])
                self.assertFalse(x["original_historical_finding_closed"])

    def test_aggregate_preserves_original_labs_and_human_authorization_gates(self):
        r=lab.run_campaign(as_of=date(2026,10,13))
        self.assertEqual(r["scope"],lab.SCOPE)
        self.assertEqual(r["existing_research_labs"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["ephemeral_dual_signer_positive_controls"],22)
        self.assertEqual(r["different_invalid_trust_policy_or_witness_attacks"],22)
        self.assertEqual(r["exact_current_witness_gate_denials"],22)
        self.assertTrue(r["public_keys_supplied_by_caller_not_bundle"])
        self.assertTrue(r["signatures_bound_to_manifest_scope_request_audience_expiry"])
        self.assertTrue(r["both_required_roles_must_use_distinct_public_keys"])
        self.assertTrue(r["all_keypairs_ephemeral_and_not_written_to_files"])
        self.assertTrue(r["original_m50_data_source_integrity_still_required"])
        self.assertFalse(r["actual_recovery_activation_or_customer_approval"])
        self.assertFalse(r["real_carrier_bank_or_customer_money_verified"])
        self.assertFalse(r["underlying_two_sqlite_files_acid_atomic_as_one"])
        self.assertEqual(r["all_26_original_historical_findings_open"],26)
        self.assertEqual(r["historical_original_findings_closed"],0)
        self.assertEqual(r["independent_first_customer_pilot_human_gates_unmet"],18)
        self.assertIsNone(r["actual_customer_cash_recovered"])
        self.assertEqual(r["externally_publishable_empirical_claims_approved"],0)
        self.assertTrue(r["no_production_merge_deploy_or_schedule_change"])
        self.assertEqual(r["receipt_sha256"],digest({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_good_two_signatures_are_only_technical_review_not_customer_activation(self):
        with tempfile.TemporaryDirectory() as td:
            bundle,result,manifest,keys,args=lab._make_known_good(Path(td))
            outcome=backup.verify_witnessed_recovery_bundle(bundle,result,**args)
            self.assertEqual(outcome["scope"],witness.SCOPE)
            self.assertEqual(outcome["technical_witness_count"],2)
            self.assertEqual(outcome["distinct_external_public_key_count"],2)
            self.assertEqual(set(outcome["required_roles_verified"]),set(witness.ROLES))
            self.assertTrue(outcome["manifest_and_scoped_money_referenced_by_both_signers"])
            self.assertTrue(outcome["restore_request_id_bound"])
            self.assertTrue(outcome["audience_and_expiry_checked"])
            self.assertFalse(outcome["receipt_or_private_key_written_to_disk"])
            self.assertFalse(outcome["full_customer_restore_activation_authorized"])
            self.assertFalse(outcome["real_customer_or_bank_or_carrier_consents_established"])
            self.assertEqual(outcome["independent_customer_pilot_approval_gates_still_unmet"],18)
            self.assertTrue(outcome["not_a_durable_nonce_replay_ledger"])
            self.assertTrue(backup.verify_backup_bundle(bundle,result)["manifest_sha256"])

    def test_two_distinct_keys_but_same_role_never_count_as_independent_review(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            mutated=lab._attack("DUPLICATE_ROLE_WITH_TWO_KEYS",keys,args)
            with self.assertRaisesRegex(ValueError,
                    "M51_WITNESS_DUPLICATE_ROLE_OR_SIGNER"):
                backup.verify_witnessed_recovery_bundle(path,result,**mutated)

    def test_file_corruption_is_rejected_even_when_both_valid_signatures_remain(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,args=lab._make_known_good(root)
            with (bundle/"settlement.backup.sqlite3").open("ab") as target:
                target.write(b"M51_TEST_ONLY_CORRUPTED_REAL_SOURCE_FILE")
            with self.assertRaisesRegex(ValueError,
                                         "M49_BUNDLE_SQLITE_FILE_MISSING_OR_CHANGED"):
                backup.verify_witnessed_recovery_bundle(bundle,result,**args)

    def test_signer_cannot_substitute_a_forged_valid_signature_from_own_key(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            forgery=lab._attack("FORGED_SIGNATURE_DIFFERENT_KEY",keys,args)
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_SIGNATURE_NOT_VALID"):
                backup.verify_witnessed_recovery_bundle(path,result,**forgery)

    def test_expired_even_legitimately_signed_review_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            old=lab._attack("EXPIRED_WITNESS",keys,args)
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_EXPIRED_WITNESS"):
                backup.verify_witnessed_recovery_bundle(path,result,**old)

    def test_signed_claims_do_not_authorize_a_second_restore_request(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            other={**args,"expected_restore_request_id":"M51-NEW-RESTORE-REQUEST-002"}
            with self.assertRaisesRegex(ValueError,
                                         "M51_WITNESS_RESTORE_REQUEST_REPLAY_OR_MISMATCH"):
                backup.verify_witnessed_recovery_bundle(path,result,**other)

    def test_signing_payload_rejects_human_approval_injection_and_uncanonical_times(self):
        with tempfile.TemporaryDirectory() as td:
            _,_,_,keys,args=lab._make_known_good(Path(td))
            receipt=deepcopy(args["witness_receipts"][0]["payload"])
            receipt["actual_customer_approved"]=True
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_INVALID_RECEIPT_FIELDS"):
                witness.signing_message(receipt)
            del receipt["actual_customer_approved"]
            receipt["issued_at_utc"]="2026-10-13T18:00:00+01:00"
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_BAD_TIMESTAMP"):
                witness.signing_message(receipt)

    def test_valid_signatures_at_a_future_time_expire_as_intended(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            future={**args,"as_of_utc":datetime(2026,10,13,23,0,tzinfo=timezone.utc)}
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_EXPIRED_WITNESS"):
                backup.verify_witnessed_recovery_bundle(path,result,**future)

    def test_one_missing_or_unregistered_external_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_TRUST_REGISTRY_NOT_PROVISIONED"):
                backup.verify_witnessed_recovery_bundle(
                    path,result,**{**args,"trust_registry":None})
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_MISSING_TWO_DISTINCT_WITNESSES"):
                backup.verify_witnessed_recovery_bundle(
                    path,result,**{**args,"witness_receipts":None})

    def test_bad_context_is_rejected_without_accepting_a_technical_review(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,_,keys,args=lab._make_known_good(Path(td))
            bad_contexts=[
                ("as_of_utc",None),("as_of_utc",True),("as_of_utc","2026-10-13"),
                ("expected_restore_request_id",""),
                ("expected_restore_request_id","../bad"),
                ("expected_audience",""),
            ]
            for key,invalid in bad_contexts:
                with self.subTest(key=key,value=invalid),self.assertRaisesRegex(
                    ValueError,"M51_WITNESS_INVALID_CALLER_CONTEXT"):
                    backup.verify_witnessed_recovery_bundle(
                        path,result,**{**args,key:invalid})

    def test_public_key_is_not_discovered_from_its_purported_backup_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            path,result,manifest,keys,args=lab._make_known_good(Path(td))
            marker=path/"capture.complete.json"
            modified=deepcopy(manifest)
            modified["unreviewed_public_key_claim"]="f"*64
            from freight.contracts import canonical_hash
            modified["manifest_sha256"]=canonical_hash({
                k:v for k,v in modified.items() if k!="manifest_sha256"
            })
            marker.write_text(json.dumps(modified))
            # Raw completion manifest has extra unreviewed field; local
            # hashes may be recomputed, but this can never substitute for
            # a caller-supplied independent registry.
            with self.assertRaises(ValueError):
                backup.verify_witnessed_recovery_bundle(
                    path,result,
                    **{**args,"trust_registry":None})
            self.assertNotIn("private_key",marker.read_text())

    def test_no_receipt_private_key_is_exported_as_lab_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"derived"
            from unittest.mock import patch
            with patch("sys.argv",[
                "m51","--as-of-date","2026-10-13","--out",str(out)
            ]):
                lab.main()
            report=json.loads((out/"off_bundle_witness_m51.json").read_text())
            self.assertEqual(report["exact_current_witness_gate_denials"],22)
            self.assertEqual(report["historical_original_findings_closed"],0)
            self.assertTrue((out/"off_bundle_witness_m51.html").is_file())
            for entry in out.iterdir():
                data=entry.read_text()
                self.assertNotIn("private_key_hex",data)
                self.assertNotIn("BEGIN PRIVATE KEY",data)
                self.assertNotIn("signature_b64",data)
                self.assertNotIn("public_key_hex",data)

    def test_report_escaping_and_false_real_world_claims_denied(self):
        report=lab.run_campaign(as_of=date(2026,10,13))
        changed=deepcopy(report)
        changed["cases"][0]["scenario"]="<script>alert(1)</script>"
        html=lab.render_html(changed)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("22 known-good fictional",html)
        self.assertFalse(report["actual_recovery_activation_or_customer_approval"])

    def test_invalid_attack_ids_and_research_dates_make_no_trusted_receipt(self):
        for bad in ("",None,True,5,"recovery-signature.json",
                    "../../someone-elses-private-key"):
            with self.subTest(case=bad),self.assertRaisesRegex(
                ValueError,"M51_UNKNOWN_WITNESS_TEST_CASE"):
                lab.replay_one(bad)
        for bad in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(date=bad),self.assertRaisesRegex(
                ValueError,"M51_INVALID_RESEARCH_AS_OF"):
                lab.run_campaign(as_of=bad)


if __name__=="__main__":
    unittest.main()
