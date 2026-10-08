"""Execute against unmodified ORIGINAL or patched OFFLINE Unified Laboratory.

Use PYTHONPATH=<archive-unpacked RecoveryOS_Unified_Development_Lab> python -m
unittest freight.phase5.test_phase5d_original_d07.  GitHub CI does not have
the original archive and MUST NOT call this an executed source test.
"""
import tempfile
import unittest
from pathlib import Path

class D07ActorReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from unified.core import load_source
            from unified.staging import StagingTwin, Rejected
        except ImportError as e:
            raise RuntimeError("Original Unified Laboratory archive required") from e
        cls.row=load_source(2)[0]
        cls.StagingTwin=StagingTwin
        cls.Rejected=Rejected
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.twin=self.StagingTwin(Path(self.temp.name)/"stage.sqlite3")
        self.twin.create(self.row,"SIM-TENANT-001","SIM-CASE-D07")
    def test_diff_allowed_actor_replay_refused(self):
        p={"message":"SIM-PAYLOAD"}
        self.twin.act("SIM-CASE-D07","SIM-TENANT-001","buyer","MESSAGE",p,idempotency="SIM-REPLAY-D07")
        with self.assertRaisesRegex(self.Rejected,"IDEMPOTENCY_CONFLICT"):
            self.twin.act("SIM-CASE-D07","SIM-TENANT-001","operator","MESSAGE",p,idempotency="SIM-REPLAY-D07")
        self.assertEqual(self.twin.view("SIM-CASE-D07","SIM-TENANT-001")["event_count"],2)
    def test_same_actor_replay_idempotent(self):
        p={"message":"SIM-PAYLOAD"}
        self.twin.act("SIM-CASE-D07","SIM-TENANT-001","buyer","MESSAGE",p,idempotency="SIM-REPLAY-D07")
        response=self.twin.act("SIM-CASE-D07","SIM-TENANT-001","buyer","MESSAGE",p,idempotency="SIM-REPLAY-D07")
        self.assertEqual(response["status"],"IDEMPOTENT_REPLAY")
        self.assertEqual(self.twin.view("SIM-CASE-D07","SIM-TENANT-001")["event_count"],2)
