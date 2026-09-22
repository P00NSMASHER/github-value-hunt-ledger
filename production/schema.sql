-- Reference PostgreSQL schema. GitHub Markdown remains the human-auditable projection.
create table if not exists intel_agent (id text primary key, lane text not null, runtime_version text, base_prompt_version text, verified_skill_set_hash text, status text not null default 'ACTIVE');
create table if not exists intel_run (id text primary key, agent_id text references intel_agent(id), parent_run_id text references intel_run(id), started_at timestamptz not null default now(), completed_at timestamptz, hypothesis text, prompt_version text, model_id text, policy_version text, tokens_in bigint default 0, tokens_out bigint default 0, llm_cost numeric default 0, search_cost numeric default 0, compute_cost numeric default 0, outcome text);
create table if not exists intel_candidate (id text primary key, canonical_uri text not null, source_type text not null, exact_revision text, capability_fingerprint text, state text not null, duplicate_of text references intel_candidate(id), sensitivity_state text not null default 'NORMAL', rights_state text);
create table if not exists intel_evidence (id text primary key, candidate_id text not null references intel_candidate(id), canonical_source text not null, exact_revision text not null, retrieved_at timestamptz not null default now(), sha256 text not null, locator text, evidence_type text not null, object_uri text, sensitivity_class text not null default 'NORMAL', redaction_state text not null default 'NONE');
create table if not exists intel_claim (id text primary key, candidate_id text not null references intel_candidate(id), proposition text not null, claim_type text not null, status text not null, confidence_class text, supporting_evidence_ids jsonb not null default '[]', contradicting_evidence_ids jsonb not null default '[]');
create table if not exists intel_verification (id text primary key, candidate_id text not null references intel_candidate(id), frozen_snapshot_hash text not null, verifier_id text not null, verifier_model text, rubric_version text not null, verdict text not null, blocking_findings jsonb not null default '[]', completed_at timestamptz not null default now());
create table if not exists intel_skill (id text not null, version text not null, name text not null, state text not null, interface_schema jsonb not null, implementation_ref text, origin_runs jsonb not null default '[]', origin_tasks jsonb not null default '[]', risk_class text, primary key (id, version));
create table if not exists intel_skill_verification (skill_id text not null, version text not null, heldout_suite_id text not null, pass_count int not null, fail_count int not null, regression_count int not null, adversarial_passed boolean not null default false, adjacent_domain_passed boolean not null default false, evidence_hash text, primary key (skill_id, version, heldout_suite_id));
create table if not exists intel_task_lease (task_id text primary key, owner text not null, generation bigint not null, acquired_at timestamptz not null, expires_at timestamptz not null, payload_hash text);
create table if not exists intel_promotion (candidate_id text primary key references intel_candidate(id), verification_id text references intel_verification(id), score jsonb not null, proposer text not null, approved_by text, decision text not null, master_commit_sha text);
create table if not exists intel_outcome (id text primary key, candidate_id text references intel_candidate(id), experiment_id text, realized_build_days numeric, realized_revenue numeric, realized_savings numeric, failed_reason text, observed_at timestamptz not null default now());

-- Outcome-weighted experience memory. Retrieval similarity remains external;
-- this table stores learned utility only.
create table if not exists intel_experience_value (
  memory_key text primary key,
  experience_kind text not null,
  q_value numeric not null default 0,
  visits bigint not null default 0,
  reward_ma numeric not null default 0,
  last_reward numeric,
  last_run_id text references intel_run(id),
  updated_at timestamptz not null default now()
);

-- Immutable reproducible hunter-system failures. Sensitive/benchmark-contaminated
-- rows remain blocked and cannot seed repair learning.
create table if not exists intel_learning_failure (
  id text primary key,
  run_id text not null references intel_run(id),
  agent_id text references intel_agent(id),
  target_type text not null,
  target_id text not null,
  failure_class text not null,
  signature_sha256 text not null,
  observation text not null,
  reproduction_steps jsonb not null default '[]',
  evidence_refs jsonb not null default '[]',
  proposed_regression_test text,
  sensitive_material_involved boolean not null default false,
  benchmark_contaminated boolean not null default false,
  status text not null default 'SUBMITTED',
  created_at timestamptz not null default now()
);

create table if not exists intel_skill_repair (
  failure_id text not null references intel_learning_failure(id),
  skill_id text not null,
  candidate_version text not null,
  diff_hash text not null,
  regression_tests_total int not null,
  regression_tests_passed int not null,
  decision_history_ref text not null,
  decision text not null,
  created_at timestamptz not null default now(),
  primary key (failure_id, skill_id, candidate_version)
);

create table if not exists intel_skill_variant_eval (
  skill_id text not null,
  baseline_version text not null,
  candidate_version text not null,
  mutate_dev_examples int not null,
  promotion_test_examples int not null,
  baseline_dev_score numeric not null,
  candidate_dev_score numeric not null,
  champion_test_score numeric not null,
  candidate_test_score numeric not null,
  hard_regressions int not null default 0,
  split_fingerprints_disjoint boolean not null default false,
  provenance_complete boolean not null default false,
  decision text not null,
  score_delta numeric not null,
  created_at timestamptz not null default now(),
  primary key (skill_id, candidate_version)
);

create table if not exists intel_skill_transfer (
  skill_id text not null,
  source_agent_id text not null,
  target_agent_id text not null,
  source_version text,
  compatibility_score numeric not null,
  target_failure_overlap numeric not null,
  decision text not null,
  evidence_refs jsonb not null default '[]',
  created_at timestamptz not null default now(),
  primary key (skill_id, source_agent_id, target_agent_id, created_at)
);

create table if not exists intel_fleet_parent_score (
  generation_id text not null,
  agent_id text not null,
  performance numeric not null,
  novelty numeric not null,
  combined_score numeric not null,
  success_vector jsonb not null,
  selected boolean not null default false,
  created_at timestamptz not null default now(),
  primary key (generation_id, agent_id)
);

create table if not exists intel_harness_mutation (
  mutation_id text primary key,
  candidate_agent_id text references intel_agent(id),
  touched_paths jsonb not null,
  allowed_paths jsonb not null,
  diff_hash text not null,
  selection_tasks int not null,
  baseline_score numeric not null,
  candidate_score numeric not null,
  regressions int not null default 0,
  decision text not null,
  created_at timestamptz not null default now()
);

create table if not exists intel_training_export (
  manifest_sha256 text primary key,
  accepted_run_ids jsonb not null default '[]',
  rejected_run_ids jsonb not null default '[]',
  created_at timestamptz not null default now()
);
