"""M52: real replay journal persistence and thread-safe restore-review tests.

Every receipt and original recovery bundle is fictional. Real customer
authorization is deliberately impossible through these interfaces.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from freight import backup_restore as backup
from freight import recovery_replay_m52 as replay
from freight import lab_recovery_replay_m52 as lab
from freight.lab_assurance import digest
from freight.lab_recovery_witness_m51 import _make_known_good


TODAY=date(2026,10,13)


class M52OneTimeTechnicalReviewTests(unittest.TestCase):
    def test_fourteen_genuine_current_sqlite_replay_and_schema_attacks_denied(self):
        self.assertEqual(len(lab.ATTACKS),14)
        for scenario,exact in lab.ATTACKS.items():
            with self.subTest(scenario=scenario):
                result=lab.replay_one(scenario)
                self.assertEqual(result["scenario"],scenario)
                self.assertEqual(result["expected_exact_denial"],exact)
                self.assertTrue(result["initial_two_key_review_recorded_technical_only"])
                self.assertTrue(result["initial_unique_request_and_two_nonces_durably_consumed"])
                self.assertTrue(result["adversarial_replay_attempt_rejected"])
                self.assertTrue(result["source_backup_and_restore_images_untouched"])
                self.assertFalse(result["production_activation_or_customer_approval"])
                self.assertTrue(result["locally_mutable_replay_journal_is_not_external_trust_anchor"])
                self.assertEqual(result["separate_original_human_pilot_approvals_unmet"],18)
                self.assertEqual(result["historical_original_findings_closed"],0)

    def test_campaign_cannot_promote_technical_journal_into_external_recovery_proof(self):
        report=lab.run_campaign(as_of=TODAY)
        self.assertEqual(report["scope"],lab.SCOPE)
        self.assertEqual(report["original_research_labs"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["synthetic_original_technical_review_positive_controls"],14)
        self.assertEqual(report["durable_review_replay_negative_scenarios"],14)
        self.assertEqual(report["exact_current_replay_and_journal_denials"],14)
        self.assertTrue(report["separate_local_review_journal_not_recovery_bundle"])
        self.assertTrue(report["global_restore_request_uniqueness_enforced"])
        self.assertTrue(report["global_witness_nonce_uniqueness_enforced"])
        self.assertTrue(report["sqlite_replay_consumptions_atomic_and_rollback_verified"])
        self.assertTrue(report["local_file_identity_and_reviewed_sql_trigger_policy_enforced"])
        self.assertFalse(report["independently_trusted_distributed_nonce_service_established"])
        self.assertFalse(report["real_customer_restore_activation_performed"])
        self.assertFalse(report["real_customer_bank_carrier_authority_verified"])
        self.assertIsNone(report["actual_customer_cash_recovered"])
        self.assertEqual(report["historical_original_findings_open"],26)
        self.assertEqual(report["historical_original_findings_closed"],0)
        self.assertEqual(report["independent_first_customer_human_controls_unmet"],18)
        self.assertEqual(report["externally_publishable_empirical_claims_approved"],0)
        self.assertFalse(report["scheduled_tasks_or_production_changed"])
        self.assertEqual(report["receipt_sha256"],digest({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_real_two_signed_reviews_consumed_at_most_once_across_reopened_clients(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            path=root/"separate-journal.sqlite3"
            first=replay.TechnicalReviewReplayLedger(path,create=True)
            outcome=backup.record_witnessed_recovery_review(
                bundle,result,replay_ledger=first,**kwargs
            )
            self.assertEqual(outcome["scope"],replay.SCOPE)
            self.assertEqual(outcome["two_ephemeral_review_nonces_consumed"],2)
            self.assertFalse(outcome["real_customer_restore_activation_authorized"])
            self.assertFalse(outcome["legal_customer_or_bank_permission_verified"])
            self.assertTrue(outcome["replay_ledger_is_locally_mutable_not_external_trust_anchor"])
            self.assertTrue(outcome["source_sqlite_bytes_modified"] is False)
            reopened=replay.TechnicalReviewReplayLedger(path)
            self.assertEqual(reopened.verify()["technical_review_rows"],1)
            self.assertEqual(reopened.verify()["durable_individual_witness_nonces"],2)
            with self.assertRaisesRegex(ValueError,"M52_REPLAY_REQUEST_ALREADY_CONSUMED"):
                backup.record_witnessed_recovery_review(
                    bundle,result,replay_ledger=reopened,**kwargs
                )
            self.assertEqual(first.verify()["technical_review_rows"],1)

    def test_new_independent_request_and_two_new_nonces_can_be_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
            backup.record_witnessed_recovery_review(
                bundle,result,replay_ledger=journal,**kwargs
            )
            new=lab._new_signed_context(kwargs,keys,"new-proper-request")
            later=backup.record_witnessed_recovery_review(
                bundle,result,replay_ledger=journal,**new
            )
            self.assertEqual(later["review_event_rows_in_journal"],2)
            self.assertEqual(journal.verify()["durable_individual_witness_nonces"],4)
            self.assertFalse(later["real_customer_restore_activation_authorized"])

    def test_concurrent_reviewers_contend_on_one_atomic_sqlite_unique_request(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            path=root/"shared-review-journal.sqlite3"
            replay.TechnicalReviewReplayLedger(path,create=True)
            def try_record(_):
                separate=replay.TechnicalReviewReplayLedger(path)
                try:
                    accepted=backup.record_witnessed_recovery_review(
                        bundle,result,replay_ledger=separate,**kwargs
                    )
                    return ("SUCCESS",accepted["review_attempt_recorded_once"])
                except ValueError as err:
                    return ("DENIED",str(err))
            with ThreadPoolExecutor(max_workers=6) as pool:
                outcomes=list(pool.map(try_record,range(6)))
            self.assertEqual(sum(x[0]=="SUCCESS" for x in outcomes),1)
            self.assertEqual(sum(x[0]=="DENIED" for x in outcomes),5)
            self.assertTrue(all("M52_REPLAY_REQUEST_ALREADY_CONSUMED" in x[1]
                                for x in outcomes if x[0]=="DENIED"))
            journal=replay.TechnicalReviewReplayLedger(path)
            self.assertEqual(journal.verify()["technical_review_rows"],1)
            self.assertEqual(journal.verify()["durable_individual_witness_nonces"],2)

    def test_post_insert_integrity_failure_rolls_back_review_and_both_nonces(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
            normal=replay._validate
            called=[0]
            def fail_after_staged_inserts(conn):
                called[0]+=1
                if called[0]==2:
                    raise RuntimeError("M52_TEST_ONLY_AFTER_INSERT_FAILURE")
                return normal(conn)
            with patch.object(replay,"_validate",side_effect=fail_after_staged_inserts):
                with self.assertRaisesRegex(RuntimeError,"M52_TEST_ONLY_AFTER_INSERT_FAILURE"):
                    backup.record_witnessed_recovery_review(
                        bundle,result,replay_ledger=journal,**kwargs
                    )
            self.assertEqual(called[0],2)
            self.assertEqual(journal.verify()["technical_review_rows"],0)
            self.assertEqual(journal.verify()["durable_individual_witness_nonces"],0)
            result2=backup.record_witnessed_recovery_review(
                bundle,result,replay_ledger=journal,**kwargs
            )
            self.assertEqual(result2["review_event_rows_in_journal"],1)

    def test_same_signer_nonce_reused_for_new_valid_restore_is_refused_globally(self):
        for role in (0,1):
            with self.subTest(role=role),tempfile.TemporaryDirectory() as td:
                root=Path(td)
                bundle,result,_,keys,kwargs=_make_known_good(root)
                journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
                backup.record_witnessed_recovery_review(
                    bundle,result,replay_ledger=journal,**kwargs
                )
                new=lab._new_signed_context(
                    kwargs,keys,"reuse-"+str(role),
                    preserve_nonce_role=role
                )
                with self.assertRaisesRegex(ValueError,"M52_REPLAY_WITNESS_NONCE_ALREADY_CONSUMED"):
                    backup.record_witnessed_recovery_review(
                        bundle,result,replay_ledger=journal,**new
                    )
                self.assertEqual(journal.verify()["technical_review_rows"],1)

    def test_bad_signature_does_not_consume_request_or_nonce_in_journal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
            invalid=deepcopy(kwargs)
            invalid["witness_receipts"][1]["signature_b64"]="bad"
            with self.assertRaisesRegex(ValueError,"M51_WITNESS_INVALID_SIGNATURE_ENCODING"):
                backup.record_witnessed_recovery_review(
                    bundle,result,replay_ledger=journal,**invalid
                )
            self.assertEqual(journal.verify()["technical_review_rows"],0)

    def test_real_bundle_tamper_is_rejected_before_any_local_replay_record(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
            with (bundle/"audit.backup.sqlite3").open("ab") as stream:
                stream.write(b"M52_TEST_ONLY_SOURCE_CORRUPTION")
            with self.assertRaisesRegex(ValueError,
                                         "M49_BUNDLE_SQLITE_FILE_MISSING_OR_CHANGED"):
                backup.record_witnessed_recovery_review(
                    bundle,result,replay_ledger=journal,**kwargs
                )
            self.assertEqual(journal.verify()["technical_review_rows"],0)

    def test_replay_journal_inside_backed_up_bundle_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            inner=replay.TechnicalReviewReplayLedger(
                bundle/"BAD-SELF-BUNDLED-JOURNAL.sqlite3",create=True
            )
            with self.assertRaisesRegex(ValueError,"M52_REPLAY_JOURNAL_MUST_BE_OFF_BUNDLE"):
                backup.record_witnessed_recovery_review(
                    bundle,result,replay_ledger=inner,**kwargs
                )
            self.assertEqual(inner.verify()["technical_review_rows"],0)

    def test_missing_journal_is_not_auto_created_by_review_or_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            file=root/"missing-separate-journal.sqlite3"
            with self.assertRaisesRegex(RuntimeError,"M47_SQLITE_SOURCE_FILE_MISSING"):
                replay.TechnicalReviewReplayLedger(file)
            self.assertFalse(file.exists())
            with self.assertRaisesRegex(ValueError,"M52_REPLAY_JOURNAL_NOT_PROVISIONED"):
                backup.record_witnessed_recovery_review(
                    bundle,result,replay_ledger=None,**kwargs
                )
            self.assertFalse(file.exists())

    def test_review_status_cannot_be_promoted_to_legal_customer_approval(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
            backup.record_witnessed_recovery_review(bundle,result,replay_ledger=journal,**kwargs)
            with sqlite3.connect(journal.path) as conn:
                self.assertEqual(conn.execute(
                    "SELECT decision FROM review_consumptions"
                ).fetchone()[0],replay.TECHNICAL_STATUS)
                with self.assertRaises(sqlite3.DatabaseError):
                    conn.execute(
                        "UPDATE review_consumptions SET decision='CUSTOMER_APPROVED'"
                    )
            self.assertFalse(journal.verify().get("legal_customer_approval",False))

    def test_broken_replay_schema_is_not_silently_repaired_on_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,kwargs=_make_known_good(root)
            journal=replay.TechnicalReviewReplayLedger(root/"journal.sqlite3",create=True)
            backup.record_witnessed_recovery_review(bundle,result,replay_ledger=journal,**kwargs)
            with sqlite3.connect(journal.path) as conn:
                conn.execute("DROP TRIGGER immutable_witness_nonce_d")
            with self.assertRaisesRegex(ValueError,"M52_REPLAY_SQLITE_REPLAY_SCHEMA_DRIFT"):
                replay.TechnicalReviewReplayLedger(journal.path)
            with sqlite3.connect(journal.path) as conn:
                present=conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='trigger' "
                    "AND name='immutable_witness_nonce_d'"
                ).fetchone()
                self.assertIsNone(present)

    def test_bad_journal_creation_race_does_not_clobber_existing_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"existing.sqlite3"
            path.write_bytes(b"DO-NOT-OVERWRITE-EXISTING-CUSTOMER-JOURNAL")
            with self.assertRaisesRegex(ValueError,"M52_REPLAY_JOURNAL_ALREADY_EXISTS"):
                replay.TechnicalReviewReplayLedger(path,create=True)
            self.assertEqual(path.read_bytes(),
                b"DO-NOT-OVERWRITE-EXISTING-CUSTOMER-JOURNAL")

    def test_invalid_research_dates_and_unknown_cases_never_modify_sources(self):
        for bad in ("",None,True,1,"../../someone-else.sqlite3"):
            with self.subTest(scenario=bad),self.assertRaisesRegex(
                ValueError,"M52_UNKNOWN_REPLAY_ADVERSARIAL_CASE"
            ):
                lab.replay_one(bad)
        for bad in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(as_of=bad),self.assertRaisesRegex(
                ValueError,"M52_INVALID_RESEARCH_AS_OF"
            ):
                lab.run_campaign(as_of=bad)

    def test_metadata_artifacts_contain_no_private_key_or_original_sqlite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            target=root/"derived"
            with patch("sys.argv",[
                "m52","--as-of-date","2026-10-13","--out",str(target)
            ]):
                lab.main()
            report=json.loads((target/"review_replay_m52.json").read_text())
            self.assertEqual(report["exact_current_replay_and_journal_denials"],14)
            self.assertEqual(report["historical_original_findings_closed"],0)
            self.assertTrue((target/"review_replay_m52.html").is_file())
            for item in target.iterdir():
                self.assertNotIn(item.suffix,(".db",".sqlite3"))
                content=item.read_text()
                for name in ("private_key_hex","public_key_hex",
                             "signature_b64","BEGIN PRIVATE KEY"):
                    self.assertNotIn(name,content)
            poisoned=deepcopy(report)
            poisoned["cases"][0]["scenario"]="<script>alert(1)</script>"
            html=lab.render_html(poisoned)
            self.assertIn("&lt;script&gt;",html)
            self.assertNotIn("<script>",html)


if __name__=="__main__":
    unittest.main()
