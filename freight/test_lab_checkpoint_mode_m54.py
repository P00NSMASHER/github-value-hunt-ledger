"""M54 real SQLite one-way checkpoint-mode and downgrade protection tests.

The fixture's Ed25519 custodian/reviewer keys exist IN MEMORY ONLY. No
real external trust registry, production recovery or customer consent.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from freight import backup_restore as backup
from freight import lab_checkpoint_mode_m54 as lab
from freight import recovery_mode_m54 as mode
from freight.lab_assurance import digest
from freight.lab_recovery_witness_m51 import _make_known_good
from freight.lab_recovery_replay_m52 import _new_signed_context
from freight.lab_replay_checkpoint_m53 import (
    _fixture,_journal_state,_make_anchor,NAMESPACE,AUDIENCE,
)
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger


DAY=date(2026,10,13)


class M54OneWayCheckpointModeTests(unittest.TestCase):
    def test_twelve_real_current_source_downgrades_are_typed_and_denied(self):
        self.assertEqual(len(lab.CASES),12)
        for scenario,code in lab.CASES.items():
            with self.subTest(scenario=scenario):
                row=lab.replay_one(scenario)
                self.assertEqual(row["scenario"],scenario)
                self.assertEqual(row["expected_exact_denial"],code)
                self.assertTrue(row["valid_original_signed_checkpointed_review_completed"])
                self.assertTrue(row["same_file_security_header_was_promoted_to_54"])
                self.assertTrue(row["adversarial_downgrade_or_bad_checkpoint_denied"])
                self.assertTrue(row["current_review_rows_unchanged_by_denied_attempt"])
                self.assertTrue(row["all_four_customer_backup_images_untouched"])
                self.assertIn(row["rejection_count"],(1,2))
                self.assertTrue(row[
                    "privileged_header_rewrite_cannot_be_stopped_without_external_anchor"
                ])
                self.assertFalse(row["real_external_custodian_or_bank_identity_provisioned"])
                self.assertFalse(row["production_restore_or_legal_approval_granted"])
                self.assertEqual(row["original_26_historical_findings_closed"],0)
                self.assertEqual(row["independent_customer_pilot_gates_unmet"],18)

    def test_lab14_receipt_and_human_boundaries_not_upgraded_by_fictional_signers(self):
        report=lab.run_campaign(as_of=DAY)
        self.assertEqual(report["scope"],lab.SCOPE)
        self.assertEqual(report["original_research_labs"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["original_signed_checkpointed_technical_positive_controls"],12)
        self.assertEqual(report["same_sqlite_journal_downgrade_negative_scenarios"],12)
        self.assertEqual(report["current_exact_mode_or_checkpoint_negative_denials"],13)
        self.assertTrue(report["local_only_compatibility_remains_on_never_elevated_journals"])
        self.assertTrue(report["first_signed_review_sets_durable_mode_in_same_write_transaction"])
        self.assertTrue(report["already_open_and_reopened_legacy_clients_cannot_bypass_elevated_mode"])
        self.assertTrue(report["checkpoint_mode_bound_into_independent_signed_journal_state_hash"])
        self.assertTrue(report["same_sqlite_mode_change_rollback_tested_separately"])
        self.assertTrue(report["checkpoint_security_requires_external_custody_against_full_privileged_rollback"])
        self.assertFalse(report["real_remote_checkpoint_custodian_provisioned"])
        self.assertFalse(report["real_bank_carrier_or_customer_signer_authenticated"])
        self.assertFalse(report["customer_restore_activation_performed"])
        self.assertEqual(report["original_historical_findings_open"],26)
        self.assertEqual(report["original_historical_findings_closed"],0)
        self.assertEqual(report["human_first_customer_approval_gates_unmet"],18)
        self.assertIsNone(report["real_recovered_customer_cash"])
        self.assertEqual(report["externally_publishable_empirical_claims_approved"],0)
        self.assertFalse(report["business_registered_merged_or_production_schedule_changed"])
        self.assertEqual(report["receipt_sha256"],digest({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_first_checkpointed_review_promotes_underlying_sqlite_header_and_reopens(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,reviewers,kwargs=_make_known_good(root)
            path=root/"technical-review.sqlite3"
            ledger=TechnicalReviewReplayLedger(path,create=True)
            observer=TechnicalReviewReplayLedger(path)
            self.assertEqual(lab._mode_file(path),mode.LOCAL_ONLY)
            self.assertFalse(ledger.verify()["checkpoint_required_for_future_reviews"])
            key=Ed25519PrivateKey.generate()
            trust={
                "authority_id":"M53-IN-MEMORY-ONLY-CUSTODIAN",
                "public_key_hex":key.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ).hex(),
            }
            initial=_make_anchor(
                _journal_state(ledger),key,checkpoint_id="M54-INIT-CHECKPOINT"
            )
            accepted=backup.record_checkpointed_witnessed_recovery_review(
                bundle,result,replay_ledger=ledger,**kwargs,
                external_checkpoint=initial,
                checkpoint_custodian_trust=trust,
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
            self.assertTrue(accepted["m53_prior_checkpoint_verified_under_write_lock"])
            self.assertEqual(accepted["m53_successor_sequence"],1)
            self.assertEqual(lab._mode_file(path),mode.CHECKPOINT_REQUIRED)
            self.assertTrue(observer.verify()["checkpoint_required_for_future_reviews"])
            self.assertEqual(TechnicalReviewReplayLedger(path).verify()["technical_review_rows"],1)
            new=_new_signed_context(kwargs,reviewers,"m54-after-upgrade")
            for store in (ledger,observer,TechnicalReviewReplayLedger(path)):
                with self.assertRaisesRegex(ValueError,
                        "M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE"):
                    backup.record_witnessed_recovery_review(
                        bundle,result,replay_ledger=store,**new
                    )
            self.assertEqual(ledger.verify()["technical_review_rows"],1)
            self.assertEqual(lab._mode_file(path),mode.CHECKPOINT_REQUIRED)

    def test_six_concurrent_fresh_local_only_clients_cannot_touch_checkpointed_journal(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            new=[
                _new_signed_context(
                    fx["original_review_kwargs"],fx["reviewer_private_keys"],
                    "m54-six-attempts-"+str(i)
                )
                for i in range(6)
            ]
            def attempt(kwargs):
                instance=TechnicalReviewReplayLedger(fx["ledger"].path)
                try:
                    backup.record_witnessed_recovery_review(
                        fx["bundle"],fx["result"],
                        replay_ledger=instance,**kwargs
                    )
                except ValueError as err:
                    return str(err)
                raise AssertionError("M54 accepted a local-only downgraded request")
            with ThreadPoolExecutor(max_workers=6) as pool:
                denial=list(pool.map(attempt,new))
            self.assertEqual(len(denial),6)
            self.assertTrue(all(
                "M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE" in e for e in denial
            ))
            self.assertEqual(fx["ledger"].verify()["technical_review_rows"],1)

    def test_failed_first_mode_promotion_rolls_back_review_nonce_and_header(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle,result,_,keys,original=_make_known_good(root)
            ledger=TechnicalReviewReplayLedger(root/"checkpoint-atomic.sqlite3",create=True)
            key=Ed25519PrivateKey.generate()
            trust={
                "authority_id":"M53-IN-MEMORY-ONLY-CUSTODIAN",
                "public_key_hex":key.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ).hex(),
            }
            signed=_make_anchor(
                _journal_state(ledger),key,checkpoint_id="M54-ROLLBACK-INIT"
            )
            good=dict(
                replay_ledger=ledger,**original,
                external_checkpoint=signed,
                checkpoint_custodian_trust=trust,
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
            real=mode.advance_mode
            called=[0]
            def fail_after_mode(conn,*,verified_checkpoint):
                output=real(conn,verified_checkpoint=verified_checkpoint)
                called[0]+=1
                raise RuntimeError("M54_TEST_ONLY_POST_PROMOTION_FAILURE")
            with patch.object(mode,"advance_mode",side_effect=fail_after_mode):
                with self.assertRaisesRegex(RuntimeError,
                                            "M54_TEST_ONLY_POST_PROMOTION_FAILURE"):
                    backup.record_checkpointed_witnessed_recovery_review(
                        bundle,result,**good
                    )
            self.assertEqual(called,[1])
            self.assertEqual(lab._mode_file(ledger.path),mode.LOCAL_ONLY)
            self.assertEqual(ledger.verify()["technical_review_rows"],0)
            self.assertEqual(ledger.verify()["durable_individual_witness_nonces"],0)
            # The initially signed empty header0 receipt remains valid
            # because both the request and promotion rolled back together.
            retry=backup.record_checkpointed_witnessed_recovery_review(
                bundle,result,**good
            )
            self.assertEqual(retry["m53_successor_sequence"],1)
            self.assertEqual(lab._mode_file(ledger.path),mode.CHECKPOINT_REQUIRED)

    def test_independently_signed_journal_digest_binds_persistent_security_mode(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            strict=_journal_state(fx["ledger"])
            self.assertEqual(strict["local_checkpoint_mode"],mode.CHECKPOINT_REQUIRED)
            original=deepcopy(strict)
            lab._change_header(fx["ledger"].path,0)
            lowered=_journal_state(fx["ledger"])
            self.assertEqual(lowered["local_checkpoint_mode"],mode.LOCAL_ONLY)
            self.assertEqual(strict["review_sequence"],lowered["review_sequence"])
            self.assertNotEqual(strict["journal_state_sha256"],
                                lowered["journal_state_sha256"])
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],
                    replay_ledger=fx["ledger"],**fx["next_review_kwargs"],
                    external_checkpoint=fx["current_checkpoint"],
                    checkpoint_custodian_trust=fx["trust"],
                    checkpoint_namespace=NAMESPACE,
                    checkpoint_audience=AUDIENCE,
                )

    def test_unknown_mode_fails_reopen_and_cannot_be_automatically_migrated(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            lab._change_header(fx["ledger"].path,99)
            with self.assertRaisesRegex(ValueError,
                                         "M54_REPLAY_UNKNOWN_CHECKPOINT_MODE"):
                TechnicalReviewReplayLedger(fx["ledger"].path)
            self.assertEqual(lab._mode_file_known_raw(fx["ledger"].path) if hasattr(lab,"_mode_file_known_raw") else
                             self._read_raw_mode(fx["ledger"].path),99)
            with self.assertRaisesRegex(ValueError,
                                         "M54_REPLAY_UNKNOWN_CHECKPOINT_MODE"):
                backup.record_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                    **fx["next_review_kwargs"]
                )
    @staticmethod
    def _read_raw_mode(path:Path)->int:
        with sqlite3.connect(path) as con:
            return con.execute("PRAGMA user_version").fetchone()[0]

    def test_only_never_upgraded_local_only_journal_remains_legacy_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fx=_fixture(root)
            separately_local=TechnicalReviewReplayLedger(
                root/"separate-explicit-legacy-only.sqlite3",create=True
            )
            self.assertFalse(
                separately_local.verify()["checkpoint_required_for_future_reviews"]
            )
            result=backup.record_witnessed_recovery_review(
                fx["bundle"],fx["result"],replay_ledger=separately_local,
                **fx["original_review_kwargs"]
            )
            self.assertTrue(result["review_attempt_recorded_once"])
            self.assertFalse(
                separately_local.verify()["checkpoint_required_for_future_reviews"]
            )
            self.assertEqual(separately_local.verify()["technical_review_rows"],1)
            # Even a properly signed fresh request cannot use LOCAL_ONLY
            # against the separate journal raised by a checkpointed review.
            with self.assertRaisesRegex(ValueError,
                    "M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE"):
                backup.record_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                    **fx["next_review_kwargs"]
                )

    def test_unreviewed_manual_header_reset_remains_outside_local_trust_boundary(self):
        # This demonstrates the admitted limitation: local mode header
        # cannot prevent a privileged attacker from resetting its header.
        # A real independent signed M53 checkpoint still rejects it.
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            lab._change_header(fx["ledger"].path,0)
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                    **fx["next_review_kwargs"],
                    external_checkpoint=fx["current_checkpoint"],
                    checkpoint_custodian_trust=fx["trust"],
                    checkpoint_namespace=NAMESPACE,
                    checkpoint_audience=AUDIENCE,
                )
            # The historical M52 local-only path has no externally held
            # signed state. We do not claim M54 can stop full privileged
            # mode+row rollback or a substituted brand-new journal.
            self.assertEqual(self._read_raw_mode(fx["ledger"].path),0)
            self.assertEqual(fx["ledger"].verify()["technical_review_rows"],1)

    def test_cli_no_customer_source_secrets_or_signature_bytes_published(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"derived"
            with patch("sys.argv",[
                "m54","--as-of-date","2026-10-13","--out",str(target)
            ]):
                lab.main()
            stored=json.loads((target/"checkpoint_mode_m54.json").read_text())
            self.assertEqual(stored["original_research_labs"],14)
            self.assertEqual(stored["current_exact_mode_or_checkpoint_negative_denials"],13)
            self.assertEqual(stored["original_historical_findings_closed"],0)
            self.assertTrue((target/"checkpoint_mode_m54.html").is_file())
            for item in target.iterdir():
                self.assertNotIn(item.suffix,(".db",".sqlite3"))
                contents=item.read_text()
                for sensitive in ("public_key_hex","private_key_hex",
                                  "signature_b64","BEGIN PRIVATE KEY"):
                    self.assertNotIn(sensitive,contents)
            fake=deepcopy(stored)
            fake["cases"][0]["scenario"]="<script>alert(1)</script>"
            rendered=lab.render_html(fake)
            self.assertIn("&lt;script&gt;",rendered)
            self.assertNotIn("<script>",rendered)

    def test_invalid_user_input_and_old_dates_do_not_touch_databases(self):
        for scenario in ("",None,True,1,"../other-journal.sqlite3"):
            with self.subTest(scenario=scenario),self.assertRaisesRegex(
                ValueError,"M54_UNKNOWN_CHECKPOINT_DOWNGRADE_CASE"
            ):
                lab.replay_one(scenario)
        for d in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(date=d),self.assertRaisesRegex(
                ValueError,"M54_INVALID_RESEARCH_AS_OF"
            ):
                lab.run_campaign(as_of=d)


if __name__=="__main__":
    unittest.main()
