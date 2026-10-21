import hashlib
import tempfile
import unittest
from pathlib import Path
from recoveryworks.portfolio_readiness import BRANCHES, GATES, assess, render, template


class PortfolioReadinessTests(unittest.TestCase):
    def test_empty_manifest_blocks_all_seven(self):
        with tempfile.TemporaryDirectory() as directory:
            result = assess(template('client'), Path(directory))
        self.assertEqual(tuple(result['branches']), BRANCHES)
        self.assertTrue(all(r['status'] == 'BLOCKED' for r in result['branches'].values()))
        self.assertFalse(result['commercially_certified'])

    def test_review_is_bound_to_exact_local_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'evidence.txt'
            path.write_text('synthetic integrity test only')
            manifest = template('client')
            record = dict(reviewer_id='a', independent_reviewer_id='b', decision='accepted',
                          scope='test-only', reviewed_at='2026-01-01T00:00:00Z', evidence_path=path.name,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            for branch in BRANCHES:
                for gate in GATES:
                    manifest['branches'][branch][gate] = dict(record)
            result = assess(manifest, root)
            self.assertEqual(result['branches']['freight']['status'], 'REVIEW_RECORDS_COMPLETE')
            self.assertFalse(result['commercially_certified'])
            path.write_text('changed')
            self.assertEqual(assess(manifest, root)['branches']['freight']['status'], 'BLOCKED')

    def test_self_review_and_path_escape_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = template('<script>alert(1)</script>')
            manifest['branches']['ap']['authorized_scope'].update(
                reviewer_id='same', independent_reviewer_id='same', evidence_path='../outside')
            result = assess(manifest, root)
            issues = result['branches']['ap']['gates']['authorized_scope']['issues']
            self.assertIn('distinct independent reviewer missing', issues)
            self.assertNotIn('<script>', render(result))
