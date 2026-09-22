#!/usr/bin/env python3
"""Rebuild and validate the intelligence layer in one shared CI/local order.

Writes derived reports and ingests immutable submissions. Does not search, execute
candidate repositories, claim work, send messages, or publish commits.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = (
    ['tools/ti_sync.py'],  # Materialize same-commit taxonomy changes before intake.
    ['tools/ti_ingest_runs.py', '--write'],
    ['tools/ti_sync.py'],
    ['tools/ti_registry.py'],
    ['tools/ti_revision_debt.py'],
    ['tools/ti_query_families.py'],
    ['tools/ti_graph.py'],
    ['tools/ti_quality.py'],
    ['tools/ti_candidate_learning.py'],
    ['tools/ti_search_move_learning.py'],
    ['tools/ti_search_move_policy.py'],
    ['tools/ti_coordination_report.py'],
    ['tools/ti_efficiency_report.py'],
    ['tools/ti_attribution.py'],
    ['tools/ti_objectives.py'],
    ['tools/ti_report.py'],
    ['tools/ti_learning_state.py', '--write', 'intelligence/LEARNING_STATE.json'],
    ['tools/ti_learning_state_validate.py'],
    ['tools/ti_training_environment.py'],
    ['tools/ti_training_environment_validate.py'],
    ['tools/ti_repair_queue.py'],
    ['tools/ti_repair_queue_validate.py'],
    ['tools/ti_repair_candidate_intake.py'],
    ['tools/ti_repair_candidate_intake_validate.py'],
    ['tools/ti_skill_eval_result_intake.py'],
    ['tools/ti_skill_eval_result_intake_validate.py'],
    ['tools/ti_skill_promotion_result_intake.py'],
    ['tools/ti_skill_promotion_result_intake_validate.py'],
    ['tools/ti_policy.py'],
    ['tools/ti_learning_curriculum.py'],
    ['tools/ti_learning_curriculum_validate.py'],
    ['tools/ti_network_priors.py'],
    ['tools/ti_saturation.py'],
    ['tools/ti_saturation_validate.py'],
    ['tools/ti_profiles.py'],
    ['tools/ti_coverage.py'],
    ['tools/ti_coverage_validate.py'],
    ['tools/ti_seed_compiler.py'],
    ['tools/ti_seed_validate.py'],
    ['tools/ti_adjacency.py'],
    ['tools/ti_adjacency_validate.py'],
    ['tools/ti_measurement_plan.py'],
    ['tools/ti_measurement_plan_validate.py'],
    ['tools/ti_measurement_campaign.py'],
    ['tools/ti_surface.py'],
    ['tools/ti_allocator_learning.py'],
    ['tools/ti_allocator_learning_validate.py'],
    ['tools/ti_allocator.py'],
    ['tools/ti_allocator_validate.py'],
    ['tools/ti_execution.py'],
    ['tools/ti_execution_validate.py'],
    ['tools/ti_worker_profiles.py'],
    ['tools/ti_routing_learning.py'],
    ['tools/ti_routing_learning_validate.py'],
    ['tools/ti_worker_routing.py'],
    ['tools/ti_worker_routing_validate.py'],
    ['tools/ti_routing_exploration_validate.py'],
    ['tools/ti_dispatch.py'],
    ['tools/ti_dispatch_validate.py'],
    ['tools/ti_dispatch_backpressure.py'],
    ['tools/ti_dispatch_backpressure_validate.py'],
    ['tools/ti_worker_presence.py'],
    ['tools/ti_worker_presence_validate.py'],
    ['tools/ti_activation.py'],
    ['tools/ti_activation_validate.py'],
    ['tools/ti_activation_response_learning.py'],
    ['tools/ti_activation_response_validate.py'],
    ['tools/ti_validate.py'],
)


def main():
    for index, command in enumerate(STEPS, 1):
        print(f"[{index}/{len(STEPS)}] {' '.join(command)}", flush=True)
        result = subprocess.run([sys.executable, *command], cwd=ROOT)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
