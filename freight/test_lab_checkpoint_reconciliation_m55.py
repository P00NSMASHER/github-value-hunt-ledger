"""M55: read-only recovery of a missing independent countersignature.

All signing keys exist only in memory, and ALL SQLite files, recovery cash
and signer identities in these fixtures are fictional. No real custodian,
human first-customer authorization or original bank/carrier attestation.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight import backup_restore as backup
from freight import lab_checkpoint_reconciliation_m55 as lab
from freight import recovery_reconcile_m55 as recovery
from freight.lab_assurance import digest
from freight.lab_replay_checkpoint_m53 import (
    _fixture, _journal_state, _make_anchor, _rewrite_rows,
    AUDIENCE,NAMESPACE,
)
from freight.lab_recovery_replay_m52 import _new_signed_context
from freight.recovery_replay_m52 import (
    TechnicalReviewReplayLedger,TECHNICAL_STATUS,
)


DAY=date(2026,10,13)


class M55SignedCheckpointCrashGapTests(unittest.TestCase):
    def test_all_eighteen_rehearsals_use_actual_signed_journal_state(self):
        self.assertEqual(len(lab.SCENARIOS),18)
        for name,expected in lab.SCENARIOS.items():
            with self.subTest(name=name):
                result=lab.replay_one(name)
                self.assertEqual(result["scenario"],name)
                self.assertEqual(result["exact_expected_denial"],expected)
                self.assertTrue(result["original_signed_head_matched_in_positive_control"])
                self.assertTrue(result["honest_one_step_unsigned_successor_held_pending"])
                self.assertTrue(result["authentic_previous_checkpoint_signature_required"])
                self.assertTrue(result["source_rollback_fork_or_untrusted_signature_denied"])
                self.assertTrue(result["no_external_checkpoint_automatically_signed_or_published"])
                self.assertTrue(result["all_four_customer_recovery_files_untouched"])
                self.assertFalse(result["real_customer_restore_or_human_approval"])
                self.assertEqual(result["historical_original_findings_closed"],0)

    def test_original_lab_and_customer_permission_numbers_remain_exact(self):
        r=lab.run_campaign(as_of=DAY)
        self.assertEqual(r["scope"],lab.SCOPE)
        self.assertEqual(r["original_research_labs"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["valid_original_countersigned_head_positive_controls"],18)
        self.assertEqual(r["valid_one_commit_pending_external_countersign_controls"],18)
        self.assertEqual(r["signed_journal_or_bad_custodian_negative_scenarios"],18)
        self.assertEqual(r["current_exact_fail_closed_reconciliation_denials"],18)
        self.assertTrue(r["signed_prefix_excludes_exactly_one_review_and_two_nonces"])
        self.assertTrue(r["journal_is_inspected_read_only_in_one_sqlite_revision"])
        self.assertTrue(r["multiple_local_commits_without_custodian_signatures_rejected"])
        self.assertTrue(r["one_step_unsigned_result_must_remain_pending_not_reauthorized"])
        self.assertTrue(r["prior_signed_head_and_full_journal_mode_both_bound"])
        self.assertFalse(r["external_custodian_signs_or_stores_checkpoint_by_this_code"])
        self.assertFalse(r["independent_remote_trust_or_immutable_high_water_service_present"])
        self.assertFalse(r["actual_customer_restore_or_legally_approved"])
        self.assertEqual(r["original_historical_findings_open"],26)
        self.assertEqual(r["original_historical_findings_closed"],0)
        self.assertEqual(r["independent_first_customer_human_gates_unmet"],18)
        self.assertIsNone(r["real_customer_cash_recovered"])
        self.assertEqual(r["externally_publishable_empirical_claims_approved"],0)
        self.assertTrue(r["production_merge_registration_schedules_unchanged"])
        self.assertEqual(r["receipt_sha256"],digest({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_read_only_snapshot_matches_separately_signed_latest_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            state=lab._review(
                fx,fx["current_checkpoint"],fx["original_review_kwargs"]
            )
            self.assertEqual(state["scope"],recovery.SCOPE)
            self.assertEqual(state["state"],recovery.SIGNED_HEAD_MATCH)
            self.assertEqual(state["signed_prior_sequence"],1)
            self.assertEqual(state["current_local_sequence"],1)
            self.assertEqual(state["current_local_security_mode"],54)
            self.assertTrue(state["journal_matches_off_journal_signed_checkpoint"])
            self.assertFalse(state["pending_custodian_signature"])
            self.assertFalse(state["restore_activation_authorized"])
            self.assertFalse(state["customer_or_bank_authority_verified"])
            self.assertFalse(state["external_signing_or_persistent_checkpoint_updated"])

    def test_exact_single_committed_successor_is_held_pending_not_automatically_signed(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            outcome=lab._review(
                fx,fx["initial_checkpoint"],fx["original_review_kwargs"]
            )
            self.assertEqual(outcome["state"],recovery.ONE_UNSIGNED_SUCCESSOR)
            self.assertEqual(outcome["signed_prior_sequence"],0)
            self.assertEqual(outcome["current_local_sequence"],1)
            self.assertEqual(outcome["unique_predecessor_candidate_count"],1)
            self.assertEqual(outcome["current_local_security_mode"],54)
            self.assertTrue(outcome["one_step_successor_proven"])
            self.assertTrue(outcome["pending_custodian_signature"])
            self.assertTrue(outcome["external_custodian_must_independently_review_sign_and_persist"])
            self.assertTrue(outcome["new_review_admission_must_remain_blocked"])
            self.assertFalse(outcome["restore_activation_authorized"])
            self.assertFalse(outcome["external_signing_or_persistent_checkpoint_updated"])

    def test_original_m53_write_still_rejects_older_pending_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            before=fx["ledger"].verify()
            with self.assertRaisesRegex(ValueError,
                                         "M53_CHECKPOINT_STATE_MISMATCH"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
                    **fx["next_review_kwargs"],
                    external_checkpoint=fx["initial_checkpoint"],
                    checkpoint_custodian_trust=fx["trust"],
                    checkpoint_namespace=NAMESPACE,
                    checkpoint_audience=AUDIENCE,
                )
            self.assertEqual(fx["ledger"].verify(),before)
            self.assertEqual(lab._review(
                fx,fx["initial_checkpoint"],fx["original_review_kwargs"]
            )["state"],recovery.ONE_UNSIGNED_SUCCESSOR)

    def test_external_custodian_can_independently_sign_the_pending_state_later(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            # M55 does not sign; the test simulates a DIFFERENT custodian
            # externally countersigning after verifying the pending hold.
            pending=lab._review(
                fx,fx["initial_checkpoint"],fx["original_review_kwargs"]
            )
            self.assertTrue(pending["pending_custodian_signature"])
            independent=lab._make_anchor(
                _journal_state(fx["ledger"]),
                fx["private_custodian_key"],
                checkpoint_id="M55-TEST-EXTERNALLY-SIGNED-SEQ1",
            )
            self.assertEqual(lab._review(
                fx,independent,fx["original_review_kwargs"]
            )["state"],recovery.SIGNED_HEAD_MATCH)
            second=lab._checkpoint_review(
                fx,fx["next_review_kwargs"],independent
            )
            self.assertEqual(second["m53_successor_sequence"],2)
            self.assertFalse(second["m53_external_checkpoint_updated_by_this_operation"])
            self.assertEqual(lab._review(
                fx,independent,fx["original_review_kwargs"]
            )["state"],recovery.ONE_UNSIGNED_SUCCESSOR)

    def test_two_approved_local_review_generations_beyond_old_anchor_refused(self):
        self.assertEqual(
            lab.replay_one("OLD_SIGNED_HEAD_AFTER_TWO_SUCCESSIVE_REVIEWS")[
                "exact_expected_denial"
            ],
            "M55_RECONCILE_MULTIPLE_UNCOUNTERSIGNED_REVIEWS_OR_HISTORY_GAP",
        )

    def test_same_sequence_rewrite_detected_even_with_valid_immutable_sql_schema(self):
        self.assertEqual(
            lab.replay_one("COHERENT_SAME_SEQUENCE_REWRITE")[
                "exact_expected_denial"
            ],
            "M55_RECONCILE_SAME_SEQUENCE_JOURNAL_FORK_OR_MODE_ROLLBACK",
        )

    def test_signed_ancestor_tamper_cannot_be_hidden_by_extra_valid_local_child(self):
        self.assertEqual(
            lab.replay_one("TAMPER_SIGNED_ANCESTOR_AND_APPEND_VALID_SUCCESSOR")[
                "exact_expected_denial"
            ],
            "M55_RECONCILE_NOT_AN_EXACT_ONE_REVIEW_SIGNED_SUCCESSOR",
        )

    def test_one_alleged_coherent_successor_is_not_independent_external_approval(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            initial_signed=fx["current_checkpoint"]
            journal=fx["ledger"]
            # A privileged SQLite editor can inject one otherwise coherent
            # row + its two nonces under the existing header and triggers.
            # M55 may classify it as "candidate one-step successor" but
            # NEVER grants approval or signs the fake local entry.
            request="M55-INJECTED-NO-REAL-WITNESS"
            with sqlite3.connect(journal.path) as con:
                con.execute(
                    "INSERT INTO review_consumptions VALUES (?,?,?,?,?,?,?,?,?)",
                    (request,"a"*64,"b"*64,"FICTIONAL-OWNER","TEST-BU",
                     AUDIENCE,"2026-10-13T19:00:00Z","c"*64,TECHNICAL_STATUS),
                )
                for role_index,role in enumerate((
                    "RECOVERY_OPERATOR","INDEPENDENT_SECURITY_REVIEWER"
                )):
                    con.execute(
                        "INSERT INTO witness_nonce_consumptions "
                        "VALUES (?,?,?,?,?,?)",
                        (sha256(("m55-fake-nonce-"+str(role_index)).encode()).hexdigest(),
                         request,"m55-forged-user-"+str(role_index),role,
                         sha256(("m55-fake-key-"+str(role_index)).encode()).hexdigest(),
                         sha256(("m55-fake-signed-"+str(role_index)).encode()).hexdigest()),
                    )
            self.assertEqual(journal.verify()["technical_review_rows"],2)
            result=lab._review(fx,initial_signed,fx["original_review_kwargs"])
            self.assertEqual(result["state"],recovery.ONE_UNSIGNED_SUCCESSOR)
            self.assertFalse(result["restore_activation_authorized"])
            self.assertTrue(result["pending_custodian_signature"])
            self.assertTrue(result["new_review_admission_must_remain_blocked"])
            # Real custodian source attestation remains OUTSIDE this tool.

    def test_none_or_untrusted_ledger_never_treated_as_a_disposable_source(self):
        for invalid in (None,True,"/tmp/other.sqlite3"):
            with self.subTest(invalid=invalid),self.assertRaisesRegex(
                ValueError,"M55_RECONCILE_JOURNAL_NOT_EXPLICITLY_PROVISIONED"
            ):
                backup.inspect_signed_replay_checkpoint_reconciliation(
                    replay_ledger=invalid,
                    independently_held_checkpoint={},
                    custodian_trust={},
                    journal_namespace=NAMESPACE,
                    expected_audience=AUDIENCE,
                    as_of_utc=lab._fixture_as_of() if hasattr(lab,"_fixture_as_of") else
                        __import__("datetime").datetime(2026,10,13,19,0,0,
                          tzinfo=__import__("datetime").timezone.utc),
                )

    def test_new_local_only_journal_with_extra_unsigned_row_is_not_eligible(self):
        self.assertEqual(lab.replay_one(
            "LEGACY_LOCAL_ONLY_APPEND_NOT_RECONCILABLE")[
            "exact_expected_denial"
        ],"M55_RECONCILE_LOCAL_ONLY_UNCOUNTERSIGNED_REVIEW_NOT_ELIGIBLE")

    def test_signed_checkpoint_authority_and_audience_are_not_inferred_from_journal(self):
        for attack,reason in (
            ("MISSING_EXTERNAL_CUSTODIAN_TRUST",
             "M53_CHECKPOINT_TRUST_NOT_PROVISIONED"),
            ("UNTRUSTED_EPHEMERAL_CUSTODIAN_SIGNATURE",
             "M53_CHECKPOINT_INVALID_SIGNATURE"),
            ("SIGNED_OTHER_JOURNAL_NAMESPACE",
             "M53_CHECKPOINT_NAMESPACE_MISMATCH"),
            ("SIGNED_OTHER_AUDIENCE",
             "M53_CHECKPOINT_AUDIENCE_MISMATCH"),
        ):
            with self.subTest(attack=attack):
                self.assertEqual(lab.replay_one(attack)["exact_expected_denial"],
                                 reason)

    def test_validation_does_not_create_deleted_or_replaced_main_journal(self):
        for attack in ("DELETED_JOURNAL_FILE","REPLACED_VALID_JOURNAL_FILE",
                       "REPLACED_JOURNAL_SYMLINK"):
            with self.subTest(attack=attack):
                self.assertTrue(lab.replay_one(attack)[
                    "all_four_customer_recovery_files_untouched"
                ])

    def test_readonly_journal_and_source_receipt_when_successor_hold_is_returned(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            current=fx["ledger"].verify()
            before=[backup._file_hash(fx["bundle"]/name)
                    for name in backup._capture_files()]
            for _ in range(3):
                self.assertEqual(
                    lab._review(fx,fx["initial_checkpoint"],
                                fx["original_review_kwargs"])["state"],
                    recovery.ONE_UNSIGNED_SUCCESSOR
                )
            self.assertEqual(current,fx["ledger"].verify())
            self.assertEqual(before,[
                backup._file_hash(fx["bundle"]/name)
                for name in backup._capture_files()
            ])

    def test_research_dates_and_html_do_not_export_or_approve_customer_private_keys(self):
        for date_value in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(date=date_value),self.assertRaisesRegex(
                ValueError,"M55_INVALID_RESEARCH_AS_OF"
            ):
                lab.run_campaign(as_of=date_value)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"derived-metadata"
            with patch("sys.argv",[
                "m55","--as-of-date","2026-10-13","--out",str(out)
            ]):
                lab.main()
            report=json.loads((out/"checkpoint_reconciliation_m55.json").read_text())
            self.assertEqual(report["current_exact_fail_closed_reconciliation_denials"],18)
            self.assertEqual(report["original_historical_findings_closed"],0)
            self.assertEqual(report["independent_first_customer_human_gates_unmet"],18)
            self.assertFalse(report["actual_customer_restore_or_legally_approved"])
            self.assertTrue((out/"checkpoint_reconciliation_m55.html").is_file())
            for item in out.iterdir():
                self.assertNotIn(item.suffix,(".sqlite3",".db"))
                contents=item.read_text()
                for secret in (
                    "BEGIN PRIVATE KEY","public_key_hex","private_key_hex",
                    "signature_b64",
                ):
                    self.assertNotIn(secret,contents)
            modified=deepcopy(report)
            modified["cases"][0]["scenario"]="<script>alert(1)</script>"
            html=lab.render_html(modified)
            self.assertIn("&lt;script&gt;",html)
            self.assertNotIn("<script>",html)


if __name__=="__main__":
    unittest.main()
