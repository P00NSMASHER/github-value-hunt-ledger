from __future__ import annotations

import sys
from typing import Any, Mapping

from ti_common import ROOT

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.control_plane import (
    ProjectionContract,
    project_assignment,
    validate_assignment_projection,
)


TI_ASSIGNMENT_PROJECTION = ProjectionContract(
    name="technology-intelligence-candidate-assignment-v1",
    protected_fields=(
        "work_item_id",
        "work_revision_sha256",
        "work_identity_payload",
        "work_kind",
        "work_action",
        "query_recipe_id",
        "query_anchors",
        "required_signatures",
        "exclude_domains",
        "source_id",
        "title",
        "measurement_contract_version",
        "authorization_basis",
        "final_score",
        "score_components",
        "strategy_id",
        "search_objective_id",
        "capability_ids",
        "experiment_ids",
        "coverage_gap_ids",
        "adjacency_root",
        "instructions",
        "business_os_plan_hash",
        "business_os_work_id",
        "business_os_seed_hash",
        "business_os_initiative_key",
        "business_os_metric_key",
        "business_os_gap_type",
        "business_os_required_source_type",
    ),
    normalized_list_fields=(
        "query_anchors",
        "required_signatures",
        "exclude_domains",
        "capability_ids",
        "experiment_ids",
        "coverage_gap_ids",
    ),
    required_candidate_fields=(
        "work_item_id",
        "work_kind",
        "work_action",
        "source_id",
        "title",
        "final_score",
        "score_components",
        "instructions",
    ),
    projection_hash_field="candidate_projection_sha256",
)


def project_ti_assignment(
    candidate: Mapping[str, Any],
    assignment_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return project_assignment(
        candidate,
        assignment_metadata,
        TI_ASSIGNMENT_PROJECTION,
    )


def validate_ti_assignment_projection(
    candidate: Mapping[str, Any],
    assignment: Mapping[str, Any],
) -> None:
    validate_assignment_projection(
        candidate,
        assignment,
        TI_ASSIGNMENT_PROJECTION,
    )
