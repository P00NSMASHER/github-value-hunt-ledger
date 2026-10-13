"""M53: real current-source, signed off-journal rollback checkpoint tests.

Only fictional local SQLite and transient test Ed25519 keys. No real
external custodian key was provisioned, and customer restoration is never
authorized by this technical checkpoint simulation.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date,datetime,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import backup_restore as backup
from freight import lab_replay_checkpoint_m53 as lab
from freight import recovery_checkpoint_m53 as checkpoint
from freight.lab_assurance import digest
from freight.lab_recovery_replay_m52 import _new_signed_context
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger


TODAY=date(2026,10,13)


class M53SignedRollbackCheckpointTests(unittest.TestCase):
    def test_nineteen_coherent_history_and_rehashed_anchor_forgery_denials(self):
        self.assertEqual(len(lab.FAILURES),19)
        for attack,expected in lab.FAILURES.items():
            with self.subTest(attack=attack):
                result=lab.replay_one(attack)
                self.assertEqual(result["scenario"],attack)
                self.assertEqual(result["expected_exact_denial"],expected)
                self.assertTrue(result["prior_valid_signed_off_journal_positive_review"])
                self.assertTrue(result["actual_same_file_local_journal_read_and_checked"])
                self.assertTrue(result["negative_checkpoint_or_coherent_rollback_rejected"])
                self.assertTrue(result["denied_review_left_journal_state_unchanged"])
                self.assertTrue(result["original_four_sqlite_recovery_images_untouched"])
                self.assertTrue(result["one_local_checkpoint_not_a_distributed_trust_service"])
                self.assertFalse(result["independent_real_signing_custodian_provisioned"])
                self.assertEqual(result["original_historical_findings_closed"],0)
                self.assertEqual(result["human_first_customer_controls_unmet"],18)
                self.assertFalse(result["actual_customer_restore_activation"])

    def test_aggregate_keeps_26_historical_findings_and_all_18_human_gates_open(self):
        r=lab.run_campaign(as_of=TODAY)
        self.assertEqual(r["scope"],lab.SCOPE)
        self.assertEqual(r["existing_research_labs"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["synthetic_checkpointed_positive_reviews"],19)
        self.assertEqual(r["same_journal_state_or_signature_negative_scenarios"],19)
        self.assertEqual(r["exact_current_checkpoint_denials"],19)
        self.assertEqual(r["coherent_same_inode_journal_rollback_cases"],2)
        self.assertEqual(r["same_inode_coherent_row_tamper_cases"],4)
        self.assertTrue(r["checkpoint_verification_occurs_under_same_sqlite_write_lock"])
        self.assertTrue(r["independent_custodian_public_key_must_be_supplied_by_caller"])
        self.assertTrue(r["successor_checkpoint_requires_separate_external_signature"])
        self.assertFalse(r["successor_checkpoint_externally_persisted_by_this_code"])
        self.assertTrue(r["original_m50_m51_validation_still_required"])
        self.assertTrue(r["old_m52_local_only_entrypoint_still_rollback_susceptible"])
        self.assertFalse(r["externally_operated_nonrollbackable_checkpoint_service_provisioned"])
        self.assertFalse(r["two_sqlite_sources_share_one_acid_commit"])
        self.assertFalse(r["real_customer_or_carrier_signatures_or_legal_consent_verified"])
        self.assertFalse(r["real_restore_or_customer_activation_executed"])
        self.assertEqual(r["historical_original_findings_open"],26)
        self.assertEqual(r["historical_original_findings_closed"],0)
        self.assertEqual(r["human_first_customer_pilot_gates_unmet"],18)
        self.assertIsNone(r["actual_customer_cash_recovered"])
        self.assertEqual(r["externally_publishable_empirical_claims_approved"],0)
        self.assertFalse(r["production_deployment_business_registration_or_schedules_changed"])
        self.assertEqual(r["receipt_sha256"],digest({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_signed_empty_journal_checkpoint_enables_exactly_one_valid_review(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fx=lab._fixture(root)
            journal=fx["ledger"]
            self.assertEqual(journal.verify()["technical_review_rows"],1)
            result=backup.record_checkpointed_witnessed_recovery_review(
                fx["bundle"],fx["result"],replay_ledger=journal,
                **fx["next_review_kwargs"],
                external_checkpoint=fx["current_checkpoint"],
                checkpoint_custodian_trust=fx["trust"],
                checkpoint_namespace=lab.NAMESPACE,
                checkpoint_audience=lab.AUDIENCE,
            )
            self.assertTrue(result["m53_prior_checkpoint_verified_under_write_lock"])
            self.assertEqual(result["m53_signed_prior_sequence"],1)
            self.assertEqual(result["m53_successor_sequence"],2)
            self.assertTrue(result["m53_successor_requires_independent_external_signature"])
            self.assertFalse(result["m53_external_checkpoint_updated_by_this_operation"])
            self.assertFalse(result["m53_customer_activation_authorized"])
            self.assertFalse(result["real_customer_restore_activation_authorized"])
            self.assertEqual(result["m53_successor_state_sha256"],
                             lab._journal_state(journal)["journal_state_sha256"])

    def test_lost_external_checkpoint_after_local_commit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            new=fx["next_review_kwargs"]
            extra={
                "external_checkpoint":fx["current_checkpoint"],
                "checkpoint_custodian_trust":fx["trust"],
                "checkpoint_namespace":lab.NAMESPACE,
                "checkpoint_audience":lab.AUDIENCE,
            }
            first=backup.record_checkpointed_witnessed_recovery_review(
                fx["bundle"],fx["result"],
                replay_ledger=fx["ledger"],**new,**extra
            )
            later=_new_signed_context(
                fx["original_review_kwargs"],fx["reviewer_private_keys"],
                "lost-offsite-checkpoint"
            )
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],
                    replay_ledger=fx["ledger"],**later,**extra
                )
            self.assertEqual(fx["ledger"].verify()["technical_review_rows"],2)
            self.assertFalse(first["m53_external_checkpoint_updated_by_this_operation"])

    def test_new_external_custodian_signature_advances_to_new_generation(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            kwargs={
                "external_checkpoint":fx["current_checkpoint"],
                "checkpoint_custodian_trust":fx["trust"],
                "checkpoint_namespace":lab.NAMESPACE,
                "checkpoint_audience":lab.AUDIENCE,
            }
            second=backup.record_checkpointed_witnessed_recovery_review(
                fx["bundle"],fx["result"],
                replay_ledger=fx["ledger"],
                **fx["next_review_kwargs"],**kwargs
            )
            self.assertEqual(second["m53_successor_sequence"],2)
            third_signed=lab._make_anchor(
                lab._journal_state(fx["ledger"]),
                fx["private_custodian_key"],
                checkpoint_id="M53-THIRD-REVIEW-ANCHOR"
            )
            third=_new_signed_context(
                fx["original_review_kwargs"],fx["reviewer_private_keys"],
                "newly-countersigned-third"
            )
            completed=backup.record_checkpointed_witnessed_recovery_review(
                fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                **third,
                **{**kwargs,"external_checkpoint":third_signed}
            )
            self.assertEqual(completed["m53_signed_prior_sequence"],2)
            self.assertEqual(completed["m53_successor_sequence"],3)
            self.assertEqual(fx["ledger"].verify()["durable_individual_witness_nonces"],6)

    def test_original_m52_local_only_is_blocked_after_checkpoint_upgrade_but_legacy_still_risks_rollback(self):
        # M54 eliminates the ordinary local-only downgrade on a journal
        # whose first M53 checkpointed review was committed. It does NOT
        # prove a still-local-only journal is resilient to privileged SQL.
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fx=lab._fixture(root)
            journal=fx["ledger"]
            before=(journal.path.stat().st_dev,journal.path.stat().st_ino)
            lab._rewrite_rows(journal,"ROLLBACK_TO_EMPTY_SAME_INODE")
            self.assertEqual((journal.path.stat().st_dev,journal.path.stat().st_ino),before)
            self.assertEqual(journal.verify()["technical_review_rows"],0)
            self.assertTrue(journal.verify()["checkpoint_required_for_future_reviews"])
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=journal,
                    **fx["original_review_kwargs"],
                    external_checkpoint=fx["current_checkpoint"],
                    checkpoint_custodian_trust=fx["trust"],
                    checkpoint_namespace=lab.NAMESPACE,
                    checkpoint_audience=lab.AUDIENCE,
                )
            self.assertEqual(journal.verify()["technical_review_rows"],0)
            # After M54, plain M52 review ALSO cannot downgrade this
            # elevated journal; a stored checkpoint may not be omitted.
            with self.assertRaisesRegex(ValueError,
                    "M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE"):
                backup.record_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=journal,
                    **fx["original_review_kwargs"]
                )
            self.assertEqual(journal.verify()["technical_review_rows"],0)

            # The original M52 local-only creation path is deliberately
            # still supported for unchanged legacy local test journals.
            # It remains vulnerable to a privileged coherent row rewind.
            legacy=TechnicalReviewReplayLedger(root/"never-elevated.sqlite3",create=True)
            good=backup.record_witnessed_recovery_review(
                fx["bundle"],fx["result"],replay_ledger=legacy,
                **fx["original_review_kwargs"]
            )
            self.assertTrue(good["review_attempt_recorded_once"])
            self.assertFalse(legacy.verify()["checkpoint_required_for_future_reviews"])
            lab._rewrite_rows(legacy,"ROLLBACK_TO_EMPTY_SAME_INODE")
            old=backup.record_witnessed_recovery_review(
                fx["bundle"],fx["result"],replay_ledger=legacy,
                **fx["original_review_kwargs"]
            )
            self.assertTrue(old["review_attempt_recorded_once"])
            self.assertEqual(legacy.verify()["technical_review_rows"],1)

    def test_six_concurrent_independent_requests_one_old_checkpoint_only_one_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            journal_file=fx["ledger"].path
            candidates=[
                _new_signed_context(
                    fx["original_review_kwargs"],fx["reviewer_private_keys"],
                    "m53-concurrent-"+str(i),
                )
                for i in range(6)
            ]
            def contender(kwargs):
                other=TechnicalReviewReplayLedger(journal_file)
                try:
                    accepted=backup.record_checkpointed_witnessed_recovery_review(
                        fx["bundle"],fx["result"],replay_ledger=other,
                        **kwargs,
                        external_checkpoint=fx["current_checkpoint"],
                        checkpoint_custodian_trust=fx["trust"],
                        checkpoint_namespace=lab.NAMESPACE,
                        checkpoint_audience=lab.AUDIENCE,
                    )
                    return ("SUCCESS",accepted["m53_successor_sequence"])
                except ValueError as err:
                    return ("DENIED",str(err))
            with ThreadPoolExecutor(max_workers=6) as pool:
                results=list(pool.map(contender,candidates))
            self.assertEqual(sum(x[0]=="SUCCESS" for x in results),1)
            self.assertEqual(sum(x[0]=="DENIED" for x in results),5)
            self.assertTrue(all("M53_CHECKPOINT_STATE_MISMATCH" in str(x[1])
                                for x in results if x[0]=="DENIED"))
            self.assertEqual(TechnicalReviewReplayLedger(journal_file).verify()[
                "technical_review_rows"],2)

    def test_a_valid_original_bundle_and_signed_reviews_are_required_first(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            with (fx["bundle"]/"audit.backup.sqlite3").open("ab") as file:
                file.write(b"M53_TEST_ONLY_BAD_ORIGINAL")
            with self.assertRaisesRegex(ValueError,
                    "M49_BUNDLE_SQLITE_FILE_MISSING_OR_CHANGED"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],
                    replay_ledger=fx["ledger"],
                    **fx["next_review_kwargs"],
                    external_checkpoint=fx["current_checkpoint"],
                    checkpoint_custodian_trust=fx["trust"],
                    checkpoint_namespace=lab.NAMESPACE,
                    checkpoint_audience=lab.AUDIENCE,
                )
            self.assertEqual(fx["ledger"].verify()["technical_review_rows"],1)

    def test_unknown_authority_or_untrusted_public_key_cannot_be_read_from_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            for custodian in (None,{},{"public_key_hex":"f"*64}):
                with self.subTest(trust=custodian),self.assertRaisesRegex(
                    ValueError,"M53_CHECKPOINT_TRUST_NOT_PROVISIONED"):
                    backup.record_checkpointed_witnessed_recovery_review(
                        fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                        **fx["next_review_kwargs"],
                        external_checkpoint=fx["current_checkpoint"],
                        checkpoint_custodian_trust=custodian,
                        checkpoint_namespace=lab.NAMESPACE,
                        checkpoint_audience=lab.AUDIENCE,
                    )
            self.assertEqual(fx["ledger"].verify()["technical_review_rows"],1)

    def test_wrong_replay_checkpoint_audience_namespace_and_noncanonical_times(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            for change,invalid in (
                ("checkpoint_audience","../not-an-audience"),
                ("checkpoint_namespace","M"),
            ):
                with self.subTest(change=change),self.assertRaisesRegex(
                    ValueError,"M53_CHECKPOINT_INVALID_CALLER_CONTEXT"):
                    backup.record_checkpointed_witnessed_recovery_review(
                        fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                        **fx["next_review_kwargs"],
                        external_checkpoint=fx["current_checkpoint"],
                        checkpoint_custodian_trust=fx["trust"],
                        checkpoint_namespace=(
                            invalid if change=="checkpoint_namespace" else lab.NAMESPACE
                        ),
                        checkpoint_audience=(
                            invalid if change=="checkpoint_audience" else lab.AUDIENCE
                        ),
                    )
            bad=deepcopy(fx["current_checkpoint"]["payload"])
            bad["issued_at_utc"]="2026-10-13T18:00:00+01:00"
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_BAD_TIMESTAMP"):
                checkpoint.signing_message(bad)

    def test_checkpoint_payload_must_have_exact_no_business_approval_fields(self):
        with tempfile.TemporaryDirectory() as td:
            fx=lab._fixture(Path(td))
            payload=deepcopy(fx["current_checkpoint"]["payload"])
            payload["customer_permission_granted"]=True
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_INVALID_SIGNED_PAYLOAD"):
                checkpoint.signing_message(payload)
            payload.pop("customer_permission_granted")
            payload["review_sequence"]=True
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_INVALID_SIGNED_PAYLOAD"):
                checkpoint.signing_message(payload)

    def test_html_private_key_and_customer_recovery_claims_are_not_exported(self):
        result=lab.run_campaign(as_of=TODAY)
        edited=deepcopy(result)
        edited["cases"][0]["scenario"]="<script>alert(1)</script>"
        html=lab.render_html(edited)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertTrue(result["old_m52_local_only_entrypoint_still_rollback_susceptible"])
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"derived"
            with patch("sys.argv",[
                "m53","--as-of-date","2026-10-13","--out",str(dest)
            ]):
                lab.main()
            saved=json.loads((dest/"signed_replay_checkpoint_m53.json").read_text())
            self.assertEqual(saved["exact_current_checkpoint_denials"],19)
            self.assertEqual(saved["historical_original_findings_closed"],0)
            for file in dest.iterdir():
                self.assertNotIn(file.suffix,(".sqlite3",".db"))
                content=file.read_text()
                for secret in (
                    "BEGIN PRIVATE KEY","signature_b64",
                    "public_key_hex","private_key_hex",
                ):
                    self.assertNotIn(secret,content)

    def test_invalid_research_inputs_fail_without_creating_a_customer_asset(self):
        for bad in (None,True,1,"", "../fraud-db.sqlite3"):
            with self.subTest(bad=bad),self.assertRaisesRegex(
                ValueError,"M53_UNKNOWN_SIGNED_CHECKPOINT_ATTACK"):
                lab.replay_one(bad)
        for d in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(date=d),self.assertRaisesRegex(
                ValueError,"M53_INVALID_RESEARCH_AS_OF"):
                lab.run_campaign(as_of=d)


if __name__=="__main__":
    unittest.main()
