"""Meaningful regressions for query/action routing and authoritative STOP gates."""
import json
import hashlib
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ti_search_actions import (action_errors, anchored_query, capability_recipe,
                               experiment_status, parse_capability_ids, transfer_recipe, load_recipe_policy)


class ActionUnitTests(unittest.TestCase):
    def test_ready_markdown_punctuation_and_scope(self):
        for value in ('**READY**.', '**READY** synthetic; **BLOCKED_EXTERNAL** commercial.', '**READY with artifact-byte gate**.'):
            self.assertEqual(experiment_status(value), 'READY')
        self.assertEqual(experiment_status('**BLOCKED_EXTERNAL**.'), 'BLOCKED_EXTERNAL')

    def test_compact_capability_membership(self):
        self.assertEqual(parse_capability_ids('CAP-002, 007, 008, 016, 019.'),
                         ['CAP-002', 'CAP-007', 'CAP-008', 'CAP-016', 'CAP-019'])
        self.assertEqual(parse_capability_ids('CAP-013, CAP-017 plus components.'), ['CAP-013', 'CAP-017'])

    def test_unknown_prose_does_not_create_a_search(self):
        recipe = capability_recipe('CAP-999')
        self.assertEqual(recipe['work_action'], 'await_external')
        self.assertEqual(recipe['blocking_reason'], 'recipe_review_required')
        self.assertEqual(recipe['query_templates'], [])
        self.assertIsNone(transfer_recipe('unknown/word-salad'))

    def test_required_domain_anchor_not_generic_signatures(self):
        self.assertFalse(anchored_query('independent adjudicate certification', ['HSMS', 'SECS/GEM']))
        self.assertFalse(anchored_query('evidence deterministic replay', ['mortgage', 'insurance']))
        self.assertFalse(anchored_query('myDICOMwrapper replay', ['DICOM']))
        self.assertTrue(anchored_query('DICOM "roundtrip" language:C++', ['DICOM']))

    def test_hard_gates_apply_to_every_seed_kind(self):
        for cid in ('CAP-014', 'CAP-015'):
            recipe = capability_recipe(cid)
            for kind in ('capability_gap', 'coverage_gap', 'learning_measurement'):
                bad = {'seed_type': kind, 'capability_ids': [cid], 'work_action': 'search',
                       'query_templates': ['HSMS engine'], 'stop_conditions': recipe['stop_conditions']}
                self.assertTrue(action_errors(bad))
            good = {'capability_ids': [cid], 'work_action': recipe['work_action'],
                    'query_templates': [], 'stop_conditions': recipe['stop_conditions']}
            self.assertEqual(action_errors(good), [])
            good['stop_conditions'] = []
            self.assertTrue(action_errors(good))

    def test_gate_reopens_only_with_reviewed_digest_bound_executed_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cid in ('CAP-014', 'CAP-015'):
                policy = copy.deepcopy(load_recipe_policy())
                plan = policy['capabilities'][cid]
                gate = plan['search_gate']
                gate['state'] = 'reopened'
                plan.update(work_action='search', query_templates=[plan['query_anchors'][0] + ' "fixtures"'],
                            next_action='Adjudicate the recorded named gap.', acceptance_target='Independent result for the frozen gap.')
                with self.assertRaises(ValueError):
                    capability_recipe(cid, policy, root)
                receipt = {'gate_id': gate['gate_id'], 'gap_id': 'GAP:observed-001', 'executed': True,
                           'result': gate['required_evidence_result'], 'next_search_question': 'Which independent implementation resolves the measured mismatch?'}
                raw = json.dumps(receipt).encode()
                (root / 'receipt.json').write_bytes(raw)
                gate['reopen_evidence'] = {'reviewed': True, 'path': 'receipt.json',
                                           'sha256': hashlib.sha256(raw).hexdigest(), 'gap_id': receipt['gap_id']}
                self.assertEqual(capability_recipe(cid, policy, root)['work_action'], 'search')
                (root / 'receipt.json').write_bytes(raw + b' ')
                with self.assertRaises(ValueError):
                    capability_recipe(cid, policy, root)
                receipt['executed'] = False
                raw = json.dumps(receipt).encode()
                (root / 'receipt.json').write_bytes(raw)
                gate['reopen_evidence']['sha256'] = hashlib.sha256(raw).hexdigest()
                with self.assertRaises(ValueError):
                    capability_recipe(cid, policy, root)

    def test_nonsearch_packet_cannot_hide_queries_in_instructions(self):
        self.assertTrue(action_errors({'work_action': 'execute_fixture', 'instructions': {'queries': ['generic discovery']}}))


class GeneratedPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='hunter-action-test-')
        cls.root = Path(cls.tmp.name)
        shutil.copytree(ROOT / 'tools', cls.root / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(
            ROOT / 'production' / 'control_plane',
            cls.root / 'production' / 'control_plane',
            ignore=shutil.ignore_patterns('__pycache__'),
        )
        (cls.root / 'intelligence').mkdir()
        for name in ('MASTER.md', 'EXPERIMENTS.md', 'SEARCH_QUEUE.md'):
            shutil.copy(ROOT / name, cls.root / name)
        inputs = ('search_policy.json', 'capabilities.jsonl', 'search_strategies.jsonl', 'search_runs.jsonl',
                  'search_objectives.json', 'exploration_gap_queue.jsonl', 'research_neighborhoods.jsonl',
                  'search_recipe_policy.json', 'allocator_policy.json', 'allocator_policy_effective.json',
                  'adjacency_queue.jsonl', 'measurement_plan.json', 'learning_curriculum.json')
        for name in inputs:
            if (ROOT / 'intelligence' / name).exists():
                shutil.copy(ROOT / 'intelligence' / name, cls.root / 'intelligence' / name)
        for script in ('ti_seed_compiler.py', 'ti_seed_validate.py', 'ti_allocator.py', 'ti_allocator_validate.py'):
            result = subprocess.run([sys.executable, str(cls.root / 'tools' / script)], cwd=cls.root,
                                    capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(f'{script}: {result.stdout}\n{result.stderr}')
        cls.seeds = cls.read('search_seeds.jsonl')
        cls.candidates = cls.read('hunt_candidates.jsonl')
        cls.allocations = cls.read('hunt_allocations.jsonl')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def read(cls, name):
        return [json.loads(line) for line in (cls.root / 'intelligence' / name).read_text().splitlines() if line]

    def test_real_experiments_survive_status_parser(self):
        exps = {c['source_id'] for c in self.candidates if c['work_kind'] == 'experiment_execution'}
        self.assertIn('EXP-008', exps)
        self.assertIn('EXP-012', exps)
        self.assertNotIn('EXP-001', exps)
        self.assertTrue(any(a['work_kind'] == 'experiment_execution' for a in self.allocations))

    def test_nonsearch_gap_actions_and_derived_gates(self):
        by_id = {s['seed_id']: s for s in self.seeds}
        self.assertEqual(by_id['SEED:gap:cap-014']['work_action'], 'execute_fixture')
        self.assertEqual(by_id['SEED:gap:cap-015']['work_action'], 'verify_artifact')
        for s in self.seeds:
            if s['work_action'] != 'search':
                self.assertEqual(s['query_templates'], [])
            if s['seed_type'] in {'coverage_gap', 'learning_measurement'}:
                parent = by_id[s['parent_seed_id']]
                self.assertEqual(parent['work_action'], 'search')
                self.assertTrue(set(parent['stop_conditions']).issubset(s['stop_conditions']))
                self.assertNotIn('CAP-014', s['capability_ids'])
                self.assertNotIn('CAP-015', s['capability_ids'])

    def test_all_search_queries_have_reviewed_anchors(self):
        for s in self.seeds:
            if s['work_action'] == 'search':
                self.assertTrue(s['query_templates'])
                for query in s['query_templates']:
                    self.assertTrue(anchored_query(query, s['query_anchors']), query)

    def test_protected_exploration_and_external_dependencies(self):
        kinds = [a['work_kind'] for a in self.allocations]
        self.assertGreaterEqual(kinds.count('coverage_gap'), 2)
        for kind in ('learning_measurement', 'wildcard', 'independent_verification'):
            self.assertIn(kind, kinds)
        self.assertNotIn('strategy_measurement', kinds)
        self.assertFalse(
            any(
                s['seed_type'] == 'strategy_measurement'
                for s in self.seeds
            )
        )
        self.assertFalse(any(a['work_action'] == 'await_external' for a in self.allocations))
        self.assertTrue(all(a['instructions'].get('acceptance_target') for a in self.allocations))

    def test_fallback_is_hypothesis_challenge_not_independent_verified(self):
        path = self.root / 'EXPERIMENTS.md'
        original = path.read_text()
        try:
            path.write_text('# No live experiments\n')
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.root / 'tools' / 'ti_allocator.py'),
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                result.stdout + result.stderr,
            )
            fallback = [
                row
                for row in self.read('hunt_candidates.jsonl')
                if row['work_kind'] == 'independent_verification'
            ]
            self.assertEqual(len(fallback), 1)
            packet = fallback[0]['instructions']
            self.assertRegex(
                fallback[0]['work_revision_sha256'],
                r'^[a-f0-9]{64}$',
            )
            self.assertEqual(
                packet['verification_mode'],
                'hypothesis_challenge',
            )
            self.assertIs(
                packet['can_establish_verified'],
                False,
            )
            self.assertEqual(packet['queries'], [])
        finally:
            path.write_text(original)
            subprocess.run(
                [
                    sys.executable,
                    str(self.root / 'tools' / 'ti_allocator.py'),
                ],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            )

    def test_exp007_stale_assignment_is_not_reissued(self):
        exp007 = [
            candidate
            for candidate in self.candidates
            if "EXP-007" in candidate.get("experiment_ids", [])
        ]
        self.assertTrue(exp007)
        stale_work_id = "WORK:verify:aec101b06ab5"
        self.assertFalse(
            any(
                candidate.get("work_item_id") == stale_work_id
                for candidate in exp007
            )
        )
        for candidate in exp007:
            next_action = (
                candidate.get("instructions") or {}
            ).get("next_action") or ""
            self.assertIn("176/232-byte", next_action)
            self.assertNotIn(
                "patch/rebuild OpenTFRaw event lookup",
                next_action,
            )

    def test_terminal_stale_semantic_work_is_suppressed(self):
        history_path = (
            self.root
            / "intelligence"
            / "execution_claim_history.jsonl"
        )
        verifier = next(
            candidate
            for candidate in self.candidates
            if (
                candidate.get("work_kind")
                == "independent_verification"
                and "EXP-007"
                in candidate.get("experiment_ids", [])
            )
        )
        stale_id = verifier["work_item_id"]
        original = (
            history_path.read_text()
            if history_path.exists()
            else None
        )
        try:
            history_path.write_text(
                json.dumps(
                    {
                        "claim_id": "CLAIM:teststale001",
                        "work_item_id": stale_id,
                        "status": "FAILED_TERMINAL",
                        "failure_code": "STALE_ASSIGNMENT",
                        "retryable": False,
                    }
                )
                + "\n"
            )
            for script in (
                "ti_allocator.py",
                "ti_allocator_validate.py",
            ):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(self.root / "tools" / script),
                    ],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stdout + result.stderr,
                )
            candidates = self.read("hunt_candidates.jsonl")
            allocations = self.read("hunt_allocations.jsonl")
            metrics = json.loads(
                (
                    self.root
                    / "intelligence"
                    / "allocator_metrics.json"
                ).read_text()
            )
            self.assertFalse(
                any(
                    row.get("work_item_id") == stale_id
                    for row in candidates
                )
            )
            self.assertFalse(
                any(
                    row.get("work_item_id") == stale_id
                    for row in allocations
                )
            )
            self.assertIn(
                stale_id,
                metrics["suppressed_stale_work_items"],
            )
        finally:
            if original is None:
                history_path.unlink(missing_ok=True)
            else:
                history_path.write_text(original)
            subprocess.run(
                [
                    sys.executable,
                    str(
                        self.root
                        / "tools"
                        / "ti_allocator.py"
                    ),
                ],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            )

    def test_versioned_work_revision_is_preserved_into_assignments(self):
        candidates = {
            row["work_item_id"]: row
            for row in self.candidates
        }
        for candidate in self.candidates:
            if candidate["work_kind"] in {
                "experiment_execution",
                "independent_verification",
            }:
                self.assertRegex(
                    candidate["work_revision_sha256"],
                    r"^[a-f0-9]{64}$",
                )
        for assignment in self.allocations:
            candidate = candidates[assignment["work_item_id"]]
            self.assertEqual(
                assignment.get("work_revision_sha256"),
                candidate.get("work_revision_sha256"),
            )
            self.assertEqual(
                assignment.get("work_identity_payload"),
                candidate.get("work_identity_payload"),
            )

    def test_semantic_identity_payload_tamper_fails_validation(self):
        candidate_path = (
            self.root
            / "intelligence"
            / "hunt_candidates.jsonl"
        )
        original = candidate_path.read_text()
        try:
            rows = self.read("hunt_candidates.jsonl")
            target = next(
                row
                for row in rows
                if row.get("work_kind")
                in {
                    "experiment_execution",
                    "independent_verification",
                }
            )
            target["work_identity_payload"][
                "next_action"
            ] = "tampered action"
            candidate_path.write_text(
                "\n".join(
                    json.dumps(row)
                    for row in rows
                )
                + "\n"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        self.root
                        / "tools"
                        / "ti_allocator_validate.py"
                    ),
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "semantic work",
                result.stdout + result.stderr,
            )
        finally:
            candidate_path.write_text(original)

    def test_learning_measurement_candidate_is_seed_bound(self):
        candidate_path = (
            self.root
            / "intelligence"
            / "hunt_candidates.jsonl"
        )
        original = candidate_path.read_text()
        try:
            rows = self.read("hunt_candidates.jsonl")
            target = next(
                row
                for row in rows
                if row.get("work_kind") == "learning_measurement"
            )
            target["query_recipe_id"] = "tampered-recipe"
            candidate_path.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        self.root
                        / "tools"
                        / "ti_allocator_validate.py"
                    ),
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "learning measurement contract mismatch",
                result.stdout + result.stderr,
            )
        finally:
            candidate_path.write_text(original)

    def test_assignment_projection_hash_binds_full_candidate_contract(self):
        candidates = {
            row["work_item_id"]: row
            for row in self.candidates
        }
        for assignment in self.allocations:
            self.assertRegex(
                assignment["candidate_projection_sha256"],
                r"^[a-f0-9]{64}$",
            )
            self.assertIn(assignment["work_item_id"], candidates)

    def test_assignment_final_score_tamper_fails_generic_projection(self):
        allocation_path = (
            self.root
            / "intelligence"
            / "hunt_allocations.jsonl"
        )
        original = allocation_path.read_text()
        try:
            rows = self.read("hunt_allocations.jsonl")
            rows[0]["final_score"] = rows[0]["final_score"] + 0.25
            allocation_path.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        self.root
                        / "tools"
                        / "ti_allocator_validate.py"
                    ),
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "protected_field_drift:final_score",
                result.stdout + result.stderr,
            )
        finally:
            allocation_path.write_text(original)

    def test_verification_uses_a_frozen_experiment_target(self):
        for c in self.candidates:
            if c['work_kind'] == 'independent_verification':
                packet = c['instructions']
                self.assertEqual(packet['verification_mode'], 'experiment_falsification')
                self.assertTrue(packet['next_action'])
                self.assertTrue(packet['independence_requirements'])
                self.assertFalse(packet.get('queries'))


if __name__ == '__main__':
    unittest.main()
