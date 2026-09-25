"""Offline checks for Step 0 handoff integrity and safe continuation."""
import hashlib
import json
import unittest
from pathlib import Path

from portfolio_prework.validate_build_state import validate_state

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads((ROOT / path).read_text())

def git_blob(path):
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

class PortfolioArchitectureBaselineTests(unittest.TestCase):
    def setUp(self):
        self.state = read('PORTFOLIO_BUILD_STATE.json')
        self.evidence = read('docs/PORTFOLIO_STEP0_EVIDENCE.json')

    def test_handoff_artifacts_match_original_blob_identities(self):
        bundle = read('portfolio_prework/ARCHITECTURE_EVIDENCE_BUNDLE.json')
        for item in bundle['source_artifacts']:
            self.assertEqual(git_blob(item['path']), item['blob_sha'], item['path'])
        for item in self.evidence['frozen_prework_files']:
            self.assertEqual(git_blob(item['path']), item['blob_sha'], item['path'])

    def test_master_cursor_does_not_inherit_prework_step_numbers(self):
        validate_state(self.state)
        self.assertEqual(self.state['completed_steps'], [0])
        self.assertEqual(self.state['current_step'], 1)
        self.assertEqual(self.state['next_action']['step'], 1)
        self.assertIn('WAIT FOR CONTINUE', self.state['next_action']['summary'])
        self.assertEqual(read('portfolio_prework/PORTFOLIO_BUILD_STATE.json')['completed_steps'], list(range(1,11)))

    def test_only_two_deltas_and_five_cached_sources(self):
        self.assertEqual({d['repo_id'] for d in self.evidence['deltas']}, {'REPO-001','REPO-003'})
        prior = read('portfolio_prework/PORTFOLIO_BUILD_STATE.json')
        for rid in self.evidence['cached_repository_ids']:
            for field in ['last_inspected_sha','last_observed_at']:
                self.assertEqual(self.state['repositories'][rid][field], prior['repositories'][rid][field])
        for d in self.evidence['deltas']:
            self.assertEqual(self.state['repositories'][d['repo_id']]['last_inspected_sha'], d['inspected_sha'])
            self.assertTrue(d['files_complete_for_compare'])
            paths = {f['path']:f for f in d['files']}
            self.assertEqual(len(paths),len(d['files']))
            for item in d['content_reads']:
                self.assertEqual(item['blob_sha'],paths[item['path']]['blob_sha'])

    def test_inventory_counts_are_additive_not_replacements(self):
        self.assertEqual(self.evidence['baseline_inventory_counts'], {'projects':12,'workflows':47,'test_paths':367,'dependency_manifests':14})
        changes=self.evidence['additive_inventory_changes']
        self.assertEqual(len(set(changes['new_test_paths'])),5)
        self.assertEqual(changes['current_mixed_snapshot_test_paths'],367+len(changes['new_test_paths']))
        self.assertEqual(changes['workflow_path_delta'],0)

    def test_state_repo_remains_blocked(self):
        self.assertIn('BLK-001',{b['blocker_id'] for b in self.state['blockers'] if b['status']=='OPEN'})
        entry=next(b for b in self.evidence['blocked_integrations'] if b['repo_id']=='REPO-006')
        self.assertFalse(entry['adapter_enabled'])
        self.assertIn('REPO-006',' '.join(self.state['next_action']['preconditions']))

    def test_all_scouts_remain_preverification(self):
        queues=self.evidence['scout_queue_summary']
        self.assertEqual({q['worker_id'] for q in queues},{f'HUNTER-{n:02d}' for n in range(1,15)})
        self.assertTrue(all(q['authority']=='PRE_VERIFICATION_DISCOVERY_ONLY' for q in queues))
        self.assertEqual(sum(q['candidate_count'] for q in queues),self.evidence['scout_queue_candidate_rows_before_deduplication'])

if __name__ == '__main__':
    unittest.main()
