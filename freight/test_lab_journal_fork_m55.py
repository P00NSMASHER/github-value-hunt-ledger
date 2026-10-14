"""M55: signed journal-state checkpoints must bind to one local file instance.

These are disposable SQLite clones and ephemeral Ed25519 review keys.
Filesystem identity is only defense-in-depth, not a remotely attested,
globally unique, nonrollbackable identity or legal customer permission.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest

from freight import backup_restore as backup
from freight.lab_replay_checkpoint_m53 import _fixture,_journal_state,NAMESPACE,AUDIENCE
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger


def _clone(source:Path,dest:Path)->None:
    with sqlite3.connect(source) as original,sqlite3.connect(dest) as target:
        original.backup(target)


class M55JournalForkBindingTests(unittest.TestCase):
    def _review(self,fx,ledger,checkpoint):
        return backup.record_checkpointed_witnessed_recovery_review(
            fx["bundle"],fx["result"],replay_ledger=ledger,
            **fx["next_review_kwargs"],
            external_checkpoint=checkpoint,
            checkpoint_custodian_trust=fx["trust"],
            checkpoint_namespace=NAMESPACE,
            checkpoint_audience=AUDIENCE,
        )

    def test_valid_checkpoint_reopens_same_original_file(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            same=TechnicalReviewReplayLedger(fx["ledger"].path)
            a=_journal_state(fx["ledger"])
            b=_journal_state(same)
            self.assertEqual(a["journal_state_sha256"],b["journal_state_sha256"])
            self.assertEqual(a["local_journal_identity_sha256"],
                             b["local_journal_identity_sha256"])
            outcome=self._review(fx,same,fx["current_checkpoint"])
            self.assertEqual(outcome["m53_successor_sequence"],2)
            self.assertFalse(outcome["real_customer_restore_activation_authorized"])

    def test_identical_rows_on_copied_file_cannot_reuse_original_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fx=_fixture(root)
            copy=root/"independent-copied-journal.sqlite3"
            _clone(fx["ledger"].path,copy)
            cloned=TechnicalReviewReplayLedger(copy)
            old=_journal_state(fx["ledger"])
            new=_journal_state(cloned)
            self.assertEqual(old["review_sequence"],new["review_sequence"])
            self.assertEqual(old["local_checkpoint_mode"],new["local_checkpoint_mode"])
            self.assertNotEqual(old["local_journal_identity_sha256"],
                                new["local_journal_identity_sha256"])
            self.assertNotEqual(old["journal_state_sha256"],
                                new["journal_state_sha256"])
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                self._review(fx,cloned,fx["current_checkpoint"])
            self.assertEqual(cloned.verify()["technical_review_rows"],1)
            self.assertEqual(fx["ledger"].verify()["technical_review_rows"],1)

    def test_same_path_replaced_by_identical_clone_fails_even_with_new_handle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fx=_fixture(root)
            original=fx["ledger"].path
            replacement=root/"replacement.sqlite3"
            _clone(original,replacement)
            os.replace(replacement,original)
            fresh=TechnicalReviewReplayLedger(original)
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                self._review(fx,fresh,fx["current_checkpoint"])
            self.assertEqual(fresh.verify()["technical_review_rows"],1)

    def test_copied_empty_journal_cannot_reuse_original_signed_initial_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fx=_fixture(root)
            empty=TechnicalReviewReplayLedger(root/"new-empty.sqlite3",create=True)
            self.assertEqual(empty.verify()["technical_review_rows"],0)
            with self.assertRaisesRegex(ValueError,"M53_CHECKPOINT_STATE_MISMATCH"):
                backup.record_checkpointed_witnessed_recovery_review(
                    fx["bundle"],fx["result"],replay_ledger=empty,
                    **fx["original_review_kwargs"],
                    external_checkpoint=fx["initial_checkpoint"],
                    checkpoint_custodian_trust=fx["trust"],
                    checkpoint_namespace=NAMESPACE,
                    checkpoint_audience=AUDIENCE,
                )
            self.assertEqual(empty.verify()["technical_review_rows"],0)

    def test_signed_state_does_not_claim_external_file_attestation(self):
        with tempfile.TemporaryDirectory() as td:
            fx=_fixture(Path(td))
            state=_journal_state(fx["ledger"])
            self.assertEqual(len(state["local_journal_identity_sha256"]),64)
            self.assertEqual(state["local_checkpoint_mode"],54)
            self.assertNotIn("externally_verified",state)
            self.assertNotIn("real_customer_approved",state)
            self.assertFalse(fx["ledger"].verify().get("customer_approval",False))


if __name__=="__main__":
    unittest.main()
