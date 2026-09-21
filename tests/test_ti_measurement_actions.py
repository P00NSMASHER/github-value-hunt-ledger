"""Non-search completions cannot satisfy search strategy evidence gates."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ti_common import is_discovery_run


class DiscoveryEligibilityTests(unittest.TestCase):
    def test_explicit_actions_and_legacy_observations(self):
        for quality in ('prospective', 'benchmark'):
            self.assertTrue(is_discovery_run({'measurement_quality': quality}))
            self.assertTrue(is_discovery_run({'measurement_quality': quality, 'work_action': 'search'}))
            for action in ('execute_fixture', 'verify_artifact', 'await_external', None, 'unknown'):
                self.assertFalse(is_discovery_run({'measurement_quality': quality, 'work_action': action}))
        self.assertFalse(is_discovery_run({'measurement_quality': 'retrospective', 'work_action': 'search'}))


class MeasurementActionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='hunter-measurement-actions-')
        cls.root = Path(cls.temp.name)
        cls.intel = cls.root / 'intelligence'
        cls.intel.mkdir()
        (cls.root / 'tools').mkdir()
        scripts = ('ti_common.py', 'ti_policy.py', 'ti_report.py', 'ti_measurement_plan.py',
                   'ti_measurement_campaign.py', 'ti_saturation.py')
        for name in scripts:
            shutil.copy(ROOT / 'tools' / name, cls.root / 'tools' / name)
        cls.sid = 'STRAT:test-discovery'
        runs = []
        for index in range(4):
            run = {'search_run_id': f'RUN:search:{index}', 'strategy_id': cls.sid,
                   'measurement_quality': 'prospective', 'query_family': 'test discovery',
                   'query_family_id': 'QF:test-discovery', 'timestamp': '2026-09-01T00:00:00Z',
                   'candidate_count': 5, 'deep_inspected': 5, 'retained_count': 1,
                   'master_promoted_count': 0, 'work_action': 'search'}
            if index == 0:
                del run['work_action']  # Preserve genuine legacy observations.
            runs.append(run)
        runs.append({'search_run_id': 'RUN:fixture', 'strategy_id': cls.sid,
                     'measurement_quality': 'benchmark', 'work_action': 'execute_fixture',
                     'query_family': 'test discovery', 'query_family_id': 'QF:test-discovery',
                     'timestamp': '2026-09-02T00:00:00Z', 'benchmark_task_ids': ['01'],
                     'candidate_count': 100, 'deep_inspected': 100, 'retained_count': 100,
                     'master_promoted_count': 10})
        cls.rows('search_runs.jsonl', runs)
        cls.original_ledger = (cls.intel / 'search_runs.jsonl').read_bytes()
        cls.rows('search_strategies.jsonl', [{'strategy_id': cls.sid, 'name': 'Test', 'status': 'active'}])
        cls.rows('capabilities.jsonl', [])
        cls.rows('query_families.jsonl', [{'query_family_id': 'QF:test-discovery', 'label': 'test discovery'}])
        cls.rows('outcomes.jsonl', [{'outcome_id': 'OUT:fixture', 'origin_search_ids': ['RUN:fixture'],
                                  'result': 'PASS', 'date': '2026-09-03', 'revenue_usd': 500}])
        cls.config('attribution_metrics.json', {'by_strategy': [{'id': cls.sid,
                   'fractional_outcome_equivalents': 1, 'fractional_passed_equivalents': 1,
                   'revenue_usd_credit': 500}], 'by_query_family': [{'id': 'QF:test-discovery',
                   'fractional_outcome_equivalents': 1, 'revenue_usd_credit': 500}]})
        cls.config('strategy_evaluation_sets.json', {'sets': [{'evaluation_set_id': 'EVAL:test',
                   'strategy_ids': [cls.sid], 'task_ids': ['01']}]})
        (cls.root / 'benchmark').mkdir()
        (cls.root / 'benchmark' / 'BENCHMARK_TASKS.md').write_text('01. Synthetic independent search task.\n')
        for script in scripts[1:]:
            result = subprocess.run([sys.executable, str(cls.root / 'tools' / script)],
                                    cwd=cls.root, capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(f'{script}: {result.stdout}\n{result.stderr}')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def rows(cls, name, rows):
        (cls.intel / name).write_text(''.join(json.dumps(row) + '\n' for row in rows))

    @classmethod
    def config(cls, name, value):
        (cls.intel / name).write_text(json.dumps(value))

    def test_fixture_cannot_satisfy_strategy_or_saturation_threshold(self):
        policy = json.loads((self.intel / 'search_policy.json').read_text())
        row = policy['strategy_allocation'][0]
        self.assertEqual((row['runs'], row['inspected']), (4, 20))
        self.assertFalse(row['sufficient_evidence'])
        self.assertEqual(policy['excluded_nonsearch_or_unclassified_runs'], 1)
        debt = json.loads((self.intel / 'measurement_plan.json').read_text())['rows'][0]
        self.assertEqual(debt['runs_needed'], 1)
        self.assertFalse(debt['sufficient_evidence'])
        saturation = json.loads((self.intel / 'saturation_metrics.json').read_text())
        self.assertEqual(saturation['measured_runs'], 4)
        self.assertEqual(saturation['sufficient_neighborhoods'], 0)

    def test_fixture_outcome_credit_and_ledger_preserved(self):
        policy = json.loads((self.intel / 'search_policy.json').read_text())
        row = policy['strategy_allocation'][0]
        self.assertEqual(row['assisted_outcomes'], 1)
        self.assertEqual(row['fractional_outcome_equivalents'], 1)
        report = (self.intel / 'LEARNING_REPORT.md').read_text()
        self.assertIn('| STRAT:test-discovery | 4 | 20 |', report)
        self.assertIn('$500', report)
        self.assertEqual((self.intel / 'search_runs.jsonl').read_bytes(), self.original_ledger)

    def test_fixture_does_not_consume_a_discovery_benchmark_condition(self):
        campaign = json.loads((self.intel / 'measurement_campaign.json').read_text())
        rec = campaign['recommended_strategy_conditions']
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]['benchmark_task_id'], '01')


if __name__ == '__main__':
    unittest.main()
