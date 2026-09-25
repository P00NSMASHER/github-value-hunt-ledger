-- MIGRATION 20260924211357 create_ai_business_os_prod_brain_v1

create schema if not exists ai_business_os_prod;

revoke all on schema ai_business_os_prod from public, anon, authenticated;

alter default privileges in schema ai_business_os_prod
  revoke all on tables from public, anon, authenticated;
alter default privileges in schema ai_business_os_prod
  revoke all on sequences from public, anon, authenticated;
alter default privileges in schema ai_business_os_prod
  revoke all on functions from public, anon, authenticated;

create table if not exists ai_business_os_prod.schema_meta (
  singleton boolean primary key default true check (singleton),
  schema_version text not null,
  frozen_source_repo text not null,
  frozen_source_commit text not null,
  environment text not null check (environment in ('bootstrap','staging','production')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into ai_business_os_prod.schema_meta(
  singleton, schema_version, frozen_source_repo, frozen_source_commit, environment
)
values (
  true,
  'business-brain-v1',
  'P00NSMASHER/github-value-hunt-ledger',
  '15a5b2fdc236110dbbb56fa120483f36d3a4d28a',
  'bootstrap'
)
on conflict (singleton) do update set
  schema_version = excluded.schema_version,
  frozen_source_repo = excluded.frozen_source_repo,
  frozen_source_commit = excluded.frozen_source_commit,
  environment = excluded.environment,
  updated_at = now();

create table if not exists ai_business_os_prod.businesses (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  status text not null default 'ACTIVE'
    check (status in ('ACTIVE','PAUSED','ARCHIVED')),
  strategic_value numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.products (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  slug text not null,
  name text not null,
  lifecycle text not null default 'EXPERIMENT'
    check (lifecycle in ('IDEA','EXPERIMENT','BUILD','PILOT','LIVE','PAUSED','RETIRED')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_id, slug)
);

create table if not exists ai_business_os_prod.projects (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  external_key text,
  name text not null,
  status text not null default 'ACTIVE',
  priority integer not null default 0,
  objective text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.repositories (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references ai_business_os_prod.products(id),
  provider text not null default 'github',
  repo_full_name text not null unique,
  default_branch text,
  frozen_ref text,
  rights_status text not null default 'UNKNOWN',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.customers (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  canonical_key text not null,
  display_name text not null,
  status text not null default 'ACTIVE',
  external_ids jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_id, canonical_key)
);

create table if not exists ai_business_os_prod.prospects (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  canonical_key text not null,
  display_name text not null,
  qualification_status text not null default 'UNREVIEWED',
  source_ref text,
  external_ids jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_id, canonical_key)
);

create table if not exists ai_business_os_prod.contacts (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  customer_id uuid references ai_business_os_prod.customers(id),
  prospect_id uuid references ai_business_os_prod.prospects(id),
  full_name text,
  email text,
  role_title text,
  source_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (customer_id is not null or prospect_id is not null)
);

create table if not exists ai_business_os_prod.opportunities (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  customer_id uuid references ai_business_os_prod.customers(id),
  prospect_id uuid references ai_business_os_prod.prospects(id),
  stage text not null default 'DISCOVERED',
  expected_value_cents bigint check (expected_value_cents is null or expected_value_cents >= 0),
  currency text not null default 'USD',
  evidence_status text not null default 'UNVERIFIED',
  owner_agent_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.experiments (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  opportunity_id uuid references ai_business_os_prod.opportunities(id),
  experiment_key text not null,
  name text not null,
  hypothesis text not null,
  status text not null default 'PLANNED'
    check (status in ('PLANNED','RUNNING','PASSED','FAILED','STOPPED','INCONCLUSIVE')),
  pre_registered jsonb not null default '{}'::jsonb,
  result jsonb,
  started_at timestamptz,
  ended_at timestamptz,
  created_at timestamptz not null default now(),
  unique (business_id, experiment_key)
);

create table if not exists ai_business_os_prod.decisions (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  project_id uuid references ai_business_os_prod.projects(id),
  decision_type text not null,
  status text not null default 'RECORDED',
  decision jsonb not null,
  rationale text,
  evidence_hash text check (evidence_hash is null or evidence_hash ~ '^[0-9a-f]{64}$'),
  decided_by text not null,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.metrics (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  metric_key text not null,
  metric_value numeric not null,
  unit text not null,
  observed_at timestamptz not null,
  source_ref text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.financial_events (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references ai_business_os_prod.businesses(id),
  opportunity_id uuid references ai_business_os_prod.opportunities(id),
  event_type text not null,
  amount_cents bigint not null,
  currency text not null default 'USD',
  occurred_at timestamptz not null,
  source_ref text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.agent_runs (
  id uuid primary key default gen_random_uuid(),
  agent_id text not null,
  role text not null,
  goal_id text,
  status text not null,
  started_at timestamptz not null,
  ended_at timestamptz,
  cost_units numeric not null default 0 check (cost_units >= 0),
  input_hash text check (input_hash is null or input_hash ~ '^[0-9a-f]{64}$'),
  output_hash text check (output_hash is null or output_hash ~ '^[0-9a-f]{64}$'),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.evidence (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  evidence_type text not null,
  authority_type text not null,
  source_ref text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  observed_at timestamptz not null,
  valid_until timestamptz,
  admissible boolean not null default true,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (valid_until is null or valid_until >= observed_at)
);

create table if not exists ai_business_os_prod.truth_claims (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  claim_key text not null,
  subject text not null,
  statement text not null,
  verdict text not null default 'UNKNOWN'
    check (verdict in ('PROVEN','CONTESTED','NOT_PROVEN','UNKNOWN')),
  claim_hash text not null check (claim_hash ~ '^[0-9a-f]{64}$'),
  evidence_set_hash text check (evidence_set_hash is null or evidence_set_hash ~ '^[0-9a-f]{64}$'),
  evaluated_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (business_id, claim_key)
);

create table if not exists ai_business_os_prod.truth_evidence (
  claim_id uuid not null references ai_business_os_prod.truth_claims(id),
  evidence_id uuid not null references ai_business_os_prod.evidence(id),
  obligation_key text not null,
  stance text not null check (stance in ('SUPPORTS','CONTRADICTS')),
  independence_group text not null,
  primary key (claim_id, evidence_id, obligation_key)
);

create table if not exists ai_business_os_prod.alerts (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  severity text not null default 'INFO'
    check (severity in ('INFO','LOW','MEDIUM','HIGH','CRITICAL')),
  alert_type text not null,
  title text not null,
  body jsonb not null default '{}'::jsonb,
  status text not null default 'OPEN',
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table if not exists ai_business_os_prod.approvals (
  id uuid primary key default gen_random_uuid(),
  agent_id text not null,
  action_key text not null,
  action_class text not null,
  intent_hash text not null unique check (intent_hash ~ '^[0-9a-f]{64}$'),
  status text not null,
  approver_principal text,
  approval_receipt_hash text check (
    approval_receipt_hash is null or approval_receipt_hash ~ '^[0-9a-f]{64}$'
  ),
  expires_at timestamptz,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.deployments (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  repository_id uuid references ai_business_os_prod.repositories(id),
  environment text not null,
  revision text not null,
  status text not null,
  authorization_receipt_hash text check (
    authorization_receipt_hash is null or authorization_receipt_hash ~ '^[0-9a-f]{64}$'
  ),
  deployed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.incidents (
  id uuid primary key default gen_random_uuid(),
  business_id uuid references ai_business_os_prod.businesses(id),
  severity text not null,
  status text not null default 'OPEN',
  title text not null,
  description text,
  source_ref text,
  opened_at timestamptz not null default now(),
  resolved_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists ai_business_os_prod.knowledge_nodes (
  id uuid primary key default gen_random_uuid(),
  node_type text not null,
  canonical_key text not null,
  label text not null,
  provenance_hash text not null check (provenance_hash ~ '^[0-9a-f]{64}$'),
  attributes jsonb not null default '{}'::jsonb,
  status text not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  unique (node_type, canonical_key)
);

create table if not exists ai_business_os_prod.knowledge_edges (
  id uuid primary key default gen_random_uuid(),
  source_node_id uuid not null references ai_business_os_prod.knowledge_nodes(id),
  edge_type text not null,
  target_node_id uuid not null references ai_business_os_prod.knowledge_nodes(id),
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  attributes jsonb not null default '{}'::jsonb,
  valid_from timestamptz not null default now(),
  valid_to timestamptz,
  status text not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  check (source_node_id <> target_node_id),
  check (valid_to is null or valid_to >= valid_from)
);

create table if not exists ai_business_os_prod.memory_items (
  id uuid primary key default gen_random_uuid(),
  memory_key text not null,
  version text not null,
  scope text not null,
  objective text not null,
  content jsonb not null,
  content_hash text not null check (content_hash ~ '^[0-9a-f]{64}$'),
  status text not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  unique (memory_key, version, scope, objective)
);

create table if not exists ai_business_os_prod.memory_observations (
  id uuid primary key default gen_random_uuid(),
  memory_id uuid not null references ai_business_os_prod.memory_items(id),
  event_id text not null,
  reward numeric not null check (reward between -1 and 1),
  attribution_fraction numeric not null check (
    attribution_fraction > 0 and attribution_fraction <= 1
  ),
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  verification_status text not null default 'UNVERIFIED'
    check (verification_status in ('UNVERIFIED','VERIFIED','REJECTED')),
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique (memory_id, event_id)
);

create index if not exists idx_products_business on ai_business_os_prod.products(business_id);
create index if not exists idx_projects_business_status on ai_business_os_prod.projects(business_id, status);
create index if not exists idx_customers_business on ai_business_os_prod.customers(business_id);
create index if not exists idx_prospects_business on ai_business_os_prod.prospects(business_id);
create index if not exists idx_opportunities_business_stage on ai_business_os_prod.opportunities(business_id, stage);
create index if not exists idx_experiments_business_status on ai_business_os_prod.experiments(business_id, status);
create index if not exists idx_metrics_key_time on ai_business_os_prod.metrics(metric_key, observed_at desc);
create index if not exists idx_financial_events_business_time on ai_business_os_prod.financial_events(business_id, occurred_at desc);
create index if not exists idx_agent_runs_agent_time on ai_business_os_prod.agent_runs(agent_id, started_at desc);
create index if not exists idx_evidence_business_time on ai_business_os_prod.evidence(business_id, observed_at desc);
create index if not exists idx_alerts_status_severity on ai_business_os_prod.alerts(status, severity);
create index if not exists idx_knowledge_edges_source on ai_business_os_prod.knowledge_edges(source_node_id, edge_type, status);
create index if not exists idx_knowledge_edges_target on ai_business_os_prod.knowledge_edges(target_node_id, edge_type, status);

alter table ai_business_os_prod.schema_meta enable row level security;
alter table ai_business_os_prod.businesses enable row level security;
alter table ai_business_os_prod.products enable row level security;
alter table ai_business_os_prod.projects enable row level security;
alter table ai_business_os_prod.repositories enable row level security;
alter table ai_business_os_prod.customers enable row level security;
alter table ai_business_os_prod.prospects enable row level security;
alter table ai_business_os_prod.contacts enable row level security;
alter table ai_business_os_prod.opportunities enable row level security;
alter table ai_business_os_prod.experiments enable row level security;
alter table ai_business_os_prod.decisions enable row level security;
alter table ai_business_os_prod.metrics enable row level security;
alter table ai_business_os_prod.financial_events enable row level security;
alter table ai_business_os_prod.agent_runs enable row level security;
alter table ai_business_os_prod.evidence enable row level security;
alter table ai_business_os_prod.truth_claims enable row level security;
alter table ai_business_os_prod.truth_evidence enable row level security;
alter table ai_business_os_prod.alerts enable row level security;
alter table ai_business_os_prod.approvals enable row level security;
alter table ai_business_os_prod.deployments enable row level security;
alter table ai_business_os_prod.incidents enable row level security;
alter table ai_business_os_prod.knowledge_nodes enable row level security;
alter table ai_business_os_prod.knowledge_edges enable row level security;
alter table ai_business_os_prod.memory_items enable row level security;
alter table ai_business_os_prod.memory_observations enable row level security;

revoke all on all tables in schema ai_business_os_prod from public, anon, authenticated;
revoke all on all sequences in schema ai_business_os_prod from public, anon, authenticated;


-- MIGRATION 20260924211428 add_ai_business_os_prod_fk_indexes_v1

create index if not exists idx_alerts_business
  on ai_business_os_prod.alerts(business_id);
create index if not exists idx_contacts_business
  on ai_business_os_prod.contacts(business_id);
create index if not exists idx_contacts_customer
  on ai_business_os_prod.contacts(customer_id);
create index if not exists idx_contacts_prospect
  on ai_business_os_prod.contacts(prospect_id);
create index if not exists idx_decisions_business
  on ai_business_os_prod.decisions(business_id);
create index if not exists idx_decisions_project
  on ai_business_os_prod.decisions(project_id);
create index if not exists idx_deployments_business
  on ai_business_os_prod.deployments(business_id);
create index if not exists idx_deployments_product
  on ai_business_os_prod.deployments(product_id);
create index if not exists idx_deployments_repository
  on ai_business_os_prod.deployments(repository_id);
create index if not exists idx_experiments_product
  on ai_business_os_prod.experiments(product_id);
create index if not exists idx_experiments_opportunity
  on ai_business_os_prod.experiments(opportunity_id);
create index if not exists idx_financial_events_opportunity
  on ai_business_os_prod.financial_events(opportunity_id);
create index if not exists idx_incidents_business
  on ai_business_os_prod.incidents(business_id);
create index if not exists idx_metrics_business
  on ai_business_os_prod.metrics(business_id);
create index if not exists idx_metrics_product
  on ai_business_os_prod.metrics(product_id);
create index if not exists idx_opportunities_product
  on ai_business_os_prod.opportunities(product_id);
create index if not exists idx_opportunities_customer
  on ai_business_os_prod.opportunities(customer_id);
create index if not exists idx_opportunities_prospect
  on ai_business_os_prod.opportunities(prospect_id);
create index if not exists idx_projects_product
  on ai_business_os_prod.projects(product_id);
create index if not exists idx_repositories_product
  on ai_business_os_prod.repositories(product_id);
create index if not exists idx_truth_evidence_evidence
  on ai_business_os_prod.truth_evidence(evidence_id);


-- MIGRATION 20260924211643 create_ai_business_os_tool_registry_v1

create table if not exists ai_business_os_prod.tool_providers (
  provider_key text primary key,
  display_name text not null,
  connector_namespace text not null,
  connection_status text not null
    check (connection_status in (
      'VERIFIED_CONNECTED',
      'CONNECTED_NO_RESOURCES',
      'UNAVAILABLE_ACCOUNT_INACTIVE',
      'UNVERIFIED'
    )),
  enabled boolean not null default true,
  verified_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.tool_actions (
  action_key text primary key,
  provider_key text not null references ai_business_os_prod.tool_providers(provider_key),
  connector_tool_name text not null,
  action_class text not null
    check (action_class in (
      'READ','INTERNAL_WRITE','EXTERNAL_WRITE','PRODUCTION_CHANGE',
      'MONEY_MOVEMENT','DESTRUCTIVE','POLICY_CHANGE'
    )),
  approval_required boolean not null,
  read_only boolean not null,
  enabled boolean not null default true,
  requires_resource_selection boolean not null default false,
  cost_units numeric not null default 0 check (cost_units >= 0),
  reliability_tier text not null default 'A',
  risk_notes text,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.tool_registry_events (
  id uuid primary key default gen_random_uuid(),
  provider_key text references ai_business_os_prod.tool_providers(provider_key),
  action_key text references ai_business_os_prod.tool_actions(action_key),
  event_type text not null,
  status text not null,
  detail jsonb not null default '{}'::jsonb,
  observed_at timestamptz not null default now()
);

alter table ai_business_os_prod.tool_providers enable row level security;
alter table ai_business_os_prod.tool_actions enable row level security;
alter table ai_business_os_prod.tool_registry_events enable row level security;

revoke all on ai_business_os_prod.tool_providers,
  ai_business_os_prod.tool_actions,
  ai_business_os_prod.tool_registry_events
from public, anon, authenticated;

create index if not exists idx_tool_actions_provider_enabled
  on ai_business_os_prod.tool_actions(provider_key, enabled);
create index if not exists idx_tool_actions_class_enabled
  on ai_business_os_prod.tool_actions(action_class, enabled);
create index if not exists idx_tool_registry_events_provider_time
  on ai_business_os_prod.tool_registry_events(provider_key, observed_at desc);

insert into ai_business_os_prod.tool_providers(
  provider_key, display_name, connector_namespace, connection_status,
  enabled, verified_at, metadata, updated_at
) values
('github','GitHub','mcp__GitHub__','VERIFIED_CONNECTED',true,now(),'{"purpose":"source control and CI"}',now()),
('gmail','Gmail','mcp__Gmail__','VERIFIED_CONNECTED',true,now(),'{"purpose":"business email"}',now()),
('google_drive','Google Drive','mcp__Google_Drive__','VERIFIED_CONNECTED',true,now(),'{"purpose":"documents and files"}',now()),
('google_calendar','Google Calendar','mcp__Google_Calendar__','VERIFIED_CONNECTED',true,now(),'{"purpose":"scheduling"}',now()),
('stripe','Stripe','mcp__Stripe__','VERIFIED_CONNECTED',true,now(),'{"purpose":"payments and revenue","account_count":6,"has_live_accounts":true}',now()),
('supabase','Supabase','mcp__Supabase__','VERIFIED_CONNECTED',true,now(),'{"purpose":"production business brain"}',now()),
('replit','Replit','mcp__Replit__','VERIFIED_CONNECTED',true,now(),'{"purpose":"app build and preview","verified_app":"StarBlox"}',now()),
('vercel','Vercel','mcp__Vercel__','CONNECTED_NO_RESOURCES',false,now(),'{"purpose":"deployment","team_count":0}',now()),
('apollo','Apollo.io','mcp__Apollo_io__','UNAVAILABLE_ACCOUNT_INACTIVE',false,now(),'{"purpose":"prospecting and GTM","reason":"account inactive"}',now())
on conflict (provider_key) do update set
  display_name=excluded.display_name,
  connector_namespace=excluded.connector_namespace,
  connection_status=excluded.connection_status,
  enabled=excluded.enabled,
  verified_at=excluded.verified_at,
  metadata=excluded.metadata,
  updated_at=excluded.updated_at;

insert into ai_business_os_prod.tool_actions(
  action_key, provider_key, connector_tool_name, action_class,
  approval_required, read_only, enabled, requires_resource_selection,
  cost_units, reliability_tier, risk_notes, metadata, updated_at
) values
('github.repo.read','github','mcp__GitHub__fetch_file','READ',false,true,true,false,0,'A',null,'{}',now()),
('github.pr.read','github','mcp__GitHub__get_pr_info','READ',false,true,true,false,0,'A',null,'{}',now()),
('github.branch.create','github','mcp__GitHub__create_branch','INTERNAL_WRITE',false,false,true,false,1,'A','development branch only unless separately governed','{}',now()),
('github.file.write','github','mcp__GitHub__update_file','INTERNAL_WRITE',false,false,true,false,1,'A','non-production branches only by default','{}',now()),
('github.pr.create','github','mcp__GitHub__create_pull_request','EXTERNAL_WRITE',true,false,true,false,1,'A','creates externally visible repository state','{}',now()),
('github.pr.merge','github','mcp__GitHub__merge_pull_request','PRODUCTION_CHANGE',true,false,true,false,2,'A','must remain exact-head and human approved','{}',now()),
('github.file.delete','github','mcp__GitHub__delete_file','DESTRUCTIVE',true,false,true,false,2,'A','destructive repository write','{}',now()),

('gmail.search','gmail','mcp__Gmail__search_emails','READ',false,true,true,false,0,'A',null,'{}',now()),
('gmail.read','gmail','mcp__Gmail__read_email','READ',false,true,true,false,0,'A',null,'{}',now()),
('gmail.draft.create','gmail','mcp__Gmail__create_draft','INTERNAL_WRITE',false,false,true,false,1,'A','draft only; no send authority','{}',now()),
('gmail.draft.update','gmail','mcp__Gmail__update_draft','INTERNAL_WRITE',false,false,true,false,1,'A','draft only; no send authority','{}',now()),
('gmail.send','gmail','mcp__Gmail__send_email','EXTERNAL_WRITE',true,false,true,false,2,'A','live outbound message','{}',now()),
('gmail.send_draft','gmail','mcp__Gmail__send_draft','EXTERNAL_WRITE',true,false,true,false,2,'A','live outbound message','{}',now()),
('gmail.forward','gmail','mcp__Gmail__forward_emails','EXTERNAL_WRITE',true,false,true,false,2,'A','live outbound message','{}',now()),
('gmail.archive','gmail','mcp__Gmail__archive_emails','INTERNAL_WRITE',false,false,true,false,1,'A',null,'{}',now()),
('gmail.delete','gmail','mcp__Gmail__delete_emails','DESTRUCTIVE',true,false,true,false,2,'A','mail deletion','{}',now()),

('drive.search','google_drive','mcp__Google_Drive__search','READ',false,true,true,false,0,'A',null,'{}',now()),
('drive.document.read','google_drive','mcp__Google_Drive__get_document_text','READ',false,true,true,false,0,'A',null,'{}',now()),
('drive.sheet.read','google_drive','mcp__Google_Drive__get_spreadsheet_range','READ',false,true,true,false,0,'A',null,'{}',now()),
('drive.file.create','google_drive','mcp__Google_Drive__create_file','INTERNAL_WRITE',false,false,true,false,1,'A','private/internal creation by default','{}',now()),
('drive.file.update','google_drive','mcp__Google_Drive__update_file','INTERNAL_WRITE',false,false,true,false,1,'A','internal content mutation','{}',now()),
('drive.file.upload','google_drive','mcp__Google_Drive__upload_file','INTERNAL_WRITE',false,false,true,false,1,'A','internal content mutation','{}',now()),
('drive.file.share','google_drive','mcp__Google_Drive__share_file','EXTERNAL_WRITE',true,false,true,true,2,'A','changes external access','{}',now()),
('drive.file.delete','google_drive','mcp__Google_Drive__delete_file','DESTRUCTIVE',true,false,true,false,2,'A','file deletion','{}',now()),

('calendar.search','google_calendar','mcp__Google_Calendar__search_events','READ',false,true,true,false,0,'A',null,'{}',now()),
('calendar.availability','google_calendar','mcp__Google_Calendar__get_availability','READ',false,true,true,false,0,'A',null,'{}',now()),
('calendar.event.create','google_calendar','mcp__Google_Calendar__create_event','EXTERNAL_WRITE',true,false,true,true,1,'A','may notify or affect other attendees','{}',now()),
('calendar.event.update','google_calendar','mcp__Google_Calendar__update_event','EXTERNAL_WRITE',true,false,true,true,1,'A','may notify or affect other attendees','{}',now()),
('calendar.event.respond','google_calendar','mcp__Google_Calendar__respond_event','EXTERNAL_WRITE',true,false,true,true,1,'A','sends attendance response','{}',now()),
('calendar.event.delete','google_calendar','mcp__Google_Calendar__delete_event','DESTRUCTIVE',true,false,true,true,2,'A','calendar deletion','{}',now()),

('stripe.read','stripe','mcp__Stripe__stripe_api_read','READ',false,true,true,true,0,'A','account must be explicitly selected before use','{}',now()),
('stripe.analytics','stripe','mcp__Stripe__stripe_analytics','READ',false,true,true,true,1,'A','account must be explicitly selected before use','{}',now()),
('stripe.write','stripe','mcp__Stripe__stripe_api_write','MONEY_MOVEMENT',true,false,true,true,3,'A','generic Stripe writes are treated as financial until operation-specific policy narrows them','{}',now()),

('supabase.tables.read','supabase','mcp__Supabase__list_tables','READ',false,true,true,true,0,'A',null,'{}',now()),
('supabase.logs.read','supabase','mcp__Supabase__query_logs','READ',false,true,true,true,0,'A',null,'{}',now()),
('supabase.sql.execute','supabase','mcp__Supabase__execute_sql','PRODUCTION_CHANGE',true,false,true,true,2,'A','raw SQL can mutate production state','{}',now()),
('supabase.migration.apply','supabase','mcp__Supabase__apply_migration','PRODUCTION_CHANGE',true,false,true,true,3,'A','DDL migration','{}',now()),
('supabase.edge.deploy','supabase','mcp__Supabase__deploy_edge_function','PRODUCTION_CHANGE',true,false,true,true,3,'A','deploys executable production code','{}',now()),
('supabase.project.create','supabase','mcp__Supabase__create_project','EXTERNAL_WRITE',true,false,true,true,3,'A','requires separate cost confirmation','{}',now()),
('supabase.branch.create','supabase','mcp__Supabase__create_branch','EXTERNAL_WRITE',true,false,true,true,2,'A','requires separate cost confirmation','{}',now()),

('replit.apps.list','replit','mcp__Replit__list_apps','READ',false,true,true,false,0,'A',null,'{}',now()),
('replit.app.inspect','replit','mcp__Replit__ask_question','READ',false,true,true,true,0,'A',null,'{}',now()),
('replit.app.update','replit','mcp__Replit__update_app_using_prompt','INTERNAL_WRITE',false,false,true,true,2,'B','development mutation only; publish is separate','{}',now()),
('replit.app.create','replit','mcp__Replit__create_app_from_prompt','EXTERNAL_WRITE',true,false,true,false,2,'B','creates external cloud resource','{}',now()),
('replit.app.publish','replit','mcp__Replit__publish_app','PRODUCTION_CHANGE',true,false,true,true,3,'A','publishes live application','{}',now()),

('vercel.projects.list','vercel','mcp__Vercel__list_projects','READ',false,true,false,true,0,'A','disabled until a team/project resource exists','{}',now()),
('vercel.logs.read','vercel','mcp__Vercel__get_runtime_logs','READ',false,true,false,true,0,'A','disabled until a team/project resource exists','{}',now()),
('vercel.deploy','vercel','mcp__Vercel__deploy_to_vercel','PRODUCTION_CHANGE',true,false,false,true,3,'A','disabled until a team/project resource exists','{}',now()),

('apollo.read','apollo','mcp__Apollo_io__apollo_read','READ',false,true,false,true,0,'B','disabled because Apollo account is inactive','{}',now()),
('apollo.write','apollo','mcp__Apollo_io__apollo_write','EXTERNAL_WRITE',true,false,false,true,2,'B','disabled because Apollo account is inactive','{}',now()),
('apollo.destructive','apollo','mcp__Apollo_io__apollo_write_destructive','DESTRUCTIVE',true,false,false,true,3,'B','disabled because Apollo account is inactive','{}',now())
on conflict (action_key) do update set
  provider_key=excluded.provider_key,
  connector_tool_name=excluded.connector_tool_name,
  action_class=excluded.action_class,
  approval_required=excluded.approval_required,
  read_only=excluded.read_only,
  enabled=excluded.enabled,
  requires_resource_selection=excluded.requires_resource_selection,
  cost_units=excluded.cost_units,
  reliability_tier=excluded.reliability_tier,
  risk_notes=excluded.risk_notes,
  metadata=excluded.metadata,
  updated_at=excluded.updated_at;


-- MIGRATION 20260924211702 index_ai_business_os_tool_registry_v1

create index if not exists idx_tool_registry_events_action
  on ai_business_os_prod.tool_registry_events(action_key);


-- MIGRATION 20260924212038 create_ai_business_os_agent_fleet_v1

create table if not exists ai_business_os_prod.agents (
  agent_id text primary key,
  role_key text not null unique,
  display_name text not null,
  mode text not null default 'SHADOW'
    check (mode in ('SHADOW','LOW_RISK_AUTONOMY','APPROVAL_GATED','DISABLED')),
  status text not null default 'ACTIVE'
    check (status in ('ACTIVE','PAUSED','DISABLED')),
  parent_agent_id text references ai_business_os_prod.agents(agent_id),
  objective text not null,
  memory_scope text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.agent_action_grants (
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  action_key text not null references ai_business_os_prod.tool_actions(action_key),
  grant_mode text not null
    check (grant_mode in ('ALLOW','REQUIRE_APPROVAL','DENY')),
  rationale text,
  created_at timestamptz not null default now(),
  primary key (agent_id, action_key)
);

create table if not exists ai_business_os_prod.agent_budgets (
  agent_id text primary key references ai_business_os_prod.agents(agent_id),
  window_seconds integer not null default 86400 check (window_seconds > 0),
  max_actions integer not null check (max_actions >= 0),
  max_cost_units numeric not null check (max_cost_units >= 0),
  max_money_cents bigint not null default 0 check (max_money_cents >= 0),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.agent_heartbeats (
  agent_id text primary key references ai_business_os_prod.agents(agent_id),
  last_heartbeat_at timestamptz,
  generation bigint not null default 1,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.agent_goals (
  id uuid primary key default gen_random_uuid(),
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  goal_type text not null,
  title text not null,
  status text not null default 'PENDING'
    check (status in ('PENDING','ACTIVE','BLOCKED','VERIFYING','COMPLETE','CANCELLED')),
  priority integer not null default 0,
  constraints jsonb not null default '{}'::jsonb,
  evidence_requirements jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table ai_business_os_prod.agents enable row level security;
alter table ai_business_os_prod.agent_action_grants enable row level security;
alter table ai_business_os_prod.agent_budgets enable row level security;
alter table ai_business_os_prod.agent_heartbeats enable row level security;
alter table ai_business_os_prod.agent_goals enable row level security;

revoke all on ai_business_os_prod.agents,
  ai_business_os_prod.agent_action_grants,
  ai_business_os_prod.agent_budgets,
  ai_business_os_prod.agent_heartbeats,
  ai_business_os_prod.agent_goals
from public, anon, authenticated;

create index if not exists idx_agent_grants_action
  on ai_business_os_prod.agent_action_grants(action_key, grant_mode);
create index if not exists idx_agent_goals_agent_status
  on ai_business_os_prod.agent_goals(agent_id, status, priority desc);

insert into ai_business_os_prod.agents(
  agent_id, role_key, display_name, mode, status,
  parent_agent_id, objective, memory_scope
) values
('agent-chief','CHIEF_OF_STAFF','Chief of Staff','SHADOW','ACTIVE',null,
 'Coordinate portfolio priorities, delegate work, synthesize evidence, and surface decisions without bypassing specialist or approval boundaries.',
 'portfolio'),
('agent-research','RESEARCH','Research','SHADOW','ACTIVE','agent-chief',
 'Find evidence, validate opportunities, and identify knowledge gaps using read-only sources.',
 'research'),
('agent-engineering','ENGINEERING','Engineering','SHADOW','ACTIVE','agent-chief',
 'Inspect repositories, prepare isolated implementation work, run tests, and create development artifacts without production authority.',
 'engineering'),
('agent-product','PRODUCT','Product','SHADOW','ACTIVE','agent-chief',
 'Translate customer/problem evidence into product experiments, requirements, and internal planning artifacts.',
 'product'),
('agent-growth','GROWTH_SALES','Growth / Sales','SHADOW','ACTIVE','agent-chief',
 'Identify qualified opportunities and prepare outreach/drafts while never sending without approval.',
 'growth'),
('agent-finance','FINANCE_ANALYTICS','Finance / Analytics','SHADOW','ACTIVE','agent-chief',
 'Measure revenue, costs, pipeline, and operating efficiency using read-only financial and analytics sources.',
 'finance'),
('agent-auditor','AUDITOR_REDTEAM','Auditor / Red Team','SHADOW','ACTIVE',null,
 'Independently verify claims, completion evidence, risks, and policy compliance; never self-approve executor work.',
 'audit')
on conflict (agent_id) do update set
  role_key=excluded.role_key,
  display_name=excluded.display_name,
  mode='SHADOW',
  status='ACTIVE',
  parent_agent_id=excluded.parent_agent_id,
  objective=excluded.objective,
  memory_scope=excluded.memory_scope,
  updated_at=now();

insert into ai_business_os_prod.agent_budgets(
  agent_id, window_seconds, max_actions, max_cost_units, max_money_cents
) values
('agent-chief',86400,80,120,0),
('agent-research',86400,120,100,0),
('agent-engineering',86400,100,150,0),
('agent-product',86400,60,80,0),
('agent-growth',86400,80,100,0),
('agent-finance',86400,80,100,0),
('agent-auditor',86400,120,120,0)
on conflict (agent_id) do update set
  window_seconds=excluded.window_seconds,
  max_actions=excluded.max_actions,
  max_cost_units=excluded.max_cost_units,
  max_money_cents=0,
  updated_at=now();

insert into ai_business_os_prod.agent_heartbeats(agent_id,last_heartbeat_at,generation,state)
select agent_id, now(), 1, '{"phase":"production_bootstrap","mode":"SHADOW"}'::jsonb
from ai_business_os_prod.agents
on conflict (agent_id) do update set
  last_heartbeat_at=excluded.last_heartbeat_at,
  state=excluded.state,
  updated_at=now();

-- Read grants shared by selected roles.
insert into ai_business_os_prod.agent_action_grants(agent_id,action_key,grant_mode,rationale)
select a.agent_id, ta.action_key, 'ALLOW',
       'Shadow-mode read access only; execution mode still blocks writes.'
from ai_business_os_prod.agents a
join ai_business_os_prod.tool_actions ta on ta.enabled=true and ta.action_class='READ'
where
  (a.agent_id in ('agent-chief','agent-auditor'))
  or (a.agent_id='agent-research' and ta.provider_key in ('github','gmail','google_drive','google_calendar','supabase','replit'))
  or (a.agent_id='agent-engineering' and ta.provider_key in ('github','supabase','replit'))
  or (a.agent_id='agent-product' and ta.provider_key in ('github','gmail','google_drive','supabase','replit'))
  or (a.agent_id='agent-growth' and ta.provider_key in ('gmail','google_drive','google_calendar','stripe'))
  or (a.agent_id='agent-finance' and ta.provider_key in ('stripe','supabase','google_drive'))
on conflict (agent_id,action_key) do update set
  grant_mode='ALLOW',
  rationale=excluded.rationale;

-- Candidate low-risk internal writes are pre-registered but remain blocked by SHADOW mode until Step 6.
insert into ai_business_os_prod.agent_action_grants(agent_id,action_key,grant_mode,rationale) values
('agent-engineering','github.branch.create','ALLOW','Development branch only; production branch mutation prohibited.'),
('agent-engineering','github.file.write','ALLOW','Development branch only; no direct production writes.'),
('agent-engineering','replit.app.update','ALLOW','Development mutation only; publish requires separate approval.'),
('agent-product','drive.file.create','ALLOW','Internal planning artifact only; sharing remains approval gated.'),
('agent-product','drive.file.update','ALLOW','Internal planning artifact only.'),
('agent-growth','gmail.draft.create','ALLOW','Draft only; send remains approval gated.'),
('agent-growth','gmail.draft.update','ALLOW','Draft only; send remains approval gated.'),
('agent-growth','drive.file.create','ALLOW','Internal sales planning artifact only.'),
('agent-growth','drive.file.update','ALLOW','Internal sales planning artifact only.'),
('agent-chief','drive.file.create','ALLOW','Internal executive report only.'),
('agent-chief','drive.file.update','ALLOW','Internal executive report only.')
on conflict (agent_id,action_key) do update set
  grant_mode='ALLOW',
  rationale=excluded.rationale;

-- Everything consequential is explicitly approval-gated or denied.
insert into ai_business_os_prod.agent_action_grants(agent_id,action_key,grant_mode,rationale)
select a.agent_id, ta.action_key,
       case
         when ta.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','POLICY_CHANGE')
           then 'REQUIRE_APPROVAL'
         else 'DENY'
       end,
       case
         when ta.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','POLICY_CHANGE')
           then 'Consequential action requires explicit human approval.'
         else 'Money movement or destructive action disabled for autonomous fleet.'
       end
from ai_business_os_prod.agents a
join ai_business_os_prod.tool_actions ta
  on ta.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','MONEY_MOVEMENT','DESTRUCTIVE','POLICY_CHANGE')
on conflict (agent_id,action_key) do update set
  grant_mode=excluded.grant_mode,
  rationale=excluded.rationale;


-- MIGRATION 20260924212103 create_ai_business_os_shadow_mode_v1

create table if not exists ai_business_os_prod.shadow_runs (
  id uuid primary key default gen_random_uuid(),
  run_key text not null unique,
  status text not null default 'RUNNING'
    check (status in ('RUNNING','COMPLETE','FAILED')),
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  observed_systems jsonb not null default '[]'::jsonb,
  source_snapshot_hash text,
  notes text
);

create table if not exists ai_business_os_prod.shadow_observations (
  id uuid primary key default gen_random_uuid(),
  shadow_run_id uuid not null references ai_business_os_prod.shadow_runs(id),
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  provider_key text references ai_business_os_prod.tool_providers(provider_key),
  observation_type text not null,
  source_ref text not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  observation jsonb not null,
  observed_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.shadow_recommendations (
  id uuid primary key default gen_random_uuid(),
  shadow_run_id uuid not null references ai_business_os_prod.shadow_runs(id),
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  action_key text references ai_business_os_prod.tool_actions(action_key),
  recommendation_type text not null,
  title text not null,
  rationale text not null,
  evidence_refs jsonb not null default '[]'::jsonb,
  predicted_risk text not null,
  would_require_approval boolean not null,
  disposition text not null default 'UNREVIEWED'
    check (disposition in ('UNREVIEWED','SAFE_LOW_RISK','KEEP_SHADOW','BLOCK')),
  auditor_notes text,
  created_at timestamptz not null default now()
);

alter table ai_business_os_prod.shadow_runs enable row level security;
alter table ai_business_os_prod.shadow_observations enable row level security;
alter table ai_business_os_prod.shadow_recommendations enable row level security;
revoke all on ai_business_os_prod.shadow_runs,
  ai_business_os_prod.shadow_observations,
  ai_business_os_prod.shadow_recommendations
from public, anon, authenticated;

create index if not exists idx_shadow_observations_run_agent
  on ai_business_os_prod.shadow_observations(shadow_run_id, agent_id);
create index if not exists idx_shadow_recommendations_run_disposition
  on ai_business_os_prod.shadow_recommendations(shadow_run_id, disposition);


-- MIGRATION 20260924212702 activate_ai_business_os_low_risk_autonomy_v1

create table if not exists ai_business_os_prod.autonomy_policies (
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  action_key text not null references ai_business_os_prod.tool_actions(action_key),
  autonomy_status text not null
    check (autonomy_status in ('ENABLED','SHADOW_ONLY','DISABLED')),
  constraints jsonb not null default '{}'::jsonb,
  promoted_from_shadow_run_id uuid references ai_business_os_prod.shadow_runs(id),
  auditor_disposition text not null,
  activated_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (agent_id, action_key)
);

create table if not exists ai_business_os_prod.autonomy_action_receipts (
  id uuid primary key default gen_random_uuid(),
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  action_key text not null references ai_business_os_prod.tool_actions(action_key),
  target_ref text not null,
  parameters jsonb not null,
  outcome text not null check (outcome in ('SUCCEEDED','FAILED','BLOCKED')),
  evidence_ref text,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  executed_at timestamptz not null default now()
);

alter table ai_business_os_prod.autonomy_policies enable row level security;
alter table ai_business_os_prod.autonomy_action_receipts enable row level security;
revoke all on ai_business_os_prod.autonomy_policies,
  ai_business_os_prod.autonomy_action_receipts
from public, anon, authenticated;

create index if not exists idx_autonomy_policies_status
  on ai_business_os_prod.autonomy_policies(autonomy_status, agent_id);
create index if not exists idx_autonomy_receipts_agent_time
  on ai_business_os_prod.autonomy_action_receipts(agent_id, executed_at desc);

-- Promote all read actions already granted ALLOW for active providers, except Auditor stays shadow-only.
insert into ai_business_os_prod.autonomy_policies(
  agent_id,action_key,autonomy_status,constraints,
  promoted_from_shadow_run_id,auditor_disposition,activated_at
)
select g.agent_id,g.action_key,
       case when g.agent_id='agent-auditor' then 'SHADOW_ONLY' else 'ENABLED' end,
       case
         when ta.requires_resource_selection
           then '{"resource_binding_required":true,"resource_guessing_forbidden":true}'::jsonb
         else '{}'::jsonb
       end,
       sr.id,
       case when g.agent_id='agent-auditor' then 'INDEPENDENCE_BOUNDARY' else 'SAFE_LOW_RISK' end,
       case when g.agent_id='agent-auditor' then null else now() end
from ai_business_os_prod.agent_action_grants g
join ai_business_os_prod.tool_actions ta on ta.action_key=g.action_key
cross join ai_business_os_prod.shadow_runs sr
where sr.run_key='bootstrap-shadow-001'
  and g.grant_mode='ALLOW'
  and ta.action_class='READ'
  and ta.enabled=true
on conflict (agent_id,action_key) do update set
  autonomy_status=excluded.autonomy_status,
  constraints=excluded.constraints,
  promoted_from_shadow_run_id=excluded.promoted_from_shadow_run_id,
  auditor_disposition=excluded.auditor_disposition,
  activated_at=excluded.activated_at,
  updated_at=now();

-- Explicit internal-write promotions that cleared Shadow Mode.
insert into ai_business_os_prod.autonomy_policies(
  agent_id,action_key,autonomy_status,constraints,
  promoted_from_shadow_run_id,auditor_disposition,activated_at
)
select x.agent_id,x.action_key,x.autonomy_status,x.constraints,sr.id,x.auditor_disposition,
       case when x.autonomy_status='ENABLED' then now() else null end
from ai_business_os_prod.shadow_runs sr
cross join (
  values
  ('agent-chief','drive.file.create','ENABLED',
    '{"private_only":true,"sharing_forbidden":true,"purpose":["executive_report","internal_analysis"]}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-chief','drive.file.update','ENABLED',
    '{"private_only":true,"sharing_forbidden":true}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-engineering','github.branch.create','ENABLED',
    '{"allowed_prefixes":["ai-factory/","ai-business-os-"],"protected_refs":["main","ai-business-os-v1.0-frozen"],"force_forbidden":true}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-engineering','github.file.write','ENABLED',
    '{"protected_refs":["main","ai-business-os-v1.0-frozen"],"requires_non_production_branch":true}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-engineering','replit.app.update','SHADOW_ONLY',
    '{"reason":"read_only_shadow_inspection_timed_out","publish_forbidden":true}'::jsonb,
    'KEEP_SHADOW'),
  ('agent-product','drive.file.create','ENABLED',
    '{"private_only":true,"sharing_forbidden":true,"purpose":["product_plan","experiment_plan","scorecard"]}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-product','drive.file.update','ENABLED',
    '{"private_only":true,"sharing_forbidden":true}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-growth','gmail.draft.create','ENABLED',
    '{"draft_only":true,"send_forbidden":true}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-growth','gmail.draft.update','ENABLED',
    '{"draft_only":true,"send_forbidden":true}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-growth','drive.file.create','ENABLED',
    '{"private_only":true,"sharing_forbidden":true,"purpose":["sales_analysis","outreach_plan"]}'::jsonb,
    'SAFE_LOW_RISK'),
  ('agent-growth','drive.file.update','ENABLED',
    '{"private_only":true,"sharing_forbidden":true}'::jsonb,
    'SAFE_LOW_RISK')
) as x(agent_id,action_key,autonomy_status,constraints,auditor_disposition)
where sr.run_key='bootstrap-shadow-001'
on conflict (agent_id,action_key) do update set
  autonomy_status=excluded.autonomy_status,
  constraints=excluded.constraints,
  promoted_from_shadow_run_id=excluded.promoted_from_shadow_run_id,
  auditor_disposition=excluded.auditor_disposition,
  activated_at=excluded.activated_at,
  updated_at=now();

-- Keep all consequential actions outside autonomous scope even if a grant exists.
insert into ai_business_os_prod.autonomy_policies(
  agent_id,action_key,autonomy_status,constraints,
  promoted_from_shadow_run_id,auditor_disposition,activated_at
)
select g.agent_id,g.action_key,'DISABLED',
       '{"human_approval_required":true,"autonomous_execution_forbidden":true}'::jsonb,
       sr.id,'BLOCK_AUTONOMY',null
from ai_business_os_prod.agent_action_grants g
join ai_business_os_prod.tool_actions ta on ta.action_key=g.action_key
cross join ai_business_os_prod.shadow_runs sr
where sr.run_key='bootstrap-shadow-001'
  and ta.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','MONEY_MOVEMENT','DESTRUCTIVE','POLICY_CHANGE')
on conflict (agent_id,action_key) do update set
  autonomy_status='DISABLED',
  constraints=excluded.constraints,
  promoted_from_shadow_run_id=excluded.promoted_from_shadow_run_id,
  auditor_disposition='BLOCK_AUTONOMY',
  activated_at=null,
  updated_at=now();

-- Any allowed internal write not explicitly promoted remains shadow-only.
insert into ai_business_os_prod.autonomy_policies(
  agent_id,action_key,autonomy_status,constraints,
  promoted_from_shadow_run_id,auditor_disposition,activated_at
)
select g.agent_id,g.action_key,'SHADOW_ONLY',
       '{"not_promoted_by_shadow_evidence":true}'::jsonb,
       sr.id,'KEEP_SHADOW',null
from ai_business_os_prod.agent_action_grants g
join ai_business_os_prod.tool_actions ta on ta.action_key=g.action_key
cross join ai_business_os_prod.shadow_runs sr
where sr.run_key='bootstrap-shadow-001'
  and g.grant_mode='ALLOW'
  and ta.action_class='INTERNAL_WRITE'
  and not exists (
    select 1 from ai_business_os_prod.autonomy_policies p
    where p.agent_id=g.agent_id and p.action_key=g.action_key
  )
on conflict (agent_id,action_key) do nothing;

update ai_business_os_prod.agents
set mode=case
  when agent_id='agent-auditor' then 'SHADOW'
  else 'LOW_RISK_AUTONOMY'
end,
updated_at=now()
where status='ACTIVE';

-- Replit mutation explicitly remains shadow-only at the grant layer too.
update ai_business_os_prod.agent_action_grants
set grant_mode='DENY',
    rationale='Shadow read timed out; mutation autonomy not promoted.'
where agent_id='agent-engineering' and action_key='replit.app.update';


-- MIGRATION 20260924215224 create_ai_business_os_human_approval_inbox_v1

create table if not exists ai_business_os_prod.approval_inbox (
  id uuid primary key default gen_random_uuid(),
  request_key text not null unique,
  agent_id text not null references ai_business_os_prod.agents(agent_id),
  action_key text not null references ai_business_os_prod.tool_actions(action_key),
  action_class text not null,
  title text not null,
  summary text not null,
  exact_parameters jsonb not null,
  intent_hash text not null unique check (intent_hash ~ '^[0-9a-f]{64}$'),
  evidence_refs jsonb not null default '[]'::jsonb,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  predicted_risk text not null,
  expected_cost_units numeric not null default 0 check (expected_cost_units >= 0),
  expected_money_cents bigint not null default 0 check (expected_money_cents >= 0),
  rollback_plan jsonb not null default '{}'::jsonb,
  status text not null default 'PENDING'
    check (status in ('PENDING','APPROVED','REJECTED','EXPIRED','CONSUMED','CANCELLED')),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  decided_at timestamptz,
  decided_by text,
  decision_reason text,
  decision_receipt_hash text check (
    decision_receipt_hash is null or decision_receipt_hash ~ '^[0-9a-f]{64}$'
  ),
  consumed_at timestamptz,
  execution_receipt_id uuid references ai_business_os_prod.autonomy_action_receipts(id)
);

create table if not exists ai_business_os_prod.approval_inbox_events (
  id uuid primary key default gen_random_uuid(),
  approval_id uuid not null references ai_business_os_prod.approval_inbox(id),
  event_type text not null,
  actor text not null,
  event_payload jsonb not null default '{}'::jsonb,
  event_hash text not null unique check (event_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

alter table ai_business_os_prod.approval_inbox enable row level security;
alter table ai_business_os_prod.approval_inbox_events enable row level security;
revoke all on ai_business_os_prod.approval_inbox,
  ai_business_os_prod.approval_inbox_events
from public, anon, authenticated;

create index if not exists idx_approval_inbox_status_expiry
  on ai_business_os_prod.approval_inbox(status, expires_at);
create index if not exists idx_approval_inbox_agent_status
  on ai_business_os_prod.approval_inbox(agent_id, status);
create index if not exists idx_approval_inbox_events_approval_time
  on ai_business_os_prod.approval_inbox_events(approval_id, created_at);

create or replace function ai_business_os_prod.approval_decide(
  p_request_key text,
  p_decision text,
  p_decided_by text,
  p_reason text
) returns table (
  request_key text,
  status text,
  decision_receipt_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_row ai_business_os_prod.approval_inbox%rowtype;
  v_new_status text;
  v_receipt text;
  v_event_hash text;
begin
  if p_decision not in ('APPROVE','REJECT') then
    raise exception 'decision must be APPROVE or REJECT';
  end if;
  if coalesce(trim(p_decided_by),'') = '' or coalesce(trim(p_reason),'') = '' then
    raise exception 'decider identity and reason are required';
  end if;

  select * into v_row
  from ai_business_os_prod.approval_inbox
  where approval_inbox.request_key = p_request_key
  for update;

  if not found then
    raise exception 'unknown approval request';
  end if;
  if v_row.status <> 'PENDING' then
    raise exception 'approval request is not pending';
  end if;
  if v_row.expires_at <= now() then
    update ai_business_os_prod.approval_inbox
      set status='EXPIRED'
      where id=v_row.id;
    raise exception 'approval request expired';
  end if;

  v_new_status := case when p_decision='APPROVE' then 'APPROVED' else 'REJECTED' end;
  v_receipt := encode(
    digest(
      v_row.intent_hash || '|' || v_new_status || '|' || p_decided_by || '|' || p_reason,
      'sha256'
    ),
    'hex'
  );

  update ai_business_os_prod.approval_inbox
  set status=v_new_status,
      decided_at=now(),
      decided_by=p_decided_by,
      decision_reason=p_reason,
      decision_receipt_hash=v_receipt
  where id=v_row.id;

  v_event_hash := encode(
    digest(
      v_row.id::text || '|' || v_new_status || '|' || p_decided_by || '|' || v_receipt,
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.approval_inbox_events(
    approval_id,event_type,actor,event_payload,event_hash
  ) values (
    v_row.id,
    v_new_status,
    p_decided_by,
    jsonb_build_object('reason',p_reason,'intent_hash',v_row.intent_hash,'decision_receipt_hash',v_receipt),
    v_event_hash
  );

  return query select v_row.request_key, v_new_status, v_receipt;
end;
$$;

revoke execute on function ai_business_os_prod.approval_decide(text,text,text,text)
from public, anon, authenticated;


-- MIGRATION 20260924215251 add_ai_business_os_approval_consumption_v1

create or replace function ai_business_os_prod.approval_consume(
  p_request_key text,
  p_intent_hash text,
  p_execution_receipt_id uuid,
  p_actor text
) returns table (
  request_key text,
  status text,
  decision_receipt_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_row ai_business_os_prod.approval_inbox%rowtype;
  v_receipt_exists boolean;
  v_event_hash text;
begin
  if coalesce(trim(p_actor),'') = '' then
    raise exception 'actor is required';
  end if;

  select * into v_row
  from ai_business_os_prod.approval_inbox
  where approval_inbox.request_key = p_request_key
  for update;

  if not found then
    raise exception 'unknown approval request';
  end if;
  if v_row.status <> 'APPROVED' then
    raise exception 'approval request is not approved';
  end if;
  if v_row.expires_at <= now() then
    update ai_business_os_prod.approval_inbox
      set status='EXPIRED'
      where id=v_row.id;
    raise exception 'approval request expired';
  end if;
  if v_row.intent_hash <> p_intent_hash then
    raise exception 'intent hash mismatch';
  end if;

  select exists(
    select 1 from ai_business_os_prod.autonomy_action_receipts
    where id=p_execution_receipt_id
  ) into v_receipt_exists;

  if not v_receipt_exists then
    raise exception 'execution receipt does not exist';
  end if;

  update ai_business_os_prod.approval_inbox
  set status='CONSUMED',
      consumed_at=now(),
      execution_receipt_id=p_execution_receipt_id
  where id=v_row.id;

  v_event_hash := encode(
    digest(
      v_row.id::text || '|CONSUMED|' || p_actor || '|' ||
      p_execution_receipt_id::text || '|' || v_row.intent_hash,
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.approval_inbox_events(
    approval_id,event_type,actor,event_payload,event_hash
  ) values (
    v_row.id,
    'CONSUMED',
    p_actor,
    jsonb_build_object(
      'execution_receipt_id',p_execution_receipt_id,
      'intent_hash',v_row.intent_hash
    ),
    v_event_hash
  );

  return query
  select v_row.request_key, 'CONSUMED'::text, v_row.decision_receipt_hash;
end;
$$;

revoke execute on function ai_business_os_prod.approval_consume(text,text,uuid,text)
from public, anon, authenticated;

create or replace function ai_business_os_prod.expire_pending_approvals()
returns integer
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_count integer;
begin
  update ai_business_os_prod.approval_inbox
  set status='EXPIRED'
  where status='PENDING' and expires_at <= now();

  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

revoke execute on function ai_business_os_prod.expire_pending_approvals()
from public, anon, authenticated;


-- MIGRATION 20260924215335 fix_ai_business_os_approval_hash_search_path_v1

create or replace function ai_business_os_prod.approval_decide(
  p_request_key text,
  p_decision text,
  p_decided_by text,
  p_reason text
) returns table (
  request_key text,
  status text,
  decision_receipt_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_row ai_business_os_prod.approval_inbox%rowtype;
  v_new_status text;
  v_receipt text;
  v_event_hash text;
begin
  if p_decision not in ('APPROVE','REJECT') then
    raise exception 'decision must be APPROVE or REJECT';
  end if;
  if coalesce(trim(p_decided_by),'') = '' or coalesce(trim(p_reason),'') = '' then
    raise exception 'decider identity and reason are required';
  end if;

  select * into v_row
  from ai_business_os_prod.approval_inbox
  where approval_inbox.request_key = p_request_key
  for update;

  if not found then
    raise exception 'unknown approval request';
  end if;
  if v_row.status <> 'PENDING' then
    raise exception 'approval request is not pending';
  end if;
  if v_row.expires_at <= now() then
    update ai_business_os_prod.approval_inbox
      set status='EXPIRED'
      where id=v_row.id;
    raise exception 'approval request expired';
  end if;

  v_new_status := case when p_decision='APPROVE' then 'APPROVED' else 'REJECTED' end;
  v_receipt := encode(
    extensions.digest(
      v_row.intent_hash || '|' || v_new_status || '|' || p_decided_by || '|' || p_reason,
      'sha256'
    ),
    'hex'
  );

  update ai_business_os_prod.approval_inbox
  set status=v_new_status,
      decided_at=now(),
      decided_by=p_decided_by,
      decision_reason=p_reason,
      decision_receipt_hash=v_receipt
  where id=v_row.id;

  v_event_hash := encode(
    extensions.digest(
      v_row.id::text || '|' || v_new_status || '|' || p_decided_by || '|' || v_receipt,
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.approval_inbox_events(
    approval_id,event_type,actor,event_payload,event_hash
  ) values (
    v_row.id,
    v_new_status,
    p_decided_by,
    jsonb_build_object('reason',p_reason,'intent_hash',v_row.intent_hash,'decision_receipt_hash',v_receipt),
    v_event_hash
  );

  return query select v_row.request_key, v_new_status, v_receipt;
end;
$$;

create or replace function ai_business_os_prod.approval_consume(
  p_request_key text,
  p_intent_hash text,
  p_execution_receipt_id uuid,
  p_actor text
) returns table (
  request_key text,
  status text,
  decision_receipt_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_row ai_business_os_prod.approval_inbox%rowtype;
  v_receipt_exists boolean;
  v_event_hash text;
begin
  if coalesce(trim(p_actor),'') = '' then
    raise exception 'actor is required';
  end if;

  select * into v_row
  from ai_business_os_prod.approval_inbox
  where approval_inbox.request_key = p_request_key
  for update;

  if not found then
    raise exception 'unknown approval request';
  end if;
  if v_row.status <> 'APPROVED' then
    raise exception 'approval request is not approved';
  end if;
  if v_row.expires_at <= now() then
    update ai_business_os_prod.approval_inbox
      set status='EXPIRED'
      where id=v_row.id;
    raise exception 'approval request expired';
  end if;
  if v_row.intent_hash <> p_intent_hash then
    raise exception 'intent hash mismatch';
  end if;

  select exists(
    select 1 from ai_business_os_prod.autonomy_action_receipts
    where id=p_execution_receipt_id
  ) into v_receipt_exists;

  if not v_receipt_exists then
    raise exception 'execution receipt does not exist';
  end if;

  update ai_business_os_prod.approval_inbox
  set status='CONSUMED',
      consumed_at=now(),
      execution_receipt_id=p_execution_receipt_id
  where id=v_row.id;

  v_event_hash := encode(
    extensions.digest(
      v_row.id::text || '|CONSUMED|' || p_actor || '|' ||
      p_execution_receipt_id::text || '|' || v_row.intent_hash,
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.approval_inbox_events(
    approval_id,event_type,actor,event_payload,event_hash
  ) values (
    v_row.id,
    'CONSUMED',
    p_actor,
    jsonb_build_object(
      'execution_receipt_id',p_execution_receipt_id,
      'intent_hash',v_row.intent_hash
    ),
    v_event_hash
  );

  return query
  select v_row.request_key, 'CONSUMED'::text, v_row.decision_receipt_hash;
end;
$$;


-- MIGRATION 20260924215407 add_ai_business_os_approval_queue_view_v1

create or replace view ai_business_os_prod.approval_inbox_queue
with (security_invoker = true)
as
select
  id,
  request_key,
  agent_id,
  action_key,
  action_class,
  title,
  summary,
  exact_parameters,
  intent_hash,
  evidence_refs,
  predicted_risk,
  expected_cost_units,
  expected_money_cents,
  rollback_plan,
  status,
  expires_at,
  created_at,
  decided_at,
  decided_by,
  decision_reason,
  decision_receipt_hash,
  consumed_at
from ai_business_os_prod.approval_inbox
where status in ('PENDING','APPROVED')
order by
  case status when 'PENDING' then 0 else 1 end,
  expires_at,
  created_at;


-- MIGRATION 20260924215624 create_ai_business_os_ceo_command_center_v1

alter table ai_business_os_prod.approval_inbox
  add column if not exists business_id uuid references ai_business_os_prod.businesses(id);

create index if not exists idx_approval_inbox_business_status
  on ai_business_os_prod.approval_inbox(business_id, status);

insert into ai_business_os_prod.businesses(slug,name,status,metadata)
values
('capturebrief','CaptureBrief','ACTIVE','{"verified_by":["stripe_live_account","github_repo","gmail_outreach"]}'::jsonb),
('freightrecovery','FreightRecovery','ACTIVE','{"verified_by":["stripe_live_account","drive_controlled_pilot","gmail_outreach"]}'::jsonb),
('recoveryos','RecoveryOS','ACTIVE','{"verified_by":["stripe_live_account"]}'::jsonb),
('starblox','StarBlox','ACTIVE','{"verified_by":["github_repo","replit_app"]}'::jsonb)
on conflict (slug) do update set
  name=excluded.name,
  status=excluded.status,
  metadata=excluded.metadata,
  updated_at=now();

insert into ai_business_os_prod.products(business_id,slug,name,lifecycle,metadata)
select id,'capturebrief','CaptureBrief','PILOT','{"evidence":["github:capturebrief","stripe:CaptureBrief","gmail:outreach"]}'::jsonb
from ai_business_os_prod.businesses where slug='capturebrief'
on conflict (business_id,slug) do update set lifecycle=excluded.lifecycle,metadata=excluded.metadata,updated_at=now();

insert into ai_business_os_prod.products(business_id,slug,name,lifecycle,metadata)
select id,'freightrecovery','FreightRecovery','PILOT','{"evidence":["drive:controlled-pilot","stripe:FreightRecovery","gmail:outreach"]}'::jsonb
from ai_business_os_prod.businesses where slug='freightrecovery'
on conflict (business_id,slug) do update set lifecycle=excluded.lifecycle,metadata=excluded.metadata,updated_at=now();

insert into ai_business_os_prod.products(business_id,slug,name,lifecycle,metadata)
select id,'recoveryos','RecoveryOS','EXPERIMENT','{"evidence":["stripe:RecoveryOS"],"lifecycle_confidence":"LOW"}'::jsonb
from ai_business_os_prod.businesses where slug='recoveryos'
on conflict (business_id,slug) do update set lifecycle=excluded.lifecycle,metadata=excluded.metadata,updated_at=now();

insert into ai_business_os_prod.products(business_id,slug,name,lifecycle,metadata)
select id,'starblox','StarBlox','BUILD','{"evidence":["github:StarBlox","replit:StarBlox"],"replit_read_status":"TIMEOUT"}'::jsonb
from ai_business_os_prod.businesses where slug='starblox'
on conflict (business_id,slug) do update set lifecycle=excluded.lifecycle,metadata=excluded.metadata,updated_at=now();

insert into ai_business_os_prod.repositories(product_id,provider,repo_full_name,default_branch,frozen_ref,rights_status,metadata)
select p.id,'github','P00NSMASHER/capturebrief','main',null,'OWNER_CONTROLLED','{"source":"github_connected_repo"}'::jsonb
from ai_business_os_prod.products p
join ai_business_os_prod.businesses b on b.id=p.business_id
where b.slug='capturebrief' and p.slug='capturebrief'
on conflict (repo_full_name) do update set
  product_id=excluded.product_id,
  default_branch=excluded.default_branch,
  rights_status=excluded.rights_status,
  metadata=excluded.metadata,
  updated_at=now();

insert into ai_business_os_prod.repositories(product_id,provider,repo_full_name,default_branch,frozen_ref,rights_status,metadata)
select p.id,'github','P00NSMASHER/StarBlox','main',null,'OWNER_CONTROLLED','{"source":"github_connected_repo"}'::jsonb
from ai_business_os_prod.products p
join ai_business_os_prod.businesses b on b.id=p.business_id
where b.slug='starblox' and p.slug='starblox'
on conflict (repo_full_name) do update set
  product_id=excluded.product_id,
  default_branch=excluded.default_branch,
  rights_status=excluded.rights_status,
  metadata=excluded.metadata,
  updated_at=now();

-- Current live Stripe balances: a balance of zero is not treated as lifetime revenue.
insert into ai_business_os_prod.metrics(
  business_id,metric_key,metric_value,unit,observed_at,source_ref,source_sha256,metadata
)
select b.id,'stripe_available_balance_cents',0,'cents',now(),
       'stripe:__PRIVATE_STRIPE_ACCOUNT_ID_1__:balance',
       encode(extensions.digest('stripe:__PRIVATE_STRIPE_ACCOUNT_ID_1__:available:0:usd:2026-09-24','sha256'),'hex'),
       '{"currency":"usd","livemode":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='capturebrief'
union all
select b.id,'stripe_available_balance_cents',0,'cents',now(),
       'stripe:__PRIVATE_STRIPE_ACCOUNT_ID_2__:balance',
       encode(extensions.digest('stripe:__PRIVATE_STRIPE_ACCOUNT_ID_2__:available:0:usd:2026-09-24','sha256'),'hex'),
       '{"currency":"usd","livemode":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='freightrecovery'
union all
select b.id,'stripe_available_balance_cents',0,'cents',now(),
       'stripe:__PRIVATE_STRIPE_ACCOUNT_ID_3__:balance',
       encode(extensions.digest('stripe:__PRIVATE_STRIPE_ACCOUNT_ID_3__:available:0:usd:2026-09-24','sha256'),'hex'),
       '{"currency":"usd","livemode":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='recoveryos';

insert into ai_business_os_prod.metrics(
  business_id,metric_key,metric_value,unit,observed_at,source_ref,source_sha256,metadata
)
select b.id,'stripe_pending_balance_cents',0,'cents',now(),
       'stripe:__PRIVATE_STRIPE_ACCOUNT_ID_1__:balance',
       encode(extensions.digest('stripe:__PRIVATE_STRIPE_ACCOUNT_ID_1__:pending:0:usd:2026-09-24','sha256'),'hex'),
       '{"currency":"usd","livemode":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='capturebrief'
union all
select b.id,'stripe_pending_balance_cents',0,'cents',now(),
       'stripe:__PRIVATE_STRIPE_ACCOUNT_ID_2__:balance',
       encode(extensions.digest('stripe:__PRIVATE_STRIPE_ACCOUNT_ID_2__:pending:0:usd:2026-09-24','sha256'),'hex'),
       '{"currency":"usd","livemode":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='freightrecovery'
union all
select b.id,'stripe_pending_balance_cents',0,'cents',now(),
       'stripe:__PRIVATE_STRIPE_ACCOUNT_ID_3__:balance',
       encode(extensions.digest('stripe:__PRIVATE_STRIPE_ACCOUNT_ID_3__:pending:0:usd:2026-09-24','sha256'),'hex'),
       '{"currency":"usd","livemode":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='recoveryos';

-- Observed sample activity only; labels explicitly avoid claiming exhaustive totals.
insert into ai_business_os_prod.metrics(
  business_id,metric_key,metric_value,unit,observed_at,source_ref,source_sha256,metadata
)
select b.id,'shadow_sample_outreach_sent_count',3,'emails',now(),
       'gmail:bootstrap-shadow-001:capturebrief',
       encode(extensions.digest('gmail:bootstrap-shadow-001:capturebrief:observed-3','sha256'),'hex'),
       '{"sample_only":true,"not_exhaustive":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='capturebrief'
union all
select b.id,'shadow_sample_outreach_sent_count',5,'emails',now(),
       'gmail:bootstrap-shadow-001:freightrecovery',
       encode(extensions.digest('gmail:bootstrap-shadow-001:freightrecovery:observed-5','sha256'),'hex'),
       '{"sample_only":true,"not_exhaustive":true}'::jsonb
from ai_business_os_prod.businesses b where b.slug='freightrecovery';

update ai_business_os_prod.approval_inbox a
set business_id=b.id
from ai_business_os_prod.businesses b
where a.request_key='govcon-calibration-300-approval-001'
  and b.slug='capturebrief';

create table if not exists ai_business_os_prod.command_center_snapshots (
  id uuid primary key default gen_random_uuid(),
  snapshot_key text not null unique,
  snapshot_hash text not null unique check (snapshot_hash ~ '^[0-9a-f]{64}$'),
  payload jsonb not null,
  generated_at timestamptz not null default now()
);

alter table ai_business_os_prod.command_center_snapshots enable row level security;
revoke all on ai_business_os_prod.command_center_snapshots
from public, anon, authenticated;

create or replace view ai_business_os_prod.command_center_portfolio_v1
with (security_invoker = true)
as
with latest_metrics as (
  select distinct on (business_id, metric_key)
    business_id,metric_key,metric_value,unit,observed_at,source_ref
  from ai_business_os_prod.metrics
  order by business_id,metric_key,observed_at desc,created_at desc
),
financials as (
  select
    business_id,
    sum(amount_cents) filter (where event_type='COLLECTED') as collected_revenue_cents,
    sum(amount_cents) filter (where event_type='COST') as cost_cents
  from ai_business_os_prod.financial_events
  group by business_id
),
pipeline as (
  select
    business_id,
    count(*) filter (where stage not in ('CLOSED_WON','CLOSED_LOST')) as open_opportunities,
    sum(expected_value_cents) filter (where stage not in ('CLOSED_WON','CLOSED_LOST')) as open_pipeline_cents
  from ai_business_os_prod.opportunities
  group by business_id
),
experiments as (
  select
    business_id,
    count(*) filter (where status='RUNNING') as running_experiments,
    count(*) filter (where status='PASSED') as passed_experiments,
    count(*) filter (where status='FAILED') as failed_experiments
  from ai_business_os_prod.experiments
  group by business_id
),
approvals as (
  select
    business_id,
    count(*) filter (where status='PENDING') as pending_approvals,
    sum(expected_money_cents) filter (where status='PENDING') as pending_approval_money_cents
  from ai_business_os_prod.approval_inbox
  group by business_id
),
alerts as (
  select
    business_id,
    count(*) filter (where status='OPEN') as open_alerts,
    count(*) filter (where status='OPEN' and severity in ('HIGH','CRITICAL')) as high_alerts
  from ai_business_os_prod.alerts
  group by business_id
),
products_rollup as (
  select
    p.business_id,
    jsonb_agg(
      jsonb_build_object(
        'slug',p.slug,
        'name',p.name,
        'lifecycle',p.lifecycle,
        'metadata',p.metadata
      )
      order by p.name
    ) as products
  from ai_business_os_prod.products p
  group by p.business_id
)
select
  b.id as business_id,
  b.slug,
  b.name,
  b.status,
  pr.products,
  f.collected_revenue_cents,
  f.cost_cents,
  p.open_opportunities,
  p.open_pipeline_cents,
  e.running_experiments,
  e.passed_experiments,
  e.failed_experiments,
  a.pending_approvals,
  a.pending_approval_money_cents,
  al.open_alerts,
  al.high_alerts,
  (select metric_value from latest_metrics lm where lm.business_id=b.id and lm.metric_key='stripe_available_balance_cents') as stripe_available_balance_cents,
  (select metric_value from latest_metrics lm where lm.business_id=b.id and lm.metric_key='stripe_pending_balance_cents') as stripe_pending_balance_cents,
  (select metric_value from latest_metrics lm where lm.business_id=b.id and lm.metric_key='shadow_sample_outreach_sent_count') as observed_shadow_outreach_count,
  (
    (case when f.collected_revenue_cents is not null then 1 else 0 end) +
    (case when p.open_pipeline_cents is not null then 1 else 0 end) +
    (case when e.running_experiments is not null then 1 else 0 end) +
    (case when exists(select 1 from latest_metrics lm where lm.business_id=b.id and lm.metric_key='stripe_available_balance_cents') then 1 else 0 end)
  )::numeric / 4.0 as evidence_coverage
from ai_business_os_prod.businesses b
left join products_rollup pr on pr.business_id=b.id
left join financials f on f.business_id=b.id
left join pipeline p on p.business_id=b.id
left join experiments e on e.business_id=b.id
left join approvals a on a.business_id=b.id
left join alerts al on al.business_id=b.id
where b.status='ACTIVE'
order by b.name;

create or replace view ai_business_os_prod.command_center_agents_v1
with (security_invoker = true)
as
select
  a.agent_id,
  a.display_name,
  a.role_key,
  a.mode,
  a.status,
  h.last_heartbeat_at,
  b.max_actions,
  b.max_cost_units,
  b.max_money_cents,
  count(distinct g.id) filter (where g.status in ('PENDING','ACTIVE','BLOCKED','VERIFYING')) as open_goals,
  count(distinct r.id) filter (where r.outcome='SUCCEEDED') as successful_action_receipts
from ai_business_os_prod.agents a
left join ai_business_os_prod.agent_heartbeats h on h.agent_id=a.agent_id
left join ai_business_os_prod.agent_budgets b on b.agent_id=a.agent_id
left join ai_business_os_prod.agent_goals g on g.agent_id=a.agent_id
left join ai_business_os_prod.autonomy_action_receipts r on r.agent_id=a.agent_id
group by
  a.agent_id,a.display_name,a.role_key,a.mode,a.status,
  h.last_heartbeat_at,b.max_actions,b.max_cost_units,b.max_money_cents
order by a.display_name;

create or replace view ai_business_os_prod.command_center_system_v1
with (security_invoker = true)
as
select
  (select count(*) from ai_business_os_prod.approval_inbox where status='PENDING') as pending_approvals,
  (select count(*) from ai_business_os_prod.alerts where status='OPEN') as open_alerts,
  (select count(*) from ai_business_os_prod.incidents where status='OPEN') as open_incidents,
  (select count(*) from ai_business_os_prod.shadow_runs where status='COMPLETE') as completed_shadow_runs,
  (select count(*) from ai_business_os_prod.tool_providers where enabled) as enabled_tool_providers,
  (select count(*) from ai_business_os_prod.tool_providers where not enabled) as disabled_tool_providers,
  (select count(*) from ai_business_os_prod.autonomy_policies where autonomy_status='ENABLED') as enabled_autonomy_policies,
  (
    select count(*)
    from ai_business_os_prod.autonomy_policies p
    join ai_business_os_prod.tool_actions t on t.action_key=p.action_key
    where p.autonomy_status='ENABLED'
      and t.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','MONEY_MOVEMENT','DESTRUCTIVE','POLICY_CHANGE')
  ) as consequential_autonomy_enabled,
  (select count(*) from ai_business_os_prod.agents where mode='LOW_RISK_AUTONOMY') as low_risk_agents,
  (select count(*) from ai_business_os_prod.agents where mode='SHADOW') as shadow_agents;

create or replace function ai_business_os_prod.refresh_command_center_snapshot(
  p_snapshot_key text
) returns table (
  snapshot_key text,
  snapshot_hash text,
  generated_at timestamptz
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_payload jsonb;
  v_hash text;
  v_generated timestamptz := now();
begin
  if coalesce(trim(p_snapshot_key),'')='' then
    raise exception 'snapshot key required';
  end if;

  select jsonb_build_object(
    'generated_at',v_generated,
    'system',(select to_jsonb(s) from ai_business_os_prod.command_center_system_v1 s),
    'portfolio',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from ai_business_os_prod.command_center_portfolio_v1 p),'[]'::jsonb),
    'agents',coalesce((select jsonb_agg(to_jsonb(a) order by a.display_name) from ai_business_os_prod.command_center_agents_v1 a),'[]'::jsonb),
    'approval_queue',coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'request_key',q.request_key,
          'business_id',q.business_id,
          'title',q.title,
          'action_key',q.action_key,
          'status',q.status,
          'predicted_risk',q.predicted_risk,
          'expected_money_cents',q.expected_money_cents,
          'expires_at',q.expires_at,
          'intent_hash',q.intent_hash
        )
        order by q.expires_at
      )
      from ai_business_os_prod.approval_inbox q
      where q.status in ('PENDING','APPROVED')
    ),'[]'::jsonb)
  ) into v_payload;

  v_hash := encode(extensions.digest(v_payload::text,'sha256'),'hex');

  insert into ai_business_os_prod.command_center_snapshots(
    snapshot_key,snapshot_hash,payload,generated_at
  ) values (
    p_snapshot_key,v_hash,v_payload,v_generated
  )
  on conflict (snapshot_key) do update set
    snapshot_hash=excluded.snapshot_hash,
    payload=excluded.payload,
    generated_at=excluded.generated_at;

  return query select p_snapshot_key,v_hash,v_generated;
end;
$$;

revoke execute on function ai_business_os_prod.refresh_command_center_snapshot(text)
from public, anon, authenticated;


-- MIGRATION 20260924215702 replace_ai_business_os_command_center_snapshot_function_v1

drop function if exists ai_business_os_prod.refresh_command_center_snapshot(text);

create function ai_business_os_prod.refresh_command_center_snapshot(
  p_snapshot_key text
) returns table (
  out_snapshot_key text,
  out_snapshot_hash text,
  out_generated_at timestamptz
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_payload jsonb;
  v_hash text;
  v_generated timestamptz := now();
begin
  if coalesce(trim(p_snapshot_key),'')='' then
    raise exception 'snapshot key required';
  end if;

  select jsonb_build_object(
    'generated_at',v_generated,
    'system',(select to_jsonb(s) from ai_business_os_prod.command_center_system_v1 s),
    'portfolio',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from ai_business_os_prod.command_center_portfolio_v1 p),'[]'::jsonb),
    'agents',coalesce((select jsonb_agg(to_jsonb(a) order by a.display_name) from ai_business_os_prod.command_center_agents_v1 a),'[]'::jsonb),
    'approval_queue',coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'request_key',q.request_key,
          'business_id',q.business_id,
          'title',q.title,
          'action_key',q.action_key,
          'status',q.status,
          'predicted_risk',q.predicted_risk,
          'expected_money_cents',q.expected_money_cents,
          'expires_at',q.expires_at,
          'intent_hash',q.intent_hash
        )
        order by q.expires_at
      )
      from ai_business_os_prod.approval_inbox q
      where q.status in ('PENDING','APPROVED')
    ),'[]'::jsonb)
  ) into v_payload;

  v_hash := encode(extensions.digest(v_payload::text,'sha256'),'hex');

  insert into ai_business_os_prod.command_center_snapshots(
    snapshot_key,snapshot_hash,payload,generated_at
  ) values (
    p_snapshot_key,v_hash,v_payload,v_generated
  )
  on conflict on constraint command_center_snapshots_snapshot_key_key
  do update set
    snapshot_hash=excluded.snapshot_hash,
    payload=excluded.payload,
    generated_at=excluded.generated_at;

  return query select p_snapshot_key,v_hash,v_generated;
end;
$$;

revoke execute on function ai_business_os_prod.refresh_command_center_snapshot(text)
from public, anon, authenticated;


-- MIGRATION 20260924215735 add_ai_business_os_command_center_latest_view_v1

create or replace view ai_business_os_prod.command_center_latest_v1
with (security_invoker = true)
as
select snapshot_key,snapshot_hash,payload,generated_at
from ai_business_os_prod.command_center_snapshots
order by generated_at desc
limit 1;


-- MIGRATION 20260924220147 create_ai_business_os_revenue_loop_v1

create table if not exists ai_business_os_prod.revenue_loops (
  id uuid primary key default gen_random_uuid(),
  loop_key text not null unique,
  business_id uuid not null references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  stage text not null default 'DETECTED'
    check (stage in (
      'DETECTED','EVIDENCE_READY','ECONOMICS_READY','BUYERS_READY',
      'EXPERIMENT_READY','AWAITING_APPROVAL','EXECUTING','MEASURING',
      'ATTRIBUTED','LEARNED','STOPPED'
    )),
  title text not null,
  objective text not null,
  owner_agent_id text not null references ai_business_os_prod.agents(agent_id),
  current_action_key text references ai_business_os_prod.tool_actions(action_key),
  stage_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.revenue_loop_economics (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  version integer not null,
  pricing_status text not null
    check (pricing_status in (
      'VERIFIED_OFFER','PILOT_FREE_PRICING_DEFERRED',
      'WORKING_ASSUMPTION','UNKNOWN'
    )),
  upfront_price_cents bigint check (upfront_price_cents is null or upfront_price_cents >= 0),
  contingency_rate_bps integer check (
    contingency_rate_bps is null or contingency_rate_bps between 0 and 10000
  ),
  value_basis text,
  source_ref text not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  effective_at timestamptz not null,
  customer_facing boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(loop_id,version)
);

create table if not exists ai_business_os_prod.revenue_loop_opportunities (
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  opportunity_id uuid not null references ai_business_os_prod.opportunities(id),
  relationship text not null default 'TARGET',
  created_at timestamptz not null default now(),
  primary key(loop_id,opportunity_id)
);

create table if not exists ai_business_os_prod.revenue_loop_executions (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  action_key text references ai_business_os_prod.tool_actions(action_key),
  execution_mode text not null
    check (execution_mode in ('HISTORICAL_OBSERVED','APPROVAL_GATED','LOW_RISK_INTERNAL')),
  approval_request_key text references ai_business_os_prod.approval_inbox(request_key),
  execution_receipt_id uuid references ai_business_os_prod.autonomy_action_receipts(id),
  source_ref text not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  executed_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (
    execution_mode <> 'APPROVAL_GATED'
    or approval_request_key is not null
  )
);

create table if not exists ai_business_os_prod.revenue_loop_measurements (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  metric_key text not null,
  metric_value numeric not null,
  unit text not null,
  window_start timestamptz,
  window_end timestamptz,
  source_ref text not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  verified boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  observed_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.revenue_loop_outcomes (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  outcome_type text not null,
  outcome_value_cents bigint,
  outcome_value_numeric numeric,
  unit text,
  verified boolean not null default false,
  source_ref text not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  occurred_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.revenue_loop_attribution (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  outcome_id uuid not null references ai_business_os_prod.revenue_loop_outcomes(id),
  attributed_type text not null
    check (attributed_type in ('EXPERIMENT','PRODUCT','BUSINESS','CAPABILITY','MEMORY')),
  attributed_key text not null,
  attribution_fraction numeric not null
    check (attribution_fraction > 0 and attribution_fraction <= 1),
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.revenue_loop_learning (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  memory_id uuid references ai_business_os_prod.memory_items(id),
  memory_observation_id uuid references ai_business_os_prod.memory_observations(id),
  learning_status text not null
    check (learning_status in ('PROPOSED','VERIFIED','REJECTED')),
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.revenue_loop_events (
  id uuid primary key default gen_random_uuid(),
  loop_id uuid not null references ai_business_os_prod.revenue_loops(id),
  from_stage text,
  to_stage text not null,
  actor text not null,
  reason text not null,
  event_hash text not null unique check (event_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

alter table ai_business_os_prod.revenue_loops enable row level security;
alter table ai_business_os_prod.revenue_loop_economics enable row level security;
alter table ai_business_os_prod.revenue_loop_opportunities enable row level security;
alter table ai_business_os_prod.revenue_loop_executions enable row level security;
alter table ai_business_os_prod.revenue_loop_measurements enable row level security;
alter table ai_business_os_prod.revenue_loop_outcomes enable row level security;
alter table ai_business_os_prod.revenue_loop_attribution enable row level security;
alter table ai_business_os_prod.revenue_loop_learning enable row level security;
alter table ai_business_os_prod.revenue_loop_events enable row level security;

revoke all on ai_business_os_prod.revenue_loops,
  ai_business_os_prod.revenue_loop_economics,
  ai_business_os_prod.revenue_loop_opportunities,
  ai_business_os_prod.revenue_loop_executions,
  ai_business_os_prod.revenue_loop_measurements,
  ai_business_os_prod.revenue_loop_outcomes,
  ai_business_os_prod.revenue_loop_attribution,
  ai_business_os_prod.revenue_loop_learning,
  ai_business_os_prod.revenue_loop_events
from public, anon, authenticated;

create index if not exists idx_revenue_loops_business_stage
  on ai_business_os_prod.revenue_loops(business_id,stage);
create index if not exists idx_revenue_loop_executions_loop
  on ai_business_os_prod.revenue_loop_executions(loop_id,executed_at desc);
create index if not exists idx_revenue_loop_measurements_loop
  on ai_business_os_prod.revenue_loop_measurements(loop_id,observed_at desc);
create index if not exists idx_revenue_loop_outcomes_loop
  on ai_business_os_prod.revenue_loop_outcomes(loop_id,occurred_at desc);
create index if not exists idx_revenue_loop_attribution_outcome
  on ai_business_os_prod.revenue_loop_attribution(outcome_id);

create or replace function ai_business_os_prod.revenue_loop_transition(
  p_loop_key text,
  p_to_stage text,
  p_actor text,
  p_reason text
) returns table (
  loop_key text,
  stage text,
  event_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v ai_business_os_prod.revenue_loops%rowtype;
  v_event_hash text;
  v_ok boolean := false;
  v_count integer;
begin
  if coalesce(trim(p_actor),'')='' or coalesce(trim(p_reason),'')='' then
    raise exception 'actor and reason required';
  end if;

  select * into v
  from ai_business_os_prod.revenue_loops
  where revenue_loops.loop_key=p_loop_key
  for update;

  if not found then raise exception 'unknown revenue loop'; end if;
  if v.stage=p_to_stage then raise exception 'loop already at requested stage'; end if;

  if v.stage='DETECTED' and p_to_stage='EVIDENCE_READY' then
    select count(*) into v_count
    from ai_business_os_prod.evidence e
    where e.business_id=v.business_id;
    v_ok := v_count > 0;

  elsif v.stage='EVIDENCE_READY' and p_to_stage='ECONOMICS_READY' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_economics e
      where e.loop_id=v.id and e.pricing_status <> 'UNKNOWN'
    ) into v_ok;

  elsif v.stage='ECONOMICS_READY' and p_to_stage='BUYERS_READY' then
    select exists(
      select 1
      from ai_business_os_prod.revenue_loop_opportunities ro
      join ai_business_os_prod.opportunities o on o.id=ro.opportunity_id
      where ro.loop_id=v.id
        and (o.prospect_id is not null or o.customer_id is not null)
    ) into v_ok;

  elsif v.stage='BUYERS_READY' and p_to_stage='EXPERIMENT_READY' then
    select exists(
      select 1 from ai_business_os_prod.experiments e
      where e.business_id=v.business_id
        and (e.product_id=v.product_id or v.product_id is null)
        and e.status in ('PLANNED','RUNNING')
    ) into v_ok;

  elsif v.stage='EXPERIMENT_READY' and p_to_stage='AWAITING_APPROVAL' then
    v_ok := v.current_action_key is not null
      and exists(
        select 1 from ai_business_os_prod.tool_actions t
        where t.action_key=v.current_action_key
          and t.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','MONEY_MOVEMENT','DESTRUCTIVE','POLICY_CHANGE')
      );

  elsif v.stage='EXPERIMENT_READY' and p_to_stage='MEASURING' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_executions x
      where x.loop_id=v.id and x.execution_mode='HISTORICAL_OBSERVED'
    ) into v_ok;

  elsif v.stage='AWAITING_APPROVAL' and p_to_stage='EXECUTING' then
    select exists(
      select 1
      from ai_business_os_prod.revenue_loop_executions x
      join ai_business_os_prod.approval_inbox a
        on a.request_key=x.approval_request_key
      where x.loop_id=v.id
        and x.execution_mode='APPROVAL_GATED'
        and a.status='CONSUMED'
    ) into v_ok;

  elsif v.stage='EXECUTING' and p_to_stage='MEASURING' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_executions x
      where x.loop_id=v.id
        and x.execution_receipt_id is not null
    ) into v_ok;

  elsif v.stage='MEASURING' and p_to_stage='ATTRIBUTED' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_outcomes o
      where o.loop_id=v.id and o.verified=true
    ) into v_ok;

  elsif v.stage='ATTRIBUTED' and p_to_stage='LEARNED' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_learning l
      where l.loop_id=v.id and l.learning_status='VERIFIED'
    ) into v_ok;

  elsif p_to_stage='STOPPED' then
    v_ok := true;
  end if;

  if not v_ok then
    raise exception 'revenue loop gate not satisfied for % -> %', v.stage, p_to_stage;
  end if;

  v_event_hash := encode(
    extensions.digest(
      v.id::text || '|' || v.stage || '|' || p_to_stage || '|' ||
      p_actor || '|' || p_reason || '|' || clock_timestamp()::text,
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.revenue_loop_events(
    loop_id,from_stage,to_stage,actor,reason,event_hash
  ) values (
    v.id,v.stage,p_to_stage,p_actor,p_reason,v_event_hash
  );

  update ai_business_os_prod.revenue_loops
  set stage=p_to_stage,stage_reason=p_reason,updated_at=now()
  where id=v.id;

  return query select v.loop_key,p_to_stage,v_event_hash;
end;
$$;

revoke execute on function ai_business_os_prod.revenue_loop_transition(text,text,text,text)
from public, anon, authenticated;


-- MIGRATION 20260924220230 harden_ai_business_os_revenue_loop_identity_v1

alter table ai_business_os_prod.opportunities
  add column if not exists opportunity_key text;

create unique index if not exists uq_opportunities_business_key
  on ai_business_os_prod.opportunities(business_id,opportunity_key)
  where opportunity_key is not null;

create unique index if not exists uq_evidence_business_source_hash
  on ai_business_os_prod.evidence(business_id,source_ref,source_sha256);

create unique index if not exists uq_revenue_loop_measurement_source
  on ai_business_os_prod.revenue_loop_measurements(loop_id,metric_key,source_ref);

create unique index if not exists uq_revenue_loop_execution_source
  on ai_business_os_prod.revenue_loop_executions(loop_id,source_ref);


-- MIGRATION 20260924220522 add_ai_business_os_revenue_loop_command_center_v1

create index if not exists idx_revenue_loop_opportunities_opportunity
  on ai_business_os_prod.revenue_loop_opportunities(opportunity_id);
create index if not exists idx_revenue_loop_learning_memory
  on ai_business_os_prod.revenue_loop_learning(memory_id);
create index if not exists idx_revenue_loop_learning_observation
  on ai_business_os_prod.revenue_loop_learning(memory_observation_id);
create index if not exists idx_revenue_loop_economics_loop
  on ai_business_os_prod.revenue_loop_economics(loop_id,version desc);
create index if not exists idx_revenue_loop_events_loop
  on ai_business_os_prod.revenue_loop_events(loop_id,created_at);

create or replace view ai_business_os_prod.command_center_revenue_loops_v1
with (security_invoker = true)
as
with latest_economics as (
  select distinct on (loop_id)
    loop_id,pricing_status,upfront_price_cents,contingency_rate_bps,value_basis
  from ai_business_os_prod.revenue_loop_economics
  order by loop_id,version desc
),
buyers as (
  select loop_id,count(*) as buyer_count
  from ai_business_os_prod.revenue_loop_opportunities
  group by loop_id
),
measurements as (
  select
    loop_id,
    max(metric_value) filter (where metric_key='outreach_sent_count') as outreach_sent_count,
    max(metric_value) filter (where metric_key='external_reply_count') as external_reply_count,
    max(observed_at) as last_measured_at
  from ai_business_os_prod.revenue_loop_measurements
  where verified=true
  group by loop_id
),
outcomes as (
  select
    loop_id,
    count(*) filter (where verified=true) as verified_outcomes
  from ai_business_os_prod.revenue_loop_outcomes
  group by loop_id
),
learning as (
  select
    loop_id,
    count(*) filter (where learning_status='VERIFIED') as verified_learning_items
  from ai_business_os_prod.revenue_loop_learning
  group by loop_id
)
select
  l.loop_key,
  b.slug as business_slug,
  b.name as business_name,
  l.title,
  l.stage,
  l.stage_reason,
  l.owner_agent_id,
  l.current_action_key,
  e.pricing_status,
  e.upfront_price_cents,
  e.contingency_rate_bps,
  e.value_basis,
  coalesce(bu.buyer_count,0) as buyer_count,
  m.outreach_sent_count,
  m.external_reply_count,
  m.last_measured_at,
  coalesce(o.verified_outcomes,0) as verified_outcomes,
  coalesce(le.verified_learning_items,0) as verified_learning_items,
  case
    when l.stage='MEASURING' and coalesce(o.verified_outcomes,0)=0
      then 'WAIT_FOR_VERIFIED_OUTCOME'
    when l.stage='ATTRIBUTED' and coalesce(le.verified_learning_items,0)=0
      then 'VERIFY_LEARNING'
    when l.stage='AWAITING_APPROVAL'
      then 'HUMAN_APPROVAL'
    else 'FOLLOW_STAGE_GATE'
  end as next_gate
from ai_business_os_prod.revenue_loops l
join ai_business_os_prod.businesses b on b.id=l.business_id
left join latest_economics e on e.loop_id=l.id
left join buyers bu on bu.loop_id=l.id
left join measurements m on m.loop_id=l.id
left join outcomes o on o.loop_id=l.id
left join learning le on le.loop_id=l.id
order by b.name,l.loop_key;

drop function if exists ai_business_os_prod.refresh_command_center_snapshot(text);

create function ai_business_os_prod.refresh_command_center_snapshot(
  p_snapshot_key text
) returns table (
  out_snapshot_key text,
  out_snapshot_hash text,
  out_generated_at timestamptz
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_payload jsonb;
  v_hash text;
  v_generated timestamptz := now();
begin
  if coalesce(trim(p_snapshot_key),'')='' then
    raise exception 'snapshot key required';
  end if;

  select jsonb_build_object(
    'generated_at',v_generated,
    'system',(select to_jsonb(s) from ai_business_os_prod.command_center_system_v1 s),
    'portfolio',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from ai_business_os_prod.command_center_portfolio_v1 p),'[]'::jsonb),
    'agents',coalesce((select jsonb_agg(to_jsonb(a) order by a.display_name) from ai_business_os_prod.command_center_agents_v1 a),'[]'::jsonb),
    'revenue_loops',coalesce((select jsonb_agg(to_jsonb(r) order by r.business_name,r.loop_key) from ai_business_os_prod.command_center_revenue_loops_v1 r),'[]'::jsonb),
    'approval_queue',coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'request_key',q.request_key,
          'business_id',q.business_id,
          'title',q.title,
          'action_key',q.action_key,
          'status',q.status,
          'predicted_risk',q.predicted_risk,
          'expected_money_cents',q.expected_money_cents,
          'expires_at',q.expires_at,
          'intent_hash',q.intent_hash
        )
        order by q.expires_at
      )
      from ai_business_os_prod.approval_inbox q
      where q.status in ('PENDING','APPROVED')
    ),'[]'::jsonb)
  ) into v_payload;

  v_hash := encode(extensions.digest(v_payload::text,'sha256'),'hex');

  insert into ai_business_os_prod.command_center_snapshots(
    snapshot_key,snapshot_hash,payload,generated_at
  ) values (
    p_snapshot_key,v_hash,v_payload,v_generated
  )
  on conflict on constraint command_center_snapshots_snapshot_key_key
  do update set
    snapshot_hash=excluded.snapshot_hash,
    payload=excluded.payload,
    generated_at=excluded.generated_at;

  return query select p_snapshot_key,v_hash,v_generated;
end;
$$;

revoke execute on function ai_business_os_prod.refresh_command_center_snapshot(text)
from public, anon, authenticated;


-- MIGRATION 20260924220542 index_ai_business_os_control_plane_fks_v1

create index if not exists idx_agents_parent on ai_business_os_prod.agents(parent_agent_id);
create index if not exists idx_approval_inbox_action on ai_business_os_prod.approval_inbox(action_key);
create index if not exists idx_approval_inbox_execution_receipt on ai_business_os_prod.approval_inbox(execution_receipt_id);
create index if not exists idx_autonomy_receipts_action on ai_business_os_prod.autonomy_action_receipts(action_key);
create index if not exists idx_autonomy_policies_action on ai_business_os_prod.autonomy_policies(action_key);
create index if not exists idx_autonomy_policies_shadow on ai_business_os_prod.autonomy_policies(promoted_from_shadow_run_id);
create index if not exists idx_revenue_loop_attribution_loop on ai_business_os_prod.revenue_loop_attribution(loop_id);
create index if not exists idx_revenue_loop_executions_action on ai_business_os_prod.revenue_loop_executions(action_key);
create index if not exists idx_revenue_loop_executions_approval on ai_business_os_prod.revenue_loop_executions(approval_request_key);
create index if not exists idx_revenue_loop_executions_receipt on ai_business_os_prod.revenue_loop_executions(execution_receipt_id);
create index if not exists idx_revenue_loop_learning_loop on ai_business_os_prod.revenue_loop_learning(loop_id);
create index if not exists idx_revenue_loops_current_action on ai_business_os_prod.revenue_loops(current_action_key);
create index if not exists idx_revenue_loops_owner on ai_business_os_prod.revenue_loops(owner_agent_id);
create index if not exists idx_revenue_loops_product on ai_business_os_prod.revenue_loops(product_id);
create index if not exists idx_shadow_observations_agent on ai_business_os_prod.shadow_observations(agent_id);
create index if not exists idx_shadow_observations_provider on ai_business_os_prod.shadow_observations(provider_key);
create index if not exists idx_shadow_recommendations_action on ai_business_os_prod.shadow_recommendations(action_key);
create index if not exists idx_shadow_recommendations_agent on ai_business_os_prod.shadow_recommendations(agent_id);


-- MIGRATION 20260924220743 harden_ai_business_os_revenue_loop_execution_attribution_v1

alter table ai_business_os_prod.revenue_loop_executions
  add column if not exists authorized_at timestamptz;

alter table ai_business_os_prod.revenue_loop_executions
  alter column executed_at drop not null;

update ai_business_os_prod.revenue_loop_executions
set authorized_at=coalesce(authorized_at,executed_at,created_at)
where authorized_at is null;

create or replace function ai_business_os_prod.revenue_prepare_approved_execution(
  p_loop_key text,
  p_approval_request_key text,
  p_actor text,
  p_evidence_hash text
) returns table (
  execution_id uuid,
  loop_key text,
  approval_request_key text,
  action_key text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_loop ai_business_os_prod.revenue_loops%rowtype;
  v_approval ai_business_os_prod.approval_inbox%rowtype;
  v_execution_id uuid;
begin
  if coalesce(trim(p_actor),'')='' then
    raise exception 'actor required';
  end if;
  if p_evidence_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'valid evidence hash required';
  end if;

  select * into v_loop
  from ai_business_os_prod.revenue_loops
  where revenue_loops.loop_key=p_loop_key
  for update;

  if not found then raise exception 'unknown revenue loop'; end if;
  if v_loop.stage <> 'AWAITING_APPROVAL' then
    raise exception 'revenue loop is not awaiting approval';
  end if;
  if v_loop.current_action_key is null then
    raise exception 'revenue loop has no current action';
  end if;

  select * into v_approval
  from ai_business_os_prod.approval_inbox
  where request_key=p_approval_request_key
  for update;

  if not found then raise exception 'unknown approval request'; end if;
  if v_approval.status <> 'APPROVED' then
    raise exception 'approval request must be APPROVED before execution preparation';
  end if;
  if v_approval.expires_at <= now() then
    raise exception 'approval request expired';
  end if;
  if v_approval.action_key <> v_loop.current_action_key then
    raise exception 'approval action does not match revenue-loop action';
  end if;
  if v_approval.business_id is distinct from v_loop.business_id then
    raise exception 'approval business does not match revenue loop';
  end if;

  if exists(
    select 1 from ai_business_os_prod.revenue_loop_executions x
    where x.loop_id=v_loop.id
      and x.execution_mode='APPROVAL_GATED'
      and x.approval_request_key=p_approval_request_key
  ) then
    raise exception 'approved execution is already prepared';
  end if;

  insert into ai_business_os_prod.revenue_loop_executions(
    loop_id,action_key,execution_mode,approval_request_key,
    execution_receipt_id,source_ref,evidence_hash,authorized_at,executed_at,metadata
  ) values (
    v_loop.id,
    v_loop.current_action_key,
    'APPROVAL_GATED',
    p_approval_request_key,
    null,
    'approval:' || p_approval_request_key,
    p_evidence_hash,
    now(),
    null,
    jsonb_build_object(
      'state','AUTHORIZED_NOT_EXECUTED',
      'prepared_by',p_actor,
      'approval_intent_hash',v_approval.intent_hash
    )
  )
  returning id into v_execution_id;

  return query
  select v_execution_id,v_loop.loop_key,p_approval_request_key,v_loop.current_action_key;
end;
$$;

revoke execute on function ai_business_os_prod.revenue_prepare_approved_execution(text,text,text,text)
from public, anon, authenticated;

create or replace function ai_business_os_prod.revenue_record_execution_receipt(
  p_execution_id uuid,
  p_execution_receipt_id uuid,
  p_actor text
) returns table (
  execution_id uuid,
  approval_request_key text,
  execution_receipt_id uuid,
  executed_at timestamptz
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_exec ai_business_os_prod.revenue_loop_executions%rowtype;
  v_receipt ai_business_os_prod.autonomy_action_receipts%rowtype;
  v_approval ai_business_os_prod.approval_inbox%rowtype;
begin
  if coalesce(trim(p_actor),'')='' then
    raise exception 'actor required';
  end if;

  select * into v_exec
  from ai_business_os_prod.revenue_loop_executions
  where id=p_execution_id
  for update;

  if not found then raise exception 'unknown revenue execution'; end if;
  if v_exec.execution_mode <> 'APPROVAL_GATED' then
    raise exception 'execution is not approval-gated';
  end if;
  if v_exec.execution_receipt_id is not null then
    raise exception 'execution receipt already recorded';
  end if;

  select * into v_receipt
  from ai_business_os_prod.autonomy_action_receipts
  where id=p_execution_receipt_id;

  if not found then raise exception 'unknown execution receipt'; end if;
  if v_receipt.outcome <> 'SUCCEEDED' then
    raise exception 'only a successful execution receipt may complete revenue execution';
  end if;
  if v_receipt.action_key is distinct from v_exec.action_key then
    raise exception 'execution receipt action mismatch';
  end if;

  select * into v_approval
  from ai_business_os_prod.approval_inbox
  where request_key=v_exec.approval_request_key
  for update;

  if not found then raise exception 'linked approval missing'; end if;
  if v_approval.status <> 'APPROVED' then
    raise exception 'linked approval must still be APPROVED';
  end if;

  perform *
  from ai_business_os_prod.approval_consume(
    v_exec.approval_request_key,
    v_approval.intent_hash,
    p_execution_receipt_id,
    p_actor
  );

  update ai_business_os_prod.revenue_loop_executions
  set execution_receipt_id=p_execution_receipt_id,
      executed_at=v_receipt.executed_at,
      source_ref=coalesce(v_receipt.evidence_ref,'autonomy-receipt:' || p_execution_receipt_id::text),
      evidence_hash=v_receipt.evidence_hash,
      metadata=coalesce(metadata,'{}'::jsonb) || jsonb_build_object(
        'state','EXECUTED',
        'receipt_bound_by',p_actor
      )
  where id=p_execution_id;

  return query
  select p_execution_id,v_exec.approval_request_key,p_execution_receipt_id,v_receipt.executed_at;
end;
$$;

revoke execute on function ai_business_os_prod.revenue_record_execution_receipt(uuid,uuid,text)
from public, anon, authenticated;

create or replace function ai_business_os_prod.enforce_revenue_attribution_conservation()
returns trigger
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_outcome ai_business_os_prod.revenue_loop_outcomes%rowtype;
  v_existing numeric;
begin
  select * into v_outcome
  from ai_business_os_prod.revenue_loop_outcomes
  where id=new.outcome_id;

  if not found then raise exception 'unknown outcome'; end if;
  if v_outcome.loop_id <> new.loop_id then
    raise exception 'attribution loop does not match outcome loop';
  end if;
  if v_outcome.verified is not true then
    raise exception 'only verified outcomes may be attributed';
  end if;

  select coalesce(sum(attribution_fraction),0)
  into v_existing
  from ai_business_os_prod.revenue_loop_attribution
  where outcome_id=new.outcome_id
    and (tg_op='INSERT' or id<>new.id);

  if v_existing + new.attribution_fraction > 1.000000001 then
    raise exception 'total attribution for an outcome cannot exceed 1.0';
  end if;

  return new;
end;
$$;

drop trigger if exists trg_revenue_attribution_conservation
on ai_business_os_prod.revenue_loop_attribution;

create trigger trg_revenue_attribution_conservation
before insert or update on ai_business_os_prod.revenue_loop_attribution
for each row execute function ai_business_os_prod.enforce_revenue_attribution_conservation();

create or replace function ai_business_os_prod.revenue_loop_transition(
  p_loop_key text,
  p_to_stage text,
  p_actor text,
  p_reason text
) returns table(loop_key text, stage text, event_hash text)
language plpgsql
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v ai_business_os_prod.revenue_loops%rowtype;
  v_event_hash text;
  v_ok boolean := false;
  v_count integer;
begin
  if coalesce(trim(p_actor),'')='' or coalesce(trim(p_reason),'')='' then
    raise exception 'actor and reason required';
  end if;

  select * into v
  from ai_business_os_prod.revenue_loops
  where revenue_loops.loop_key=p_loop_key
  for update;

  if not found then raise exception 'unknown revenue loop'; end if;
  if v.stage=p_to_stage then raise exception 'loop already at requested stage'; end if;

  if v.stage='DETECTED' and p_to_stage='EVIDENCE_READY' then
    select count(*) into v_count
    from ai_business_os_prod.evidence e
    where e.business_id=v.business_id;
    v_ok := v_count > 0;

  elsif v.stage='EVIDENCE_READY' and p_to_stage='ECONOMICS_READY' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_economics e
      where e.loop_id=v.id and e.pricing_status <> 'UNKNOWN'
    ) into v_ok;

  elsif v.stage='ECONOMICS_READY' and p_to_stage='BUYERS_READY' then
    select exists(
      select 1
      from ai_business_os_prod.revenue_loop_opportunities ro
      join ai_business_os_prod.opportunities o on o.id=ro.opportunity_id
      where ro.loop_id=v.id
        and (o.prospect_id is not null or o.customer_id is not null)
    ) into v_ok;

  elsif v.stage='BUYERS_READY' and p_to_stage='EXPERIMENT_READY' then
    select exists(
      select 1 from ai_business_os_prod.experiments e
      where e.business_id=v.business_id
        and (e.product_id=v.product_id or v.product_id is null)
        and e.status in ('PLANNED','RUNNING')
    ) into v_ok;

  elsif v.stage='EXPERIMENT_READY' and p_to_stage='AWAITING_APPROVAL' then
    v_ok := v.current_action_key is not null
      and exists(
        select 1 from ai_business_os_prod.tool_actions t
        where t.action_key=v.current_action_key
          and t.action_class in ('EXTERNAL_WRITE','PRODUCTION_CHANGE','MONEY_MOVEMENT','DESTRUCTIVE','POLICY_CHANGE')
      );

  elsif v.stage='EXPERIMENT_READY' and p_to_stage='MEASURING' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_executions x
      where x.loop_id=v.id and x.execution_mode='HISTORICAL_OBSERVED'
    ) into v_ok;

  elsif v.stage='AWAITING_APPROVAL' and p_to_stage='EXECUTING' then
    select exists(
      select 1
      from ai_business_os_prod.revenue_loop_executions x
      join ai_business_os_prod.approval_inbox a
        on a.request_key=x.approval_request_key
      where x.loop_id=v.id
        and x.action_key=v.current_action_key
        and x.execution_mode='APPROVAL_GATED'
        and x.execution_receipt_id is null
        and x.authorized_at is not null
        and a.status='APPROVED'
        and a.expires_at > now()
        and a.action_key=v.current_action_key
        and a.business_id is not distinct from v.business_id
    ) into v_ok;

  elsif v.stage='EXECUTING' and p_to_stage='MEASURING' then
    select exists(
      select 1
      from ai_business_os_prod.revenue_loop_executions x
      left join ai_business_os_prod.approval_inbox a
        on a.request_key=x.approval_request_key
      where x.loop_id=v.id
        and x.execution_receipt_id is not null
        and x.executed_at is not null
        and (
          (x.execution_mode='APPROVAL_GATED' and a.status='CONSUMED')
          or x.execution_mode='LOW_RISK_INTERNAL'
        )
    ) into v_ok;

  elsif v.stage='MEASURING' and p_to_stage='ATTRIBUTED' then
    select exists(
      select 1 from ai_business_os_prod.revenue_loop_outcomes o
      where o.loop_id=v.id and o.verified=true
    )
    and not exists(
      select 1
      from ai_business_os_prod.revenue_loop_outcomes o
      where o.loop_id=v.id
        and o.verified=true
        and abs(
          1.0 - coalesce((
            select sum(a.attribution_fraction)
            from ai_business_os_prod.revenue_loop_attribution a
            where a.outcome_id=o.id
          ),0)
        ) > 0.000000001
    )
    into v_ok;

  elsif v.stage='ATTRIBUTED' and p_to_stage='LEARNED' then
    select exists(
      select 1
      from ai_business_os_prod.revenue_loop_learning l
      join ai_business_os_prod.memory_observations mo
        on mo.id=l.memory_observation_id
      where l.loop_id=v.id
        and l.learning_status='VERIFIED'
        and mo.verification_status='VERIFIED'
    ) into v_ok;

  elsif p_to_stage='STOPPED' then
    v_ok := true;
  end if;

  if not v_ok then
    raise exception 'revenue loop gate not satisfied for % -> %', v.stage, p_to_stage;
  end if;

  v_event_hash := encode(
    extensions.digest(
      v.id::text || '|' || v.stage || '|' || p_to_stage || '|' ||
      p_actor || '|' || p_reason || '|' || clock_timestamp()::text,
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.revenue_loop_events(
    loop_id,from_stage,to_stage,actor,reason,event_hash
  ) values (
    v.id,v.stage,p_to_stage,p_actor,p_reason,v_event_hash
  );

  update ai_business_os_prod.revenue_loops
  set stage=p_to_stage,stage_reason=p_reason,updated_at=now()
  where id=v.id;

  return query select v.loop_key,p_to_stage,v_event_hash;
end;
$$;

revoke execute on function ai_business_os_prod.revenue_loop_transition(text,text,text,text)
from public, anon, authenticated;


-- MIGRATION 20260924222856 create_ai_business_os_portfolio_allocator_v1

create table if not exists ai_business_os_prod.portfolio_allocator_policies (
  id uuid primary key default gen_random_uuid(),
  policy_key text not null,
  version integer not null,
  config jsonb not null,
  policy_hash text not null unique check (policy_hash ~ '^[0-9a-f]{64}$'),
  updated_by_principal text not null,
  principal_kind text not null check (principal_kind='HUMAN'),
  evidence jsonb not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  unique(policy_key,version)
);

create table if not exists ai_business_os_prod.portfolio_initiatives (
  id uuid primary key default gen_random_uuid(),
  initiative_key text not null unique,
  business_id uuid references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  name text not null,
  owner_agent_id text not null references ai_business_os_prod.agents(agent_id),
  status text not null default 'ACTIVE'
    check (status in ('ACTIVE','PAUSED','ARCHIVED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.portfolio_snapshots (
  id uuid primary key default gen_random_uuid(),
  snapshot_key text not null unique,
  initiative_id uuid not null references ai_business_os_prod.portfolio_initiatives(id),
  as_of timestamptz not null,
  metrics jsonb not null default '{}'::jsonb,
  evidence jsonb not null default '{}'::jsonb,
  snapshot_hash text not null unique check (snapshot_hash ~ '^[0-9a-f]{64}$'),
  created_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.portfolio_rankings (
  id uuid primary key default gen_random_uuid(),
  ranking_key text not null unique,
  policy_id uuid not null references ai_business_os_prod.portfolio_allocator_policies(id),
  as_of timestamptz not null,
  snapshot_set_hash text not null check (snapshot_set_hash ~ '^[0-9a-f]{64}$'),
  rows jsonb not null,
  ranking_hash text not null unique check (ranking_hash ~ '^[0-9a-f]{64}$'),
  created_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.portfolio_allocation_plans (
  id uuid primary key default gen_random_uuid(),
  plan_key text not null unique,
  ranking_id uuid not null references ai_business_os_prod.portfolio_rankings(id),
  resource_type text not null check (
    resource_type in ('AI_COST_UNITS','ENGINEERING_HOURS','HUMAN_HOURS','CASH_CENTS')
  ),
  total_units numeric,
  allocations jsonb not null default '[]'::jsonb,
  status text not null check (
    status in ('DRAFT','BLOCKED_INSUFFICIENT_EVIDENCE','PENDING_APPROVAL','AUTHORIZED','EXECUTED','CANCELLED')
  ),
  block_reason text,
  plan_hash text not null unique check (plan_hash ~ '^[0-9a-f]{64}$'),
  approval_request_key text references ai_business_os_prod.approval_inbox(request_key),
  execution_receipt_id uuid references ai_business_os_prod.autonomy_action_receipts(id),
  created_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.portfolio_data_gaps (
  id uuid primary key default gen_random_uuid(),
  initiative_id uuid not null references ai_business_os_prod.portfolio_initiatives(id),
  metric_key text not null,
  gap_type text not null check (
    gap_type in ('MISSING','PARTIAL_SCOPE','STALE','INADMISSIBLE','UNVERIFIED')
  ),
  priority integer not null default 0,
  recommended_source_type text,
  rationale text not null,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  unique(initiative_id,metric_key,gap_type)
);

alter table ai_business_os_prod.portfolio_allocator_policies enable row level security;
alter table ai_business_os_prod.portfolio_initiatives enable row level security;
alter table ai_business_os_prod.portfolio_snapshots enable row level security;
alter table ai_business_os_prod.portfolio_rankings enable row level security;
alter table ai_business_os_prod.portfolio_allocation_plans enable row level security;
alter table ai_business_os_prod.portfolio_data_gaps enable row level security;

revoke all on ai_business_os_prod.portfolio_allocator_policies,
  ai_business_os_prod.portfolio_initiatives,
  ai_business_os_prod.portfolio_snapshots,
  ai_business_os_prod.portfolio_rankings,
  ai_business_os_prod.portfolio_allocation_plans,
  ai_business_os_prod.portfolio_data_gaps
from public, anon, authenticated;

create index if not exists idx_portfolio_snapshots_initiative_asof
  on ai_business_os_prod.portfolio_snapshots(initiative_id,as_of desc);
create index if not exists idx_portfolio_rankings_created
  on ai_business_os_prod.portfolio_rankings(created_at desc);
create index if not exists idx_portfolio_plans_status
  on ai_business_os_prod.portfolio_allocation_plans(status,created_at desc);
create index if not exists idx_portfolio_gaps_initiative_priority
  on ai_business_os_prod.portfolio_data_gaps(initiative_id,priority desc);

create or replace function ai_business_os_prod.portfolio_source_quality(p_source_type text)
returns numeric
language sql
immutable
set search_path = pg_temp
as $$
select case upper(p_source_type)
  when 'BANK' then 1.00
  when 'PAYMENT_PROCESSOR' then 0.95
  when 'GENERAL_LEDGER' then 0.95
  when 'SIGNED_CONTRACT' then 0.90
  when 'INVOICE' then 0.85
  when 'CRM' then 0.60
  when 'ANALYTICS' then 0.70
  when 'MANUAL_RECORD' then 0.50
  when 'MODEL_ESTIMATE' then 0.20
  else 0.00
end::numeric;
$$;

create or replace function ai_business_os_prod.portfolio_metric_allowed_source(
  p_metric text,
  p_source_type text
) returns boolean
language sql
immutable
set search_path = pg_temp
as $$
select case p_metric
  when 'cash_collected_30d' then upper(p_source_type) in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER')
  when 'revenue_recognized_30d' then upper(p_source_type) in ('GENERAL_LEDGER','INVOICE')
  when 'cash_costs_30d' then upper(p_source_type) in ('BANK','GENERAL_LEDGER','INVOICE')
  when 'ai_cost_30d' then upper(p_source_type) in ('INVOICE','GENERAL_LEDGER','PAYMENT_PROCESSOR')
  when 'contracted_pipeline_value_90d' then upper(p_source_type) in ('SIGNED_CONTRACT','CRM')
  when 'qualified_pipeline_value_90d' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD')
  when 'human_hours_30d' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'remaining_effort_hours' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'time_to_cash_days' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'retention_signal' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'market_evidence_signal' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'strategic_reuse_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  else false
end;
$$;

create or replace function ai_business_os_prod.portfolio_metric_max_age_days(p_metric text)
returns integer
language sql
immutable
set search_path = pg_temp
as $$
select case p_metric
  when 'cash_collected_30d' then 45
  when 'revenue_recognized_30d' then 45
  when 'cash_costs_30d' then 45
  when 'ai_cost_30d' then 45
  when 'contracted_pipeline_value_90d' then 100
  when 'qualified_pipeline_value_90d' then 100
  when 'human_hours_30d' then 45
  when 'remaining_effort_hours' then 120
  when 'time_to_cash_days' then 120
  when 'retention_signal' then 120
  when 'market_evidence_signal' then 120
  when 'strategic_reuse_signal' then 120
  else 0
end;
$$;

create or replace function ai_business_os_prod.validate_portfolio_snapshot()
returns trigger
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_metric text;
  v_value jsonb;
  v_num numeric;
  v_ev jsonb;
  v_source text;
  v_sha text;
  v_observed timestamptz;
  v_max_age integer;
begin
  if jsonb_typeof(new.metrics) <> 'object' or jsonb_typeof(new.evidence) <> 'object' then
    raise exception 'metrics and evidence must be JSON objects';
  end if;

  for v_metric,v_value in select * from jsonb_each(new.metrics)
  loop
    if v_metric not in (
      'cash_collected_30d','revenue_recognized_30d','cash_costs_30d','ai_cost_30d',
      'contracted_pipeline_value_90d','qualified_pipeline_value_90d',
      'human_hours_30d','remaining_effort_hours','time_to_cash_days',
      'retention_signal','market_evidence_signal','strategic_reuse_signal'
    ) then
      raise exception 'unknown portfolio metric: %',v_metric;
    end if;
    if jsonb_typeof(v_value) <> 'number' then
      raise exception 'portfolio metric % must be numeric',v_metric;
    end if;
    v_num := (v_value#>>'{}')::numeric;
    if v_num < 0 then
      raise exception 'portfolio metric % cannot be negative',v_metric;
    end if;
    if v_metric in ('retention_signal','market_evidence_signal','strategic_reuse_signal')
       and (v_num < 0 or v_num > 1) then
      raise exception 'signal metric % must be in [0,1]',v_metric;
    end if;

    v_ev := new.evidence -> v_metric;
    if v_ev is null then
      continue;
    end if;
    if jsonb_typeof(v_ev) <> 'object' then
      raise exception 'evidence for % must be an object',v_metric;
    end if;
    v_source := upper(coalesce(v_ev->>'source_type',''));
    if not ai_business_os_prod.portfolio_metric_allowed_source(v_metric,v_source) then
      raise exception 'source type % is inadmissible for %',v_source,v_metric;
    end if;
    v_sha := lower(coalesce(v_ev->>'source_sha256',''));
    if v_sha !~ '^[0-9a-f]{64}$' then
      raise exception 'source SHA-256 required for %',v_metric;
    end if;
    v_observed := (v_ev->>'observed_at')::timestamptz;
    if v_observed is null or v_observed > new.as_of then
      raise exception 'evidence observed_at invalid for %',v_metric;
    end if;
    v_max_age := ai_business_os_prod.portfolio_metric_max_age_days(v_metric);
    if new.as_of - v_observed > make_interval(days=>v_max_age) then
      raise exception 'evidence is stale for %',v_metric;
    end if;
    if v_ev ? 'allocation_grade'
       and jsonb_typeof(v_ev->'allocation_grade') <> 'boolean' then
      raise exception 'allocation_grade must be boolean for %',v_metric;
    end if;
  end loop;

  for v_metric,v_ev in select * from jsonb_each(new.evidence)
  loop
    if not (new.metrics ? v_metric) then
      raise exception 'evidence supplied for absent metric: %',v_metric;
    end if;
  end loop;

  return new;
end;
$$;

drop trigger if exists trg_validate_portfolio_snapshot
on ai_business_os_prod.portfolio_snapshots;

create trigger trg_validate_portfolio_snapshot
before insert or update on ai_business_os_prod.portfolio_snapshots
for each row execute function ai_business_os_prod.validate_portfolio_snapshot();

insert into ai_business_os_prod.tool_actions(
  action_key,provider_key,connector_tool_name,action_class,
  approval_required,read_only,enabled,requires_resource_selection,
  cost_units,reliability_tier,risk_notes,metadata,updated_at
) values
('portfolio.allocate.ai_cost_units','supabase','internal:portfolio_allocator','INTERNAL_WRITE',true,false,true,false,1,'A','Decision-support allocation only; downstream spend still governed.','{}',now()),
('portfolio.allocate.engineering_hours','supabase','internal:portfolio_allocator','INTERNAL_WRITE',true,false,true,false,0,'A','Changes internal prioritization; human approval required.','{}',now()),
('portfolio.allocate.human_hours','supabase','internal:portfolio_allocator','INTERNAL_WRITE',true,false,true,false,0,'A','Changes internal prioritization; human approval required.','{}',now()),
('portfolio.allocate.cash','supabase','internal:portfolio_allocator','MONEY_MOVEMENT',true,false,true,false,3,'A','Cash allocation requires human approval and does not itself transfer funds.','{}',now())
on conflict (action_key) do update set
  action_class=excluded.action_class,
  approval_required=true,
  enabled=true,
  risk_notes=excluded.risk_notes,
  updated_at=now();


-- MIGRATION 20260924222945 add_ai_business_os_portfolio_scoring_v1

create or replace function ai_business_os_prod.portfolio_metric_quality(
  p_evidence jsonb,
  p_metric text
) returns numeric
language sql
immutable
set search_path = ai_business_os_prod, pg_temp
as $$
select case
  when p_evidence is null then 0::numeric
  when coalesce((p_evidence->p_metric->>'allocation_grade')::boolean,false) is not true then 0::numeric
  else ai_business_os_prod.portfolio_source_quality(p_evidence->p_metric->>'source_type')
end;
$$;

create or replace function ai_business_os_prod.portfolio_score_snapshot(
  p_snapshot_id uuid,
  p_policy_id uuid
) returns jsonb
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  s ai_business_os_prod.portfolio_snapshots%rowtype;
  p ai_business_os_prod.portfolio_allocator_policies%rowtype;
  m jsonb;
  e jsonb;
  q_cash numeric; q_rev numeric; q_cost numeric; q_ai numeric;
  q_contract numeric; q_qualified numeric; q_human numeric; q_effort numeric;
  q_time numeric; q_retention numeric; q_market numeric; q_reuse numeric;
  cash numeric; rev numeric; costs numeric; ai_cost numeric;
  contracted numeric; qualified numeric; human_hours numeric;
  effort numeric; time_days numeric; retention numeric; market numeric; reuse numeric;
  realized_net numeric; economic_value numeric; economic_index numeric;
  signal_bonus numeric; effort_penalty numeric; raw_score numeric;
  coverage_denominator integer; coverage_numerator integer;
  coverage numeric; evidence_factor numeric; score numeric;
  min_coverage numeric; state text;
begin
  select * into s from ai_business_os_prod.portfolio_snapshots where id=p_snapshot_id;
  if not found then raise exception 'unknown portfolio snapshot'; end if;
  select * into p from ai_business_os_prod.portfolio_allocator_policies where id=p_policy_id;
  if not found then raise exception 'unknown portfolio policy'; end if;

  m:=s.metrics; e:=s.evidence;

  q_cash:=ai_business_os_prod.portfolio_metric_quality(e,'cash_collected_30d');
  q_rev:=ai_business_os_prod.portfolio_metric_quality(e,'revenue_recognized_30d');
  q_cost:=ai_business_os_prod.portfolio_metric_quality(e,'cash_costs_30d');
  q_ai:=ai_business_os_prod.portfolio_metric_quality(e,'ai_cost_30d');
  q_contract:=ai_business_os_prod.portfolio_metric_quality(e,'contracted_pipeline_value_90d');
  q_qualified:=ai_business_os_prod.portfolio_metric_quality(e,'qualified_pipeline_value_90d');
  q_human:=ai_business_os_prod.portfolio_metric_quality(e,'human_hours_30d');
  q_effort:=ai_business_os_prod.portfolio_metric_quality(e,'remaining_effort_hours');
  q_time:=ai_business_os_prod.portfolio_metric_quality(e,'time_to_cash_days');
  q_retention:=ai_business_os_prod.portfolio_metric_quality(e,'retention_signal');
  q_market:=ai_business_os_prod.portfolio_metric_quality(e,'market_evidence_signal');
  q_reuse:=ai_business_os_prod.portfolio_metric_quality(e,'strategic_reuse_signal');

  cash:=case when q_cash>0 then coalesce((m->>'cash_collected_30d')::numeric,0) else 0 end;
  rev:=case when q_rev>0 then coalesce((m->>'revenue_recognized_30d')::numeric,0) else 0 end;
  costs:=case when q_cost>0 then coalesce((m->>'cash_costs_30d')::numeric,0) else 0 end;
  ai_cost:=case when q_ai>0 then coalesce((m->>'ai_cost_30d')::numeric,0) else 0 end;
  contracted:=case when q_contract>0 then coalesce((m->>'contracted_pipeline_value_90d')::numeric,0) else 0 end;
  qualified:=case when q_qualified>0 then coalesce((m->>'qualified_pipeline_value_90d')::numeric,0) else 0 end;
  human_hours:=case when q_human>0 then coalesce((m->>'human_hours_30d')::numeric,0) else 0 end;
  effort:=case when q_effort>0 then coalesce((m->>'remaining_effort_hours')::numeric,0) else 0 end;
  time_days:=case when q_time>0 then coalesce((m->>'time_to_cash_days')::numeric,0) else 0 end;
  retention:=case when q_retention>0 then coalesce((m->>'retention_signal')::numeric,0) else 0 end;
  market:=case when q_market>0 then coalesce((m->>'market_evidence_signal')::numeric,0) else 0 end;
  reuse:=case when q_reuse>0 then coalesce((m->>'strategic_reuse_signal')::numeric,0) else 0 end;

  realized_net:=cash-costs-ai_cost;
  economic_value :=
    realized_net * (p.config->>'realized_net_cash_weight')::numeric +
    rev*q_rev*(p.config->>'recognized_revenue_weight')::numeric +
    contracted*q_contract*(p.config->>'contracted_pipeline_weight')::numeric +
    qualified*q_qualified*(p.config->>'qualified_pipeline_weight')::numeric;

  economic_index:=case
    when economic_value>0 then ln(1+economic_value)
    when economic_value<0 then -ln(1+abs(economic_value))
    else 0 end;

  signal_bonus :=
    retention*q_retention*(p.config->>'retention_signal_weight')::numeric +
    market*q_market*(p.config->>'market_evidence_weight')::numeric +
    reuse*q_reuse*(p.config->>'strategic_reuse_weight')::numeric;

  effort_penalty :=
    ln(1+human_hours)*(p.config->>'human_hours_penalty')::numeric +
    ln(1+effort)*(p.config->>'remaining_effort_penalty')::numeric +
    ln(1+time_days)*(p.config->>'time_to_cash_penalty')::numeric;

  raw_score:=economic_index+signal_bonus-effort_penalty;

  select count(*) into coverage_denominator
  from (
    select unnest(array[
      'cash_collected_30d','cash_costs_30d','ai_cost_30d',
      'contracted_pipeline_value_90d','remaining_effort_hours',
      'time_to_cash_days','market_evidence_signal'
    ]) as metric
    union
    select jsonb_object_keys(m)
  ) x;

  select count(*) into coverage_numerator
  from (
    select unnest(array[
      'cash_collected_30d','cash_costs_30d','ai_cost_30d',
      'contracted_pipeline_value_90d','remaining_effort_hours',
      'time_to_cash_days','market_evidence_signal'
    ]) as metric
    union
    select jsonb_object_keys(m)
  ) x
  where ai_business_os_prod.portfolio_metric_quality(e,x.metric)>0;

  coverage:=case when coverage_denominator=0 then 0
                 else coverage_numerator::numeric/coverage_denominator::numeric end;
  evidence_factor:=coverage*coverage;
  score:=raw_score*evidence_factor;
  min_coverage:=(p.config->>'min_evidence_coverage')::numeric;

  state:=case
    when coverage<min_coverage then 'OBSERVE_ONLY'
    when realized_net<0 and economic_value<=0 then 'PAUSE_REVIEW'
    when score>0 then 'ALLOCATE_CANDIDATE'
    else 'MAINTAIN_REVIEW'
  end;

  return jsonb_build_object(
    'snapshot_id',s.id,
    'initiative_id',s.initiative_id,
    'as_of',s.as_of,
    'realized_net_cash',realized_net,
    'recognized_revenue',rev,
    'contracted_pipeline_value',contracted,
    'qualified_pipeline_value',qualified,
    'economic_value_component',economic_value,
    'economic_index_component',economic_index,
    'signal_bonus_component',signal_bonus,
    'effort_penalty_component',effort_penalty,
    'raw_score',raw_score,
    'evidence_coverage',coverage,
    'evidence_factor',evidence_factor,
    'decision_support_score',score,
    'eligible_for_allocation',coverage>=min_coverage,
    'decision_state',state
  );
end;
$$;

create or replace function ai_business_os_prod.refresh_portfolio_ranking(
  p_ranking_key text,
  p_policy_key text,
  p_created_by_agent_id text
) returns table(
  ranking_key text,
  ranking_hash text,
  eligible_count integer
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_policy ai_business_os_prod.portfolio_allocator_policies%rowtype;
  v_as_of timestamptz;
  v_oldest timestamptz;
  v_rows jsonb;
  v_snapshot_set_hash text;
  v_ranking_hash text;
  v_eligible integer;
begin
  select * into v_policy
  from ai_business_os_prod.portfolio_allocator_policies
  where policy_key=p_policy_key
  order by version desc
  limit 1;

  if not found then raise exception 'unknown allocator policy'; end if;
  if not exists(select 1 from ai_business_os_prod.agents where agent_id=p_created_by_agent_id and status='ACTIVE') then
    raise exception 'ranking creator must be an active agent';
  end if;

  with latest as (
    select distinct on (initiative_id) *
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  )
  select max(as_of),min(as_of)
  into v_as_of,v_oldest
  from latest;

  if v_as_of is null then raise exception 'no portfolio snapshots'; end if;
  if v_as_of-v_oldest > make_interval(days=>(v_policy.config->>'max_snapshot_skew_days')::integer) then
    raise exception 'snapshot dates are too far apart for fair comparison';
  end if;

  with latest as (
    select distinct on (initiative_id) *
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  ), scored as (
    select
      i.initiative_key,
      i.name,
      s.id as snapshot_id,
      s.snapshot_hash,
      ai_business_os_prod.portfolio_score_snapshot(s.id,v_policy.id) as score
    from latest s
    join ai_business_os_prod.portfolio_initiatives i on i.id=s.initiative_id
    where i.status='ACTIVE'
  ), ranked as (
    select *,
      row_number() over (
        order by
          (score->>'eligible_for_allocation')::boolean desc,
          (score->>'decision_support_score')::numeric desc,
          (score->>'evidence_coverage')::numeric desc,
          initiative_key
      ) as formula_rank
    from scored
  )
  select
    jsonb_agg(
      jsonb_build_object(
        'initiative_key',initiative_key,
        'name',name,
        'snapshot_id',snapshot_id,
        'snapshot_hash',snapshot_hash,
        'formula_rank',formula_rank
      ) || score
      order by formula_rank
    ),
    count(*) filter (where (score->>'eligible_for_allocation')::boolean)
  into v_rows,v_eligible
  from ranked;

  with latest as (
    select distinct on (initiative_id) id,snapshot_hash
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  )
  select encode(
    extensions.digest(
      coalesce(string_agg(id::text||':'||snapshot_hash,'|' order by id),''),
      'sha256'
    ),
    'hex'
  )
  into v_snapshot_set_hash
  from latest;

  v_ranking_hash:=encode(
    extensions.digest(
      v_policy.policy_hash||'|'||v_snapshot_set_hash||'|'||coalesce(v_rows::text,'[]'),
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.portfolio_rankings(
    ranking_key,policy_id,as_of,snapshot_set_hash,rows,ranking_hash,created_by_agent_id
  ) values (
    p_ranking_key,v_policy.id,v_as_of,v_snapshot_set_hash,coalesce(v_rows,'[]'::jsonb),
    v_ranking_hash,p_created_by_agent_id
  )
  on conflict (ranking_key) do update set
    policy_id=excluded.policy_id,
    as_of=excluded.as_of,
    snapshot_set_hash=excluded.snapshot_set_hash,
    rows=excluded.rows,
    ranking_hash=excluded.ranking_hash,
    created_by_agent_id=excluded.created_by_agent_id,
    created_at=now();

  return query select p_ranking_key,v_ranking_hash,v_eligible;
end;
$$;

revoke execute on function ai_business_os_prod.portfolio_score_snapshot(uuid,uuid)
from public, anon, authenticated;
revoke execute on function ai_business_os_prod.refresh_portfolio_ranking(text,text,text)
from public, anon, authenticated;


-- MIGRATION 20260924223042 fix_ai_business_os_portfolio_skew_numeric_v1

create or replace function ai_business_os_prod.refresh_portfolio_ranking(
  p_ranking_key text,
  p_policy_key text,
  p_created_by_agent_id text
) returns table(
  ranking_key text,
  ranking_hash text,
  eligible_count integer
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_policy ai_business_os_prod.portfolio_allocator_policies%rowtype;
  v_as_of timestamptz;
  v_oldest timestamptz;
  v_rows jsonb;
  v_snapshot_set_hash text;
  v_ranking_hash text;
  v_eligible integer;
begin
  select * into v_policy
  from ai_business_os_prod.portfolio_allocator_policies
  where policy_key=p_policy_key
  order by version desc
  limit 1;

  if not found then raise exception 'unknown allocator policy'; end if;
  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_created_by_agent_id and status='ACTIVE'
  ) then
    raise exception 'ranking creator must be an active agent';
  end if;

  with latest as (
    select distinct on (initiative_id) *
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  )
  select max(as_of),min(as_of)
  into v_as_of,v_oldest
  from latest;

  if v_as_of is null then raise exception 'no portfolio snapshots'; end if;
  if v_as_of-v_oldest >
     ((v_policy.config->>'max_snapshot_skew_days')::numeric * interval '1 day') then
    raise exception 'snapshot dates are too far apart for fair comparison';
  end if;

  with latest as (
    select distinct on (initiative_id) *
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  ), scored as (
    select
      i.initiative_key,
      i.name,
      s.id as snapshot_id,
      s.snapshot_hash,
      ai_business_os_prod.portfolio_score_snapshot(s.id,v_policy.id) as score
    from latest s
    join ai_business_os_prod.portfolio_initiatives i on i.id=s.initiative_id
    where i.status='ACTIVE'
  ), ranked as (
    select *,
      row_number() over (
        order by
          (score->>'eligible_for_allocation')::boolean desc,
          (score->>'decision_support_score')::numeric desc,
          (score->>'evidence_coverage')::numeric desc,
          initiative_key
      ) as formula_rank
    from scored
  )
  select
    jsonb_agg(
      jsonb_build_object(
        'initiative_key',initiative_key,
        'name',name,
        'snapshot_id',snapshot_id,
        'snapshot_hash',snapshot_hash,
        'formula_rank',formula_rank
      ) || score
      order by formula_rank
    ),
    count(*) filter (where (score->>'eligible_for_allocation')::boolean)
  into v_rows,v_eligible
  from ranked;

  with latest as (
    select distinct on (initiative_id) id,snapshot_hash
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  )
  select encode(
    extensions.digest(
      coalesce(string_agg(id::text||':'||snapshot_hash,'|' order by id),''),
      'sha256'
    ),
    'hex'
  )
  into v_snapshot_set_hash
  from latest;

  v_ranking_hash:=encode(
    extensions.digest(
      v_policy.policy_hash||'|'||v_snapshot_set_hash||'|'||coalesce(v_rows::text,'[]'),
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.portfolio_rankings(
    ranking_key,policy_id,as_of,snapshot_set_hash,rows,ranking_hash,created_by_agent_id
  ) values (
    p_ranking_key,v_policy.id,v_as_of,v_snapshot_set_hash,coalesce(v_rows,'[]'::jsonb),
    v_ranking_hash,p_created_by_agent_id
  )
  on conflict (ranking_key) do update set
    policy_id=excluded.policy_id,
    as_of=excluded.as_of,
    snapshot_set_hash=excluded.snapshot_set_hash,
    rows=excluded.rows,
    ranking_hash=excluded.ranking_hash,
    created_by_agent_id=excluded.created_by_agent_id,
    created_at=now();

  return query select p_ranking_key,v_ranking_hash,v_eligible;
end;
$$;


-- MIGRATION 20260924223145 fix_ai_business_os_portfolio_ranking_upsert_v1

create or replace function ai_business_os_prod.refresh_portfolio_ranking(
  p_ranking_key text,
  p_policy_key text,
  p_created_by_agent_id text
) returns table(
  ranking_key text,
  ranking_hash text,
  eligible_count integer
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_policy ai_business_os_prod.portfolio_allocator_policies%rowtype;
  v_as_of timestamptz;
  v_oldest timestamptz;
  v_rows jsonb;
  v_snapshot_set_hash text;
  v_ranking_hash text;
  v_eligible integer;
begin
  select * into v_policy
  from ai_business_os_prod.portfolio_allocator_policies
  where policy_key=p_policy_key
  order by version desc
  limit 1;

  if not found then raise exception 'unknown allocator policy'; end if;
  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_created_by_agent_id and status='ACTIVE'
  ) then
    raise exception 'ranking creator must be an active agent';
  end if;

  with latest as (
    select distinct on (initiative_id) *
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  )
  select max(as_of),min(as_of)
  into v_as_of,v_oldest
  from latest;

  if v_as_of is null then raise exception 'no portfolio snapshots'; end if;
  if v_as_of-v_oldest >
     ((v_policy.config->>'max_snapshot_skew_days')::numeric * interval '1 day') then
    raise exception 'snapshot dates are too far apart for fair comparison';
  end if;

  with latest as (
    select distinct on (initiative_id) *
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  ), scored as (
    select
      i.initiative_key,
      i.name,
      s.id as snapshot_id,
      s.snapshot_hash,
      ai_business_os_prod.portfolio_score_snapshot(s.id,v_policy.id) as score
    from latest s
    join ai_business_os_prod.portfolio_initiatives i on i.id=s.initiative_id
    where i.status='ACTIVE'
  ), ranked as (
    select *,
      row_number() over (
        order by
          (score->>'eligible_for_allocation')::boolean desc,
          (score->>'decision_support_score')::numeric desc,
          (score->>'evidence_coverage')::numeric desc,
          initiative_key
      ) as formula_rank
    from scored
  )
  select
    jsonb_agg(
      jsonb_build_object(
        'initiative_key',initiative_key,
        'name',name,
        'snapshot_id',snapshot_id,
        'snapshot_hash',snapshot_hash,
        'formula_rank',formula_rank
      ) || score
      order by formula_rank
    ),
    count(*) filter (where (score->>'eligible_for_allocation')::boolean)
  into v_rows,v_eligible
  from ranked;

  with latest as (
    select distinct on (initiative_id) id,snapshot_hash
    from ai_business_os_prod.portfolio_snapshots
    order by initiative_id,as_of desc,created_at desc
  )
  select encode(
    extensions.digest(
      coalesce(string_agg(id::text||':'||snapshot_hash,'|' order by id),''),
      'sha256'
    ),
    'hex'
  )
  into v_snapshot_set_hash
  from latest;

  v_ranking_hash:=encode(
    extensions.digest(
      v_policy.policy_hash||'|'||v_snapshot_set_hash||'|'||coalesce(v_rows::text,'[]'),
      'sha256'
    ),
    'hex'
  );

  insert into ai_business_os_prod.portfolio_rankings(
    ranking_key,policy_id,as_of,snapshot_set_hash,rows,ranking_hash,created_by_agent_id
  ) values (
    p_ranking_key,v_policy.id,v_as_of,v_snapshot_set_hash,coalesce(v_rows,'[]'::jsonb),
    v_ranking_hash,p_created_by_agent_id
  )
  on conflict on constraint portfolio_rankings_ranking_key_key
  do update set
    policy_id=excluded.policy_id,
    as_of=excluded.as_of,
    snapshot_set_hash=excluded.snapshot_set_hash,
    rows=excluded.rows,
    ranking_hash=excluded.ranking_hash,
    created_by_agent_id=excluded.created_by_agent_id,
    created_at=now();

  return query select p_ranking_key,v_ranking_hash,v_eligible;
end;
$$;


-- MIGRATION 20260924223256 add_ai_business_os_portfolio_planning_governance_v1

create or replace function ai_business_os_prod.create_portfolio_allocation_plan(
  p_plan_key text,
  p_ranking_key text,
  p_resource_type text,
  p_total_units numeric,
  p_created_by_agent_id text
) returns table(
  plan_key text,
  status text,
  plan_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_ranking ai_business_os_prod.portfolio_rankings%rowtype;
  v_policy ai_business_os_prod.portfolio_allocator_policies%rowtype;
  v_eligible jsonb;
  v_count integer;
  v_score_sum numeric;
  v_max_share numeric;
  v_allocations jsonb := '[]'::jsonb;
  v_allocated numeric := 0;
  v_row jsonb;
  v_units numeric;
  v_share numeric;
  v_plan_hash text;
  v_status text;
  v_block text;
begin
  if p_resource_type not in ('AI_COST_UNITS','ENGINEERING_HOURS','HUMAN_HOURS','CASH_CENTS') then
    raise exception 'unsupported resource type';
  end if;
  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_created_by_agent_id and status='ACTIVE'
  ) then
    raise exception 'plan creator must be active';
  end if;

  select * into v_ranking
  from ai_business_os_prod.portfolio_rankings
  where ranking_key=p_ranking_key;
  if not found then raise exception 'unknown ranking'; end if;

  select * into v_policy
  from ai_business_os_prod.portfolio_allocator_policies
  where id=v_ranking.policy_id;
  if not found then raise exception 'ranking policy missing'; end if;

  select coalesce(jsonb_agg(x),'[]'::jsonb),count(*),
         coalesce(sum((x->>'decision_support_score')::numeric),0)
  into v_eligible,v_count,v_score_sum
  from jsonb_array_elements(v_ranking.rows) x
  where coalesce((x->>'eligible_for_allocation')::boolean,false)
    and (x->>'decision_support_score')::numeric > 0;

  if v_count=0 then
    v_status:='BLOCKED_INSUFFICIENT_EVIDENCE';
    v_block:='No initiative meets the minimum evidence threshold with a positive decision-support score.';
    v_plan_hash:=encode(
      extensions.digest(
        p_plan_key||'|'||v_ranking.ranking_hash||'|'||p_resource_type||'|BLOCKED',
        'sha256'
      ),'hex'
    );
    insert into ai_business_os_prod.portfolio_allocation_plans(
      plan_key,ranking_id,resource_type,total_units,allocations,status,
      block_reason,plan_hash,created_by_agent_id
    ) values (
      p_plan_key,v_ranking.id,p_resource_type,p_total_units,'[]'::jsonb,v_status,
      v_block,v_plan_hash,p_created_by_agent_id
    )
    on conflict(plan_key) do update set
      ranking_id=excluded.ranking_id,
      resource_type=excluded.resource_type,
      total_units=excluded.total_units,
      allocations=excluded.allocations,
      status=excluded.status,
      block_reason=excluded.block_reason,
      plan_hash=excluded.plan_hash,
      approval_request_key=null,
      execution_receipt_id=null,
      created_by_agent_id=excluded.created_by_agent_id,
      updated_at=now();
    return query select p_plan_key,v_status,v_plan_hash;
    return;
  end if;

  if p_total_units is null or p_total_units<=0 then
    raise exception 'positive total_units required when allocation candidates exist';
  end if;
  if p_resource_type='CASH_CENTS' and trunc(p_total_units)<>p_total_units then
    raise exception 'CASH_CENTS must be an integer number of cents';
  end if;

  v_max_share:=(v_policy.config->>'max_allocation_share')::numeric;

  for v_row in select * from jsonb_array_elements(v_eligible)
  loop
    v_share:=least(
      v_max_share,
      (v_row->>'decision_support_score')::numeric / nullif(v_score_sum,0)
    );
    v_units:=p_total_units*v_share;
    if p_resource_type='CASH_CENTS' then v_units:=floor(v_units); end if;
    v_allocated:=v_allocated+v_units;
    v_allocations:=v_allocations || jsonb_build_array(
      jsonb_build_object(
        'initiative_key',v_row->>'initiative_key',
        'formula_rank',(v_row->>'formula_rank')::integer,
        'decision_support_score',(v_row->>'decision_support_score')::numeric,
        'units',v_units,
        'share',case when p_total_units=0 then 0 else v_units/p_total_units end
      )
    );
  end loop;

  if v_allocated < p_total_units then
    v_allocations:=v_allocations || jsonb_build_array(
      jsonb_build_object(
        'initiative_key','__RESERVE__',
        'formula_rank',null,
        'decision_support_score',null,
        'units',p_total_units-v_allocated,
        'share',(p_total_units-v_allocated)/p_total_units,
        'reason','Concentration cap / insufficient diversified evidence leaves resources unallocated.'
      )
    );
  end if;

  v_status:='DRAFT';
  v_plan_hash:=encode(
    extensions.digest(
      p_plan_key||'|'||v_ranking.ranking_hash||'|'||p_resource_type||'|'||
      p_total_units::text||'|'||v_allocations::text,
      'sha256'
    ),'hex'
  );

  insert into ai_business_os_prod.portfolio_allocation_plans(
    plan_key,ranking_id,resource_type,total_units,allocations,status,
    block_reason,plan_hash,created_by_agent_id
  ) values (
    p_plan_key,v_ranking.id,p_resource_type,p_total_units,v_allocations,v_status,
    null,v_plan_hash,p_created_by_agent_id
  )
  on conflict(plan_key) do update set
    ranking_id=excluded.ranking_id,
    resource_type=excluded.resource_type,
    total_units=excluded.total_units,
    allocations=excluded.allocations,
    status=excluded.status,
    block_reason=null,
    plan_hash=excluded.plan_hash,
    approval_request_key=null,
    execution_receipt_id=null,
    created_by_agent_id=excluded.created_by_agent_id,
    updated_at=now();

  return query select p_plan_key,v_status,v_plan_hash;
end;
$$;

create or replace function ai_business_os_prod.request_portfolio_plan_approval(
  p_plan_key text,
  p_actor_agent_id text
) returns table(
  request_key text,
  intent_hash text,
  status text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_plan ai_business_os_prod.portfolio_allocation_plans%rowtype;
  v_ranking ai_business_os_prod.portfolio_rankings%rowtype;
  v_action_key text;
  v_action_class text;
  v_request_key text;
  v_intent text;
  v_evidence text;
  v_expected_money bigint:=0;
begin
  select * into v_plan
  from ai_business_os_prod.portfolio_allocation_plans
  where plan_key=p_plan_key
  for update;
  if not found then raise exception 'unknown allocation plan'; end if;
  if v_plan.status<>'DRAFT' then
    raise exception 'only DRAFT plans may request approval';
  end if;

  select * into v_ranking from ai_business_os_prod.portfolio_rankings where id=v_plan.ranking_id;

  v_action_key:=case v_plan.resource_type
    when 'AI_COST_UNITS' then 'portfolio.allocate.ai_cost_units'
    when 'ENGINEERING_HOURS' then 'portfolio.allocate.engineering_hours'
    when 'HUMAN_HOURS' then 'portfolio.allocate.human_hours'
    when 'CASH_CENTS' then 'portfolio.allocate.cash'
  end;
  select action_class into v_action_class
  from ai_business_os_prod.tool_actions
  where action_key=v_action_key and enabled=true;
  if v_action_class is null then raise exception 'allocation action is not enabled'; end if;

  if v_plan.resource_type='CASH_CENTS' then
    v_expected_money:=v_plan.total_units::bigint;
  end if;

  v_request_key:='portfolio-approval-'||v_plan.plan_key;
  v_intent:=encode(
    extensions.digest(
      v_plan.plan_hash||'|'||v_ranking.ranking_hash||'|'||
      v_plan.resource_type||'|'||coalesce(v_plan.total_units::text,'')||'|'||
      v_plan.allocations::text,
      'sha256'
    ),'hex'
  );
  v_evidence:=encode(
    extensions.digest(
      v_ranking.snapshot_set_hash||'|'||v_ranking.ranking_hash,
      'sha256'
    ),'hex'
  );

  insert into ai_business_os_prod.approval_inbox(
    request_key,agent_id,action_key,action_class,title,summary,
    exact_parameters,intent_hash,evidence_refs,evidence_hash,
    predicted_risk,expected_cost_units,expected_money_cents,
    rollback_plan,status,expires_at
  ) values (
    v_request_key,
    p_actor_agent_id,
    v_action_key,
    v_action_class,
    'Approve portfolio allocation plan '||v_plan.plan_key,
    'Approve the exact evidence-bound resource allocation proposal. Approval does not itself transfer cash or assign workers.',
    jsonb_build_object(
      'plan_key',v_plan.plan_key,
      'plan_hash',v_plan.plan_hash,
      'ranking_key',v_ranking.ranking_key,
      'ranking_hash',v_ranking.ranking_hash,
      'resource_type',v_plan.resource_type,
      'total_units',v_plan.total_units,
      'allocations',v_plan.allocations
    ),
    v_intent,
    jsonb_build_array(
      'portfolio-ranking:'||v_ranking.ranking_key,
      'snapshot-set:'||v_ranking.snapshot_set_hash
    ),
    v_evidence,
    case when v_plan.resource_type='CASH_CENTS'
      then 'MONEY_MOVEMENT'
      else 'PORTFOLIO_RESOURCE_REALLOCATION'
    end,
    case when v_plan.resource_type='AI_COST_UNITS' then v_plan.total_units else 0 end,
    v_expected_money,
    jsonb_build_object(
      'execution','No resource change occurs until a separate executor acts after approval.',
      'reversal','Cancel the plan before execution or issue a superseding allocation after execution.'
    ),
    'PENDING',
    now()+interval '7 days'
  )
  on conflict(request_key) do update set
    exact_parameters=excluded.exact_parameters,
    intent_hash=excluded.intent_hash,
    evidence_refs=excluded.evidence_refs,
    evidence_hash=excluded.evidence_hash,
    predicted_risk=excluded.predicted_risk,
    expected_cost_units=excluded.expected_cost_units,
    expected_money_cents=excluded.expected_money_cents,
    rollback_plan=excluded.rollback_plan,
    status='PENDING',
    expires_at=excluded.expires_at,
    decided_at=null,decided_by=null,decision_reason=null,
    decision_receipt_hash=null,consumed_at=null,execution_receipt_id=null;

  update ai_business_os_prod.portfolio_allocation_plans
  set status='PENDING_APPROVAL',
      approval_request_key=v_request_key,
      updated_at=now()
  where id=v_plan.id;

  return query select v_request_key,v_intent,'PENDING'::text;
end;
$$;

revoke execute on function ai_business_os_prod.create_portfolio_allocation_plan(text,text,text,numeric,text)
from public, anon, authenticated;
revoke execute on function ai_business_os_prod.request_portfolio_plan_approval(text,text)
from public, anon, authenticated;


-- MIGRATION 20260924223355 fix_ai_business_os_portfolio_plan_status_ambiguity_v1

create or replace function ai_business_os_prod.create_portfolio_allocation_plan(
  p_plan_key text,
  p_ranking_key text,
  p_resource_type text,
  p_total_units numeric,
  p_created_by_agent_id text
) returns table(
  plan_key text,
  status text,
  plan_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_ranking ai_business_os_prod.portfolio_rankings%rowtype;
  v_policy ai_business_os_prod.portfolio_allocator_policies%rowtype;
  v_eligible jsonb;
  v_count integer;
  v_score_sum numeric;
  v_max_share numeric;
  v_allocations jsonb := '[]'::jsonb;
  v_allocated numeric := 0;
  v_row jsonb;
  v_units numeric;
  v_share numeric;
  v_plan_hash text;
  v_status text;
  v_block text;
begin
  if p_resource_type not in ('AI_COST_UNITS','ENGINEERING_HOURS','HUMAN_HOURS','CASH_CENTS') then
    raise exception 'unsupported resource type';
  end if;
  if not exists(
    select 1 from ai_business_os_prod.agents a
    where a.agent_id=p_created_by_agent_id and a.status='ACTIVE'
  ) then
    raise exception 'plan creator must be active';
  end if;

  select * into v_ranking
  from ai_business_os_prod.portfolio_rankings r
  where r.ranking_key=p_ranking_key;
  if not found then raise exception 'unknown ranking'; end if;

  select * into v_policy
  from ai_business_os_prod.portfolio_allocator_policies p
  where p.id=v_ranking.policy_id;
  if not found then raise exception 'ranking policy missing'; end if;

  select coalesce(jsonb_agg(x),'[]'::jsonb),count(*),
         coalesce(sum((x->>'decision_support_score')::numeric),0)
  into v_eligible,v_count,v_score_sum
  from jsonb_array_elements(v_ranking.rows) x
  where coalesce((x->>'eligible_for_allocation')::boolean,false)
    and (x->>'decision_support_score')::numeric > 0;

  if v_count=0 then
    v_status:='BLOCKED_INSUFFICIENT_EVIDENCE';
    v_block:='No initiative meets the minimum evidence threshold with a positive decision-support score.';
    v_plan_hash:=encode(
      extensions.digest(
        p_plan_key||'|'||v_ranking.ranking_hash||'|'||p_resource_type||'|BLOCKED',
        'sha256'
      ),'hex'
    );
    insert into ai_business_os_prod.portfolio_allocation_plans(
      plan_key,ranking_id,resource_type,total_units,allocations,status,
      block_reason,plan_hash,created_by_agent_id
    ) values (
      p_plan_key,v_ranking.id,p_resource_type,p_total_units,'[]'::jsonb,v_status,
      v_block,v_plan_hash,p_created_by_agent_id
    )
    on conflict on constraint portfolio_allocation_plans_plan_key_key
    do update set
      ranking_id=excluded.ranking_id,
      resource_type=excluded.resource_type,
      total_units=excluded.total_units,
      allocations=excluded.allocations,
      status=excluded.status,
      block_reason=excluded.block_reason,
      plan_hash=excluded.plan_hash,
      approval_request_key=null,
      execution_receipt_id=null,
      created_by_agent_id=excluded.created_by_agent_id,
      updated_at=now();
    return query select p_plan_key,v_status,v_plan_hash;
    return;
  end if;

  if p_total_units is null or p_total_units<=0 then
    raise exception 'positive total_units required when allocation candidates exist';
  end if;
  if p_resource_type='CASH_CENTS' and trunc(p_total_units)<>p_total_units then
    raise exception 'CASH_CENTS must be an integer number of cents';
  end if;

  v_max_share:=(v_policy.config->>'max_allocation_share')::numeric;

  for v_row in select * from jsonb_array_elements(v_eligible)
  loop
    v_share:=least(
      v_max_share,
      (v_row->>'decision_support_score')::numeric / nullif(v_score_sum,0)
    );
    v_units:=p_total_units*v_share;
    if p_resource_type='CASH_CENTS' then v_units:=floor(v_units); end if;
    v_allocated:=v_allocated+v_units;
    v_allocations:=v_allocations || jsonb_build_array(
      jsonb_build_object(
        'initiative_key',v_row->>'initiative_key',
        'formula_rank',(v_row->>'formula_rank')::integer,
        'decision_support_score',(v_row->>'decision_support_score')::numeric,
        'units',v_units,
        'share',case when p_total_units=0 then 0 else v_units/p_total_units end
      )
    );
  end loop;

  if v_allocated < p_total_units then
    v_allocations:=v_allocations || jsonb_build_array(
      jsonb_build_object(
        'initiative_key','__RESERVE__',
        'formula_rank',null,
        'decision_support_score',null,
        'units',p_total_units-v_allocated,
        'share',(p_total_units-v_allocated)/p_total_units,
        'reason','Concentration cap / insufficient diversified evidence leaves resources unallocated.'
      )
    );
  end if;

  v_status:='DRAFT';
  v_plan_hash:=encode(
    extensions.digest(
      p_plan_key||'|'||v_ranking.ranking_hash||'|'||p_resource_type||'|'||
      p_total_units::text||'|'||v_allocations::text,
      'sha256'
    ),'hex'
  );

  insert into ai_business_os_prod.portfolio_allocation_plans(
    plan_key,ranking_id,resource_type,total_units,allocations,status,
    block_reason,plan_hash,created_by_agent_id
  ) values (
    p_plan_key,v_ranking.id,p_resource_type,p_total_units,v_allocations,v_status,
    null,v_plan_hash,p_created_by_agent_id
  )
  on conflict on constraint portfolio_allocation_plans_plan_key_key
  do update set
    ranking_id=excluded.ranking_id,
    resource_type=excluded.resource_type,
    total_units=excluded.total_units,
    allocations=excluded.allocations,
    status=excluded.status,
    block_reason=null,
    plan_hash=excluded.plan_hash,
    approval_request_key=null,
    execution_receipt_id=null,
    created_by_agent_id=excluded.created_by_agent_id,
    updated_at=now();

  return query select p_plan_key,v_status,v_plan_hash;
end;
$$;


-- MIGRATION 20260924223435 add_ai_business_os_portfolio_allocator_views_v1

create or replace view ai_business_os_prod.portfolio_allocator_status_v1
with (security_invoker = true)
as
with latest_ranking as (
  select *
  from ai_business_os_prod.portfolio_rankings
  order by created_at desc
  limit 1
),
rank_rows as (
  select
    r.ranking_key,
    r.ranking_hash,
    r.as_of,
    x
  from latest_ranking r
  cross join lateral jsonb_array_elements(r.rows) x
),
gap_counts as (
  select initiative_id,
         count(*) filter (where resolved_at is null) as open_gap_count,
         jsonb_agg(
           jsonb_build_object(
             'metric_key',metric_key,
             'gap_type',gap_type,
             'priority',priority,
             'recommended_source_type',recommended_source_type,
             'rationale',rationale
           )
           order by priority desc,metric_key
         ) filter (where resolved_at is null) as gaps
  from ai_business_os_prod.portfolio_data_gaps
  group by initiative_id
)
select
  i.initiative_key,
  i.name,
  rr.ranking_key,
  rr.ranking_hash,
  rr.as_of,
  (rr.x->>'formula_rank')::integer as formula_rank,
  (rr.x->>'decision_state')::text as decision_state,
  (rr.x->>'eligible_for_allocation')::boolean as eligible_for_allocation,
  (rr.x->>'evidence_coverage')::numeric as evidence_coverage,
  (rr.x->>'decision_support_score')::numeric as decision_support_score,
  coalesce(g.open_gap_count,0) as open_gap_count,
  coalesce(g.gaps,'[]'::jsonb) as data_gaps,
  case
    when (rr.x->>'eligible_for_allocation')::boolean then 'ALLOCATION_READY'
    else 'EVIDENCE_REQUIRED'
  end as allocator_status
from rank_rows rr
join ai_business_os_prod.portfolio_initiatives i
  on i.initiative_key=rr.x->>'initiative_key'
left join gap_counts g on g.initiative_id=i.id
order by (rr.x->>'formula_rank')::integer;

create or replace view ai_business_os_prod.portfolio_plan_status_v1
with (security_invoker = true)
as
select
  p.plan_key,
  r.ranking_key,
  p.resource_type,
  p.total_units,
  p.status,
  p.block_reason,
  p.plan_hash,
  p.allocations,
  p.approval_request_key,
  p.created_at,
  p.updated_at
from ai_business_os_prod.portfolio_allocation_plans p
join ai_business_os_prod.portfolio_rankings r on r.id=p.ranking_id
order by p.created_at desc;

create or replace view ai_business_os_prod.command_center_portfolio_allocator_v1
with (security_invoker = true)
as
select jsonb_build_object(
  'policy',(
    select jsonb_build_object(
      'policy_key',policy_key,
      'version',version,
      'policy_hash',policy_hash,
      'min_evidence_coverage',config->'min_evidence_coverage',
      'max_allocation_share',config->'max_allocation_share'
    )
    from ai_business_os_prod.portfolio_allocator_policies
    order by created_at desc limit 1
  ),
  'ranking',(
    select jsonb_build_object(
      'ranking_key',ranking_key,
      'ranking_hash',ranking_hash,
      'as_of',as_of,
      'allocation_ready_count',count(*) filter (where eligible_for_allocation),
      'observe_only_count',count(*) filter (where not eligible_for_allocation)
    )
    from ai_business_os_prod.portfolio_allocator_status_v1
    group by ranking_key,ranking_hash,as_of
  ),
  'initiatives',coalesce((
    select jsonb_agg(to_jsonb(s) order by formula_rank)
    from ai_business_os_prod.portfolio_allocator_status_v1 s
  ),'[]'::jsonb),
  'plans',coalesce((
    select jsonb_agg(to_jsonb(p) order by resource_type)
    from ai_business_os_prod.portfolio_plan_status_v1 p
    where p.ranking_key='portfolio-ranking-2026-09-24'
  ),'[]'::jsonb)
) as allocator;


-- MIGRATION 20260924223523 fix_ai_business_os_portfolio_approval_upsert_v1

create or replace function ai_business_os_prod.request_portfolio_plan_approval(
  p_plan_key text,
  p_actor_agent_id text
) returns table(
  request_key text,
  intent_hash text,
  status text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_plan ai_business_os_prod.portfolio_allocation_plans%rowtype;
  v_ranking ai_business_os_prod.portfolio_rankings%rowtype;
  v_action_key text;
  v_action_class text;
  v_request_key text;
  v_intent text;
  v_evidence text;
  v_expected_money bigint:=0;
begin
  select * into v_plan
  from ai_business_os_prod.portfolio_allocation_plans p
  where p.plan_key=p_plan_key
  for update;
  if not found then raise exception 'unknown allocation plan'; end if;
  if v_plan.status<>'DRAFT' then
    raise exception 'only DRAFT plans may request approval';
  end if;

  select * into v_ranking
  from ai_business_os_prod.portfolio_rankings r
  where r.id=v_plan.ranking_id;

  v_action_key:=case v_plan.resource_type
    when 'AI_COST_UNITS' then 'portfolio.allocate.ai_cost_units'
    when 'ENGINEERING_HOURS' then 'portfolio.allocate.engineering_hours'
    when 'HUMAN_HOURS' then 'portfolio.allocate.human_hours'
    when 'CASH_CENTS' then 'portfolio.allocate.cash'
  end;

  select t.action_class into v_action_class
  from ai_business_os_prod.tool_actions t
  where t.action_key=v_action_key and t.enabled=true;
  if v_action_class is null then raise exception 'allocation action is not enabled'; end if;

  if v_plan.resource_type='CASH_CENTS' then
    v_expected_money:=v_plan.total_units::bigint;
  end if;

  v_request_key:='portfolio-approval-'||v_plan.plan_key;
  v_intent:=encode(
    extensions.digest(
      v_plan.plan_hash||'|'||v_ranking.ranking_hash||'|'||
      v_plan.resource_type||'|'||coalesce(v_plan.total_units::text,'')||'|'||
      v_plan.allocations::text,
      'sha256'
    ),'hex'
  );
  v_evidence:=encode(
    extensions.digest(
      v_ranking.snapshot_set_hash||'|'||v_ranking.ranking_hash,
      'sha256'
    ),'hex'
  );

  insert into ai_business_os_prod.approval_inbox(
    request_key,agent_id,action_key,action_class,title,summary,
    exact_parameters,intent_hash,evidence_refs,evidence_hash,
    predicted_risk,expected_cost_units,expected_money_cents,
    rollback_plan,status,expires_at
  ) values (
    v_request_key,
    p_actor_agent_id,
    v_action_key,
    v_action_class,
    'Approve portfolio allocation plan '||v_plan.plan_key,
    'Approve the exact evidence-bound resource allocation proposal. Approval does not itself transfer cash or assign workers.',
    jsonb_build_object(
      'plan_key',v_plan.plan_key,
      'plan_hash',v_plan.plan_hash,
      'ranking_key',v_ranking.ranking_key,
      'ranking_hash',v_ranking.ranking_hash,
      'resource_type',v_plan.resource_type,
      'total_units',v_plan.total_units,
      'allocations',v_plan.allocations
    ),
    v_intent,
    jsonb_build_array(
      'portfolio-ranking:'||v_ranking.ranking_key,
      'snapshot-set:'||v_ranking.snapshot_set_hash
    ),
    v_evidence,
    case when v_plan.resource_type='CASH_CENTS'
      then 'MONEY_MOVEMENT'
      else 'PORTFOLIO_RESOURCE_REALLOCATION'
    end,
    case when v_plan.resource_type='AI_COST_UNITS' then v_plan.total_units else 0 end,
    v_expected_money,
    jsonb_build_object(
      'execution','No resource change occurs until a separate executor acts after approval.',
      'reversal','Cancel the plan before execution or issue a superseding allocation after execution.'
    ),
    'PENDING',
    now()+interval '7 days'
  )
  on conflict on constraint approval_inbox_request_key_key
  do update set
    exact_parameters=excluded.exact_parameters,
    intent_hash=excluded.intent_hash,
    evidence_refs=excluded.evidence_refs,
    evidence_hash=excluded.evidence_hash,
    predicted_risk=excluded.predicted_risk,
    expected_cost_units=excluded.expected_cost_units,
    expected_money_cents=excluded.expected_money_cents,
    rollback_plan=excluded.rollback_plan,
    status='PENDING',
    expires_at=excluded.expires_at,
    decided_at=null,decided_by=null,decision_reason=null,
    decision_receipt_hash=null,consumed_at=null,execution_receipt_id=null;

  update ai_business_os_prod.portfolio_allocation_plans p
  set status='PENDING_APPROVAL',
      approval_request_key=v_request_key,
      updated_at=now()
  where p.id=v_plan.id;

  return query select v_request_key,v_intent,'PENDING'::text;
end;
$$;


-- MIGRATION 20260924223706 integrate_ai_business_os_capital_allocator_command_center_v1

create index if not exists idx_portfolio_initiatives_business
  on ai_business_os_prod.portfolio_initiatives(business_id);
create index if not exists idx_portfolio_initiatives_product
  on ai_business_os_prod.portfolio_initiatives(product_id);
create index if not exists idx_portfolio_initiatives_owner
  on ai_business_os_prod.portfolio_initiatives(owner_agent_id);
create index if not exists idx_portfolio_snapshots_creator
  on ai_business_os_prod.portfolio_snapshots(created_by_agent_id);
create index if not exists idx_portfolio_rankings_policy
  on ai_business_os_prod.portfolio_rankings(policy_id);
create index if not exists idx_portfolio_rankings_creator
  on ai_business_os_prod.portfolio_rankings(created_by_agent_id);
create index if not exists idx_portfolio_plans_ranking
  on ai_business_os_prod.portfolio_allocation_plans(ranking_id);
create index if not exists idx_portfolio_plans_approval
  on ai_business_os_prod.portfolio_allocation_plans(approval_request_key);
create index if not exists idx_portfolio_plans_execution
  on ai_business_os_prod.portfolio_allocation_plans(execution_receipt_id);
create index if not exists idx_portfolio_gaps_initiative
  on ai_business_os_prod.portfolio_data_gaps(initiative_id);

drop function if exists ai_business_os_prod.refresh_command_center_snapshot(text);

create function ai_business_os_prod.refresh_command_center_snapshot(
  p_snapshot_key text
) returns table (
  out_snapshot_key text,
  out_snapshot_hash text,
  out_generated_at timestamptz
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_payload jsonb;
  v_hash text;
  v_generated timestamptz := now();
begin
  if coalesce(trim(p_snapshot_key),'')='' then
    raise exception 'snapshot key required';
  end if;

  select jsonb_build_object(
    'generated_at',v_generated,
    'system',(select to_jsonb(s) from ai_business_os_prod.command_center_system_v1 s),
    'portfolio',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from ai_business_os_prod.command_center_portfolio_v1 p),'[]'::jsonb),
    'agents',coalesce((select jsonb_agg(to_jsonb(a) order by a.display_name) from ai_business_os_prod.command_center_agents_v1 a),'[]'::jsonb),
    'revenue_loops',coalesce((select jsonb_agg(to_jsonb(r) order by r.business_name,r.loop_key) from ai_business_os_prod.command_center_revenue_loops_v1 r),'[]'::jsonb),
    'capital_allocator',(select allocator from ai_business_os_prod.command_center_portfolio_allocator_v1),
    'approval_queue',coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'request_key',q.request_key,
          'business_id',q.business_id,
          'title',q.title,
          'action_key',q.action_key,
          'status',q.status,
          'predicted_risk',q.predicted_risk,
          'expected_money_cents',q.expected_money_cents,
          'expires_at',q.expires_at,
          'intent_hash',q.intent_hash
        )
        order by q.expires_at
      )
      from ai_business_os_prod.approval_inbox q
      where q.status in ('PENDING','APPROVED')
    ),'[]'::jsonb)
  ) into v_payload;

  v_hash := encode(extensions.digest(v_payload::text,'sha256'),'hex');

  insert into ai_business_os_prod.command_center_snapshots(
    snapshot_key,snapshot_hash,payload,generated_at
  ) values (
    p_snapshot_key,v_hash,v_payload,v_generated
  )
  on conflict on constraint command_center_snapshots_snapshot_key_key
  do update set
    snapshot_hash=excluded.snapshot_hash,
    payload=excluded.payload,
    generated_at=excluded.generated_at;

  return query select p_snapshot_key,v_hash,v_generated;
end;
$$;

revoke execute on function ai_business_os_prod.refresh_command_center_snapshot(text)
from public, anon, authenticated;


-- MIGRATION 20260924223746 index_ai_business_os_portfolio_plan_creator_v1

create index if not exists idx_portfolio_plans_creator
  on ai_business_os_prod.portfolio_allocation_plans(created_by_agent_id);


-- MIGRATION 20260924230014 add_ai_business_os_schema_fingerprint_v1

create or replace function ai_business_os_prod.schema_fingerprint_v1()
returns text
language sql
stable
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
with table_meta as (
  select
    c.oid,
    n.nspname as schema_name,
    c.relname as object_name,
    c.relkind::text as relkind,
    c.relrowsecurity,
    coalesce(
      (
        select string_agg(
          a.attname || ':' ||
          pg_catalog.format_type(a.atttypid,a.atttypmod) || ':' ||
          a.attnotnull::text || ':' ||
          coalesce(pg_get_expr(ad.adbin,ad.adrelid),''),
          '|' order by a.attnum
        )
        from pg_attribute a
        left join pg_attrdef ad
          on ad.adrelid=a.attrelid and ad.adnum=a.attnum
        where a.attrelid=c.oid
          and a.attnum>0
          and not a.attisdropped
      ),
      ''
    ) as columns_def,
    coalesce(
      (
        select string_agg(pg_get_constraintdef(con.oid,true),'|' order by con.conname)
        from pg_constraint con
        where con.conrelid=c.oid
      ),
      ''
    ) as constraints_def,
    coalesce(
      (
        select string_agg(pg_get_indexdef(i.indexrelid),'|' order by ic.relname)
        from pg_index i
        join pg_class ic on ic.oid=i.indexrelid
        where i.indrelid=c.oid
      ),
      ''
    ) as indexes_def
  from pg_class c
  join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='ai_business_os_prod'
    and c.relkind in ('r','v','m')
),
function_meta as (
  select
    p.oid,
    p.proname,
    pg_get_function_identity_arguments(p.oid) as args,
    pg_get_functiondef(p.oid) as def
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='ai_business_os_prod'
),
trigger_meta as (
  select
    t.oid,
    c.relname as table_name,
    t.tgname,
    pg_get_triggerdef(t.oid,true) as def
  from pg_trigger t
  join pg_class c on c.oid=t.tgrelid
  join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='ai_business_os_prod'
    and not t.tgisinternal
),
policy_meta as (
  select schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
  from pg_policies
  where schemaname='ai_business_os_prod'
),
payload as (
  select string_agg(part,E'\n' order by part) as material
  from (
    select
      'TABLE|'||schema_name||'|'||object_name||'|'||relkind||'|'||
      relrowsecurity::text||'|'||columns_def||'|'||constraints_def||'|'||indexes_def
      as part
    from table_meta
    union all
    select 'FUNCTION|'||proname||'|'||args||'|'||def
    from function_meta
    union all
    select 'TRIGGER|'||table_name||'|'||tgname||'|'||def
    from trigger_meta
    union all
    select
      'POLICY|'||schemaname||'|'||tablename||'|'||policyname||'|'||
      permissive::text||'|'||array_to_string(roles,',')||'|'||cmd||'|'||
      coalesce(qual,'')||'|'||coalesce(with_check,'')
    from policy_meta
  ) x
)
select encode(extensions.digest(coalesce(material,''),'sha256'),'hex')
from payload;
$$;

revoke execute on function ai_business_os_prod.schema_fingerprint_v1()
from public, anon, authenticated;

-- MIGRATION 20260925132548 focus_ai_business_os_commercial_tracks_v1

create table if not exists ai_business_os_prod.commercial_track_policy (
  id uuid primary key default gen_random_uuid(),
  policy_key text not null unique,
  version integer not null,
  status text not null check (status in ('ACTIVE','SUPERSEDED')),
  primary_business_slugs jsonb not null,
  infrastructure_business_slugs jsonb not null,
  constraints jsonb not null,
  evidence jsonb not null,
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

alter table ai_business_os_prod.commercial_track_policy enable row level security;
revoke all on ai_business_os_prod.commercial_track_policy from public,anon,authenticated;

insert into ai_business_os_prod.commercial_track_policy(
  policy_key,version,status,primary_business_slugs,infrastructure_business_slugs,
  constraints,evidence,evidence_hash
) values (
  'commercial-focus-v1',1,'ACTIVE',
  '["freightrecovery","capturebrief"]'::jsonb,
  '["recoveryos"]'::jsonb,
  '{
    "new_primary_acquisition_tracks_require_policy_change": true,
    "recoveryos_customer_acquisition_priority": false,
    "recoveryworks_new_lane_requires_buyer_linked_evidence": true,
    "consequential_actions_authorized": false
  }'::jsonb,
  '{
    "capturebrief_loop":"capturebrief-outreach-001",
    "freightrecovery_loop":"freightrecovery-pilot-001",
    "basis":"existing measured buyer cohorts; no verified external outcome yet"
  }'::jsonb,
  encode(extensions.digest(
    'commercial-focus-v1|freightrecovery|capturebrief|recoveryos|existing-measured-cohorts',
    'sha256'
  ),'hex')
)
on conflict(policy_key) do update set
  version=excluded.version,status=excluded.status,
  primary_business_slugs=excluded.primary_business_slugs,
  infrastructure_business_slugs=excluded.infrastructure_business_slugs,
  constraints=excluded.constraints,evidence=excluded.evidence,
  evidence_hash=excluded.evidence_hash;

update ai_business_os_prod.businesses
set metadata=coalesce(metadata,'{}'::jsonb) || jsonb_build_object(
  'commercial_role',
  case slug
    when 'freightrecovery' then 'PRIMARY_VALIDATION_TRACK'
    when 'capturebrief' then 'PRIMARY_VALIDATION_TRACK'
    when 'recoveryos' then 'SHARED_INFRASTRUCTURE'
  end,
  'commercial_focus_policy','commercial-focus-v1'
),
updated_at=now()
where slug in ('freightrecovery','capturebrief','recoveryos');

update ai_business_os_prod.portfolio_initiatives
set owner_agent_id=case
  when initiative_key in ('freightrecovery','capturebrief') then 'agent-growth'
  when initiative_key='recoveryos' then 'agent-engineering'
  else owner_agent_id end,
updated_at=now()
where initiative_key in ('freightrecovery','capturebrief','recoveryos');

create or replace view ai_business_os_prod.commercial_focus_status_v1
with (security_invoker=true)
as
select
  b.slug,
  b.name,
  b.metadata->>'commercial_role' as commercial_role,
  i.owner_agent_id,
  r.loop_key,
  r.stage as revenue_loop_stage,
  r.opportunity_count,
  r.outreach_sent_count,
  r.external_reply_count,
  r.verified_outcomes,
  r.verified_learnings,
  case
    when b.metadata->>'commercial_role'='PRIMARY_VALIDATION_TRACK'
      and r.loop_key is not null then 'MEASURE_EXTERNAL_OUTCOME'
    when b.metadata->>'commercial_role'='SHARED_INFRASTRUCTURE'
      then 'SUPPORT_PRIMARY_TRACKS'
    else 'POLICY_REVIEW'
  end as next_operating_mode
from ai_business_os_prod.businesses b
left join ai_business_os_prod.portfolio_initiatives i on i.business_id=b.id
left join ai_business_os_prod.revenue_loop_status_v1 r on r.business_id=b.id
where b.slug in ('freightrecovery','capturebrief','recoveryos')
order by case b.slug when 'freightrecovery' then 1 when 'capturebrief' then 2 else 3 end;

-- MIGRATION 20260925133718 separate_ai_business_os_portfolio_pools_v1

create table if not exists ai_business_os_prod.portfolio_pools (
  pool_key text primary key,
  name text not null,
  objective text not null,
  status text not null check (status in ('ACTIVE','PAUSED','ARCHIVED')),
  scoring_model text not null check (scoring_model in ('B2B_CASH_FLOW','CONSUMER_RND')),
  required_metrics jsonb not null,
  allowed_resource_types jsonb not null,
  constraints jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table ai_business_os_prod.portfolio_pools enable row level security;
revoke all on ai_business_os_prod.portfolio_pools from public,anon,authenticated;

insert into ai_business_os_prod.portfolio_pools(
  pool_key,name,objective,status,scoring_model,required_metrics,allowed_resource_types,constraints
) values
(
  'b2b-cash-flow',
  'B2B Cash-Flow Portfolio',
  'Allocate scarce operating resources using realized economics, contracted/qualified demand, delivery effort, and time-to-cash evidence.',
  'ACTIVE',
  'B2B_CASH_FLOW',
  '[
    "cash_collected_30d",
    "cash_costs_30d",
    "ai_cost_30d",
    "contracted_pipeline_value_90d",
    "remaining_effort_hours",
    "time_to_cash_days",
    "market_evidence_signal"
  ]'::jsonb,
  '["AI_COST_UNITS","ENGINEERING_HOURS","HUMAN_HOURS","CASH_CENTS"]'::jsonb,
  '{
    "cross_pool_comparison_forbidden": true,
    "primary_validation_tracks":["freightrecovery","capturebrief"],
    "infrastructure_tracks":["recoveryos"]
  }'::jsonb
),
(
  'consumer-rnd',
  'Consumer / R&D Portfolio',
  'Allocate incubation resources using release-readiness, product-quality, playtest/engagement evidence, remaining effort, and development cost without forcing early-stage consumer products into cash-flow comparisons.',
  'ACTIVE',
  'CONSUMER_RND',
  '[
    "release_readiness_signal",
    "playtest_evidence_signal",
    "product_quality_signal",
    "content_pipeline_stability_signal",
    "remaining_effort_hours",
    "ai_cost_30d"
  ]'::jsonb,
  '["AI_COST_UNITS","ENGINEERING_HOURS","HUMAN_HOURS"]'::jsonb,
  '{
    "cross_pool_comparison_forbidden": true,
    "cash_allocation_requires_separate_policy": true,
    "revenue_not_required_pre_release": true
  }'::jsonb
)
on conflict(pool_key) do update set
  name=excluded.name,
  objective=excluded.objective,
  status=excluded.status,
  scoring_model=excluded.scoring_model,
  required_metrics=excluded.required_metrics,
  allowed_resource_types=excluded.allowed_resource_types,
  constraints=excluded.constraints,
  updated_at=now();

alter table ai_business_os_prod.portfolio_initiatives
  add column if not exists pool_key text references ai_business_os_prod.portfolio_pools(pool_key);

update ai_business_os_prod.portfolio_initiatives
set pool_key=case
  when initiative_key='starblox' then 'consumer-rnd'
  else 'b2b-cash-flow'
end,
updated_at=now()
where initiative_key in ('capturebrief','freightrecovery','recoveryos','starblox');

alter table ai_business_os_prod.portfolio_initiatives
  alter column pool_key set not null;

create index if not exists idx_portfolio_initiatives_pool
  on ai_business_os_prod.portfolio_initiatives(pool_key,status);

update ai_business_os_prod.businesses
set metadata=coalesce(metadata,'{}'::jsonb) || jsonb_build_object(
  'portfolio_pool',
  case when slug='starblox' then 'consumer-rnd' else 'b2b-cash-flow' end
),
updated_at=now()
where slug in ('capturebrief','freightrecovery','recoveryos','starblox');

-- Extend typed metric contracts for consumer/R&D evidence.
create or replace function ai_business_os_prod.portfolio_metric_allowed_source(
  p_metric text,
  p_source_type text
) returns boolean
language sql
immutable
set search_path = pg_temp
as $$
select case p_metric
  when 'cash_collected_30d' then upper(p_source_type) in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER')
  when 'revenue_recognized_30d' then upper(p_source_type) in ('GENERAL_LEDGER','INVOICE')
  when 'cash_costs_30d' then upper(p_source_type) in ('BANK','GENERAL_LEDGER','INVOICE')
  when 'ai_cost_30d' then upper(p_source_type) in ('INVOICE','GENERAL_LEDGER','PAYMENT_PROCESSOR')
  when 'contracted_pipeline_value_90d' then upper(p_source_type) in ('SIGNED_CONTRACT','CRM')
  when 'qualified_pipeline_value_90d' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD')
  when 'human_hours_30d' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'remaining_effort_hours' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'time_to_cash_days' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'retention_signal' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'market_evidence_signal' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'strategic_reuse_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'release_readiness_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'playtest_evidence_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'product_quality_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'content_pipeline_stability_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  else false
end;
$$;

create or replace function ai_business_os_prod.portfolio_metric_max_age_days(p_metric text)
returns integer
language sql
immutable
set search_path = pg_temp
as $$
select case p_metric
  when 'cash_collected_30d' then 45
  when 'revenue_recognized_30d' then 45
  when 'cash_costs_30d' then 45
  when 'ai_cost_30d' then 45
  when 'contracted_pipeline_value_90d' then 100
  when 'qualified_pipeline_value_90d' then 100
  when 'human_hours_30d' then 45
  when 'remaining_effort_hours' then 120
  when 'time_to_cash_days' then 120
  when 'retention_signal' then 120
  when 'market_evidence_signal' then 120
  when 'strategic_reuse_signal' then 120
  when 'release_readiness_signal' then 30
  when 'playtest_evidence_signal' then 30
  when 'product_quality_signal' then 30
  when 'content_pipeline_stability_signal' then 30
  else 0
end;
$$;

create or replace function ai_business_os_prod.validate_portfolio_snapshot()
returns trigger
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_metric text;
  v_value jsonb;
  v_num numeric;
  v_ev jsonb;
  v_source text;
  v_sha text;
  v_observed timestamptz;
  v_max_age integer;
  v_pool text;
  v_model text;
begin
  if jsonb_typeof(new.metrics) <> 'object' or jsonb_typeof(new.evidence) <> 'object' then
    raise exception 'metrics and evidence must be JSON objects';
  end if;

  select i.pool_key,p.scoring_model
  into v_pool,v_model
  from ai_business_os_prod.portfolio_initiatives i
  join ai_business_os_prod.portfolio_pools p on p.pool_key=i.pool_key
  where i.id=new.initiative_id;

  if v_pool is null then
    raise exception 'snapshot initiative has no portfolio pool';
  end if;

  for v_metric,v_value in select * from jsonb_each(new.metrics)
  loop
    if v_metric not in (
      'cash_collected_30d','revenue_recognized_30d','cash_costs_30d','ai_cost_30d',
      'contracted_pipeline_value_90d','qualified_pipeline_value_90d',
      'human_hours_30d','remaining_effort_hours','time_to_cash_days',
      'retention_signal','market_evidence_signal','strategic_reuse_signal',
      'release_readiness_signal','playtest_evidence_signal',
      'product_quality_signal','content_pipeline_stability_signal'
    ) then
      raise exception 'unknown portfolio metric: %',v_metric;
    end if;

    if v_model='B2B_CASH_FLOW'
       and v_metric in (
         'release_readiness_signal','playtest_evidence_signal',
         'product_quality_signal','content_pipeline_stability_signal'
       ) then
      raise exception 'consumer/R&D metric % cannot be used in B2B pool',v_metric;
    end if;

    if v_model='CONSUMER_RND'
       and v_metric in (
         'cash_collected_30d','revenue_recognized_30d','cash_costs_30d',
         'contracted_pipeline_value_90d','qualified_pipeline_value_90d',
         'time_to_cash_days','retention_signal','market_evidence_signal'
       ) then
      raise exception 'B2B cash-flow metric % cannot be used in consumer/R&D pool',v_metric;
    end if;

    if jsonb_typeof(v_value) <> 'number' then
      raise exception 'portfolio metric % must be numeric',v_metric;
    end if;
    v_num := (v_value#>>'{}')::numeric;
    if v_num < 0 then
      raise exception 'portfolio metric % cannot be negative',v_metric;
    end if;
    if v_metric in (
      'retention_signal','market_evidence_signal','strategic_reuse_signal',
      'release_readiness_signal','playtest_evidence_signal',
      'product_quality_signal','content_pipeline_stability_signal'
    ) and (v_num < 0 or v_num > 1) then
      raise exception 'signal metric % must be in [0,1]',v_metric;
    end if;

    v_ev := new.evidence -> v_metric;
    if v_ev is null then continue; end if;
    if jsonb_typeof(v_ev) <> 'object' then
      raise exception 'evidence for % must be an object',v_metric;
    end if;
    v_source := upper(coalesce(v_ev->>'source_type',''));
    if not ai_business_os_prod.portfolio_metric_allowed_source(v_metric,v_source) then
      raise exception 'source type % is inadmissible for %',v_source,v_metric;
    end if;
    v_sha := lower(coalesce(v_ev->>'source_sha256',''));
    if v_sha !~ '^[0-9a-f]{64}$' then
      raise exception 'source SHA-256 required for %',v_metric;
    end if;
    v_observed := (v_ev->>'observed_at')::timestamptz;
    if v_observed is null or v_observed > new.as_of then
      raise exception 'evidence observed_at invalid for %',v_metric;
    end if;
    v_max_age := ai_business_os_prod.portfolio_metric_max_age_days(v_metric);
    if new.as_of - v_observed > make_interval(days=>v_max_age) then
      raise exception 'evidence is stale for %',v_metric;
    end if;
    if v_ev ? 'allocation_grade'
       and jsonb_typeof(v_ev->'allocation_grade') <> 'boolean' then
      raise exception 'allocation_grade must be boolean for %',v_metric;
    end if;
  end loop;

  for v_metric,v_ev in select * from jsonb_each(new.evidence)
  loop
    if not (new.metrics ? v_metric) then
      raise exception 'evidence supplied for absent metric: %',v_metric;
    end if;
  end loop;

  return new;
end;
$$;

-- StarBlox no longer inherits B2B evidence gaps.
delete from ai_business_os_prod.portfolio_data_gaps
where initiative_id=(
  select id from ai_business_os_prod.portfolio_initiatives where initiative_key='starblox'
);

insert into ai_business_os_prod.portfolio_data_gaps(
  initiative_id,metric_key,gap_type,priority,recommended_source_type,rationale
)
select i.id,g.metric_key,g.gap_type,g.priority,g.source_type,g.rationale
from ai_business_os_prod.portfolio_initiatives i
cross join (
  values
  ('release_readiness_signal','MISSING',100,'ANALYTICS/MANUAL_RECORD','Need a bounded release-readiness assessment tied to current build/test evidence.'),
  ('playtest_evidence_signal','MISSING',95,'ANALYTICS/MANUAL_RECORD','Need actual bounded playtest evidence; repository activity is not player evidence.'),
  ('product_quality_signal','MISSING',90,'ANALYTICS/MANUAL_RECORD','Need measured product-quality evidence from tests/review, not subjective optimism.'),
  ('content_pipeline_stability_signal','MISSING',85,'ANALYTICS/MANUAL_RECORD','Need evidence that question/content/art pipelines run reliably at current head.'),
  ('remaining_effort_hours','MISSING',80,'ANALYTICS/MANUAL_RECORD','Need evidence-backed remaining effort for incubation resource planning.'),
  ('ai_cost_30d','MISSING',75,'INVOICE/GENERAL_LEDGER','Need attributable AI/tool cost before comparing incubation efficiency.')
) as g(metric_key,gap_type,priority,source_type,rationale)
where i.initiative_key='starblox'
on conflict(initiative_id,metric_key,gap_type) do update set
  priority=excluded.priority,
  recommended_source_type=excluded.recommended_source_type,
  rationale=excluded.rationale,
  resolved_at=null;

create or replace view ai_business_os_prod.portfolio_pool_status_v1
with (security_invoker=true)
as
select
  p.pool_key,
  p.name as pool_name,
  p.scoring_model,
  p.objective,
  p.required_metrics,
  p.allowed_resource_types,
  p.constraints,
  count(i.id) filter (where i.status='ACTIVE') as active_initiatives,
  coalesce(jsonb_agg(
    jsonb_build_object(
      'initiative_key',i.initiative_key,
      'name',i.name,
      'owner_agent_id',i.owner_agent_id,
      'status',i.status
    ) order by i.name
  ) filter (where i.id is not null),'[]'::jsonb) as initiatives
from ai_business_os_prod.portfolio_pools p
left join ai_business_os_prod.portfolio_initiatives i on i.pool_key=p.pool_key
where p.status='ACTIVE'
group by p.pool_key,p.name,p.scoring_model,p.objective,p.required_metrics,p.allowed_resource_types,p.constraints
order by p.pool_key;

create or replace view ai_business_os_prod.portfolio_pool_gap_status_v1
with (security_invoker=true)
as
select
  i.pool_key,
  i.initiative_key,
  i.name,
  count(g.id) filter (where g.resolved_at is null) as open_gap_count,
  coalesce(jsonb_agg(
    jsonb_build_object(
      'metric_key',g.metric_key,
      'gap_type',g.gap_type,
      'priority',g.priority,
      'recommended_source_type',g.recommended_source_type,
      'rationale',g.rationale
    ) order by g.priority desc,g.metric_key
  ) filter (where g.id is not null and g.resolved_at is null),'[]'::jsonb) as open_gaps
from ai_business_os_prod.portfolio_initiatives i
left join ai_business_os_prod.portfolio_data_gaps g on g.initiative_id=i.id
where i.status='ACTIVE'
group by i.pool_key,i.initiative_key,i.name
order by i.pool_key,i.initiative_key;



-- MIGRATION 20260925133954 add_ai_business_os_pool_scoped_allocator_v1

update ai_business_os_prod.portfolio_pools p
set constraints=p.constraints || case p.pool_key
  when 'b2b-cash-flow' then '{"min_evidence_coverage":0.60,"max_allocation_share":0.50}'::jsonb
  when 'consumer-rnd' then '{"min_evidence_coverage":0.67,"max_allocation_share":0.50}'::jsonb
  else '{}'::jsonb end,
updated_at=now()
where p.pool_key in ('b2b-cash-flow','consumer-rnd');

create table ai_business_os_prod.portfolio_pool_rankings (
  id uuid primary key default gen_random_uuid(),
  ranking_key text not null unique,
  pool_key text not null references ai_business_os_prod.portfolio_pools(pool_key),
  as_of timestamptz not null,
  snapshot_set_hash text not null check (snapshot_set_hash ~ '^[0-9a-f]{64}$'),
  rows jsonb not null,
  ranking_hash text not null unique check (ranking_hash ~ '^[0-9a-f]{64}$'),
  created_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  created_at timestamptz not null default now()
);

create table ai_business_os_prod.portfolio_pool_allocation_plans (
  id uuid primary key default gen_random_uuid(),
  plan_key text not null unique,
  ranking_id uuid not null references ai_business_os_prod.portfolio_pool_rankings(id),
  pool_key text not null references ai_business_os_prod.portfolio_pools(pool_key),
  resource_type text not null check (
    resource_type in ('AI_COST_UNITS','ENGINEERING_HOURS','HUMAN_HOURS','CASH_CENTS')
  ),
  total_units numeric,
  allocations jsonb not null default '[]'::jsonb,
  status text not null check (
    status in ('DRAFT','BLOCKED_INSUFFICIENT_EVIDENCE','PENDING_APPROVAL','AUTHORIZED','EXECUTED','CANCELLED')
  ),
  block_reason text,
  plan_hash text not null unique check (plan_hash ~ '^[0-9a-f]{64}$'),
  approval_request_key text references ai_business_os_prod.approval_inbox(request_key),
  execution_receipt_id uuid references ai_business_os_prod.autonomy_action_receipts(id),
  created_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table ai_business_os_prod.portfolio_pool_rankings enable row level security;
alter table ai_business_os_prod.portfolio_pool_allocation_plans enable row level security;
revoke all on ai_business_os_prod.portfolio_pool_rankings,
  ai_business_os_prod.portfolio_pool_allocation_plans
from public,anon,authenticated;

create index idx_portfolio_pool_rankings_pool_time
  on ai_business_os_prod.portfolio_pool_rankings(pool_key,created_at desc);
create index idx_portfolio_pool_rankings_creator
  on ai_business_os_prod.portfolio_pool_rankings(created_by_agent_id);
create index idx_portfolio_pool_plans_ranking
  on ai_business_os_prod.portfolio_pool_allocation_plans(ranking_id);
create index idx_portfolio_pool_plans_pool_status
  on ai_business_os_prod.portfolio_pool_allocation_plans(pool_key,status);
create index idx_portfolio_pool_plans_creator
  on ai_business_os_prod.portfolio_pool_allocation_plans(created_by_agent_id);

create or replace function ai_business_os_prod.portfolio_score_consumer_snapshot(
  p_snapshot_id uuid,
  p_pool_key text
) returns jsonb
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  s ai_business_os_prod.portfolio_snapshots%rowtype;
  p ai_business_os_prod.portfolio_pools%rowtype;
  m jsonb; e jsonb;
  q_release numeric; q_playtest numeric; q_quality numeric; q_pipeline numeric;
  q_effort numeric; q_ai numeric;
  release_signal numeric; playtest numeric; quality numeric; pipeline numeric;
  effort numeric; ai_cost numeric;
  signal_score numeric; effort_penalty numeric; raw_score numeric;
  coverage numeric; evidence_factor numeric; score numeric;
  eligible boolean; state text;
begin
  select * into s
  from ai_business_os_prod.portfolio_snapshots ps
  where ps.id=p_snapshot_id;
  if not found then raise exception 'unknown portfolio snapshot'; end if;

  select * into p
  from ai_business_os_prod.portfolio_pools pp
  where pp.pool_key=p_pool_key;
  if not found or p.scoring_model<>'CONSUMER_RND' then
    raise exception 'consumer scoring requires a CONSUMER_RND pool';
  end if;

  if not exists(
    select 1
    from ai_business_os_prod.portfolio_initiatives pi
    where pi.id=s.initiative_id and pi.pool_key=p_pool_key
  ) then
    raise exception 'snapshot initiative does not belong to requested pool';
  end if;

  m:=s.metrics; e:=s.evidence;
  q_release:=ai_business_os_prod.portfolio_metric_quality(e,'release_readiness_signal');
  q_playtest:=ai_business_os_prod.portfolio_metric_quality(e,'playtest_evidence_signal');
  q_quality:=ai_business_os_prod.portfolio_metric_quality(e,'product_quality_signal');
  q_pipeline:=ai_business_os_prod.portfolio_metric_quality(e,'content_pipeline_stability_signal');
  q_effort:=ai_business_os_prod.portfolio_metric_quality(e,'remaining_effort_hours');
  q_ai:=ai_business_os_prod.portfolio_metric_quality(e,'ai_cost_30d');

  release_signal:=case when q_release>0 then coalesce((m->>'release_readiness_signal')::numeric,0) else 0 end;
  playtest:=case when q_playtest>0 then coalesce((m->>'playtest_evidence_signal')::numeric,0) else 0 end;
  quality:=case when q_quality>0 then coalesce((m->>'product_quality_signal')::numeric,0) else 0 end;
  pipeline:=case when q_pipeline>0 then coalesce((m->>'content_pipeline_stability_signal')::numeric,0) else 0 end;
  effort:=case when q_effort>0 then coalesce((m->>'remaining_effort_hours')::numeric,0) else 0 end;
  ai_cost:=case when q_ai>0 then coalesce((m->>'ai_cost_30d')::numeric,0) else 0 end;

  signal_score :=
    release_signal*q_release*0.30 +
    playtest*q_playtest*0.30 +
    quality*q_quality*0.20 +
    pipeline*q_pipeline*0.20;

  effort_penalty := ln(1+effort)*0.03 + ln(1+ai_cost)*0.01;
  raw_score:=signal_score-effort_penalty;
  coverage:=(
    (case when q_release>0 then 1 else 0 end) +
    (case when q_playtest>0 then 1 else 0 end) +
    (case when q_quality>0 then 1 else 0 end) +
    (case when q_pipeline>0 then 1 else 0 end) +
    (case when q_effort>0 then 1 else 0 end) +
    (case when q_ai>0 then 1 else 0 end)
  )::numeric / 6.0;
  evidence_factor:=coverage*coverage;
  score:=raw_score*evidence_factor;
  eligible:=coverage >= (p.constraints->>'min_evidence_coverage')::numeric and score>0;

  state:=case
    when coverage < (p.constraints->>'min_evidence_coverage')::numeric then 'OBSERVE_ONLY'
    when score>0 then 'ALLOCATE_CANDIDATE'
    else 'MAINTAIN_REVIEW'
  end;

  return jsonb_build_object(
    'snapshot_id',s.id,
    'initiative_id',s.initiative_id,
    'as_of',s.as_of,
    'scoring_model','CONSUMER_RND',
    'release_readiness_component',release_signal*q_release*0.30,
    'playtest_component',playtest*q_playtest*0.30,
    'product_quality_component',quality*q_quality*0.20,
    'content_pipeline_component',pipeline*q_pipeline*0.20,
    'effort_penalty_component',effort_penalty,
    'raw_score',raw_score,
    'evidence_coverage',coverage,
    'evidence_factor',evidence_factor,
    'decision_support_score',score,
    'eligible_for_allocation',eligible,
    'decision_state',state
  );
end;
$$;

create or replace function ai_business_os_prod.refresh_portfolio_pool_ranking(
  p_ranking_key text,
  p_pool_key text,
  p_created_by_agent_id text
) returns table(
  out_ranking_key text,
  out_pool_key text,
  out_ranking_hash text,
  out_eligible_count integer
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_pool ai_business_os_prod.portfolio_pools%rowtype;
  v_policy ai_business_os_prod.portfolio_allocator_policies%rowtype;
  v_as_of timestamptz;
  v_rows jsonb;
  v_snapshot_set_hash text;
  v_ranking_hash text;
  v_eligible integer;
begin
  select * into v_pool
  from ai_business_os_prod.portfolio_pools pp
  where pp.pool_key=p_pool_key and pp.status='ACTIVE';
  if not found then raise exception 'unknown or inactive portfolio pool'; end if;

  if not exists(
    select 1 from ai_business_os_prod.agents a
    where a.agent_id=p_created_by_agent_id and a.status='ACTIVE'
  ) then
    raise exception 'ranking creator must be active';
  end if;

  if v_pool.scoring_model='B2B_CASH_FLOW' then
    select * into v_policy
    from ai_business_os_prod.portfolio_allocator_policies ap
    where ap.policy_key='portfolio-default'
    order by ap.version desc limit 1;
    if not found then raise exception 'B2B allocator policy missing'; end if;
  end if;

  with latest as (
    select distinct on (ps.initiative_id) ps.*
    from ai_business_os_prod.portfolio_snapshots ps
    join ai_business_os_prod.portfolio_initiatives pi on pi.id=ps.initiative_id
    where pi.pool_key=p_pool_key and pi.status='ACTIVE'
    order by ps.initiative_id,ps.as_of desc,ps.created_at desc
  )
  select max(l.as_of) into v_as_of from latest l;
  if v_as_of is null then raise exception 'no snapshots for portfolio pool'; end if;

  with latest as (
    select distinct on (ps.initiative_id) ps.*
    from ai_business_os_prod.portfolio_snapshots ps
    join ai_business_os_prod.portfolio_initiatives pi on pi.id=ps.initiative_id
    where pi.pool_key=p_pool_key and pi.status='ACTIVE'
    order by ps.initiative_id,ps.as_of desc,ps.created_at desc
  ), scored as (
    select
      pi.initiative_key,
      pi.name,
      ps.id as snapshot_id,
      ps.snapshot_hash,
      case
        when v_pool.scoring_model='B2B_CASH_FLOW'
          then ai_business_os_prod.portfolio_score_snapshot(ps.id,v_policy.id)
        else ai_business_os_prod.portfolio_score_consumer_snapshot(ps.id,p_pool_key)
      end as score
    from latest ps
    join ai_business_os_prod.portfolio_initiatives pi on pi.id=ps.initiative_id
  ), ranked as (
    select *,
      row_number() over(
        order by
          (score->>'eligible_for_allocation')::boolean desc,
          (score->>'decision_support_score')::numeric desc,
          (score->>'evidence_coverage')::numeric desc,
          initiative_key
      ) as formula_rank
    from scored
  )
  select
    jsonb_agg(
      jsonb_build_object(
        'initiative_key',r.initiative_key,
        'name',r.name,
        'snapshot_id',r.snapshot_id,
        'snapshot_hash',r.snapshot_hash,
        'formula_rank',r.formula_rank,
        'pool_key',p_pool_key,
        'scoring_model',v_pool.scoring_model
      ) || r.score
      order by r.formula_rank
    ),
    count(*) filter(where (r.score->>'eligible_for_allocation')::boolean)
  into v_rows,v_eligible
  from ranked r;

  with latest as (
    select distinct on (ps.initiative_id) ps.id,ps.snapshot_hash
    from ai_business_os_prod.portfolio_snapshots ps
    join ai_business_os_prod.portfolio_initiatives pi on pi.id=ps.initiative_id
    where pi.pool_key=p_pool_key and pi.status='ACTIVE'
    order by ps.initiative_id,ps.as_of desc,ps.created_at desc
  )
  select encode(
    extensions.digest(
      coalesce(string_agg(l.id::text||':'||l.snapshot_hash,'|' order by l.id),''),
      'sha256'
    ),'hex'
  ) into v_snapshot_set_hash
  from latest l;

  v_ranking_hash:=encode(
    extensions.digest(
      p_pool_key||'|'||v_pool.scoring_model||'|'||
      v_snapshot_set_hash||'|'||coalesce(v_rows::text,'[]'),
      'sha256'
    ),'hex'
  );

  insert into ai_business_os_prod.portfolio_pool_rankings(
    ranking_key,pool_key,as_of,snapshot_set_hash,rows,ranking_hash,created_by_agent_id
  ) values (
    p_ranking_key,p_pool_key,v_as_of,v_snapshot_set_hash,coalesce(v_rows,'[]'::jsonb),
    v_ranking_hash,p_created_by_agent_id
  )
  on conflict on constraint portfolio_pool_rankings_ranking_key_key
  do update set
    pool_key=excluded.pool_key,
    as_of=excluded.as_of,
    snapshot_set_hash=excluded.snapshot_set_hash,
    rows=excluded.rows,
    ranking_hash=excluded.ranking_hash,
    created_by_agent_id=excluded.created_by_agent_id,
    created_at=now();

  return query select p_ranking_key,p_pool_key,v_ranking_hash,v_eligible;
end;
$$;

create or replace function ai_business_os_prod.create_portfolio_pool_plan(
  p_plan_key text,
  p_ranking_key text,
  p_resource_type text,
  p_total_units numeric,
  p_created_by_agent_id text
) returns table(
  out_plan_key text,
  out_status text,
  out_plan_hash text
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_ranking ai_business_os_prod.portfolio_pool_rankings%rowtype;
  v_pool ai_business_os_prod.portfolio_pools%rowtype;
  v_rows jsonb;
  v_count integer;
  v_score_sum numeric;
  v_max_share numeric;
  v_allocations jsonb:='[]'::jsonb;
  v_allocated numeric:=0;
  v_row jsonb;
  v_units numeric;
  v_share numeric;
  v_hash text;
  v_status text;
  v_block text;
begin
  select * into v_ranking
  from ai_business_os_prod.portfolio_pool_rankings r
  where r.ranking_key=p_ranking_key;
  if not found then raise exception 'unknown pool ranking'; end if;

  select * into v_pool
  from ai_business_os_prod.portfolio_pools pp
  where pp.pool_key=v_ranking.pool_key;
  if not found then raise exception 'pool missing'; end if;

  if not (v_pool.allowed_resource_types ? p_resource_type) then
    raise exception 'resource type % is not allowed in pool %',p_resource_type,v_pool.pool_key;
  end if;

  select coalesce(jsonb_agg(x),'[]'::jsonb),count(*),
         coalesce(sum((x->>'decision_support_score')::numeric),0)
  into v_rows,v_count,v_score_sum
  from jsonb_array_elements(v_ranking.rows) x
  where coalesce((x->>'eligible_for_allocation')::boolean,false)
    and (x->>'decision_support_score')::numeric>0;

  if v_count=0 then
    v_status:='BLOCKED_INSUFFICIENT_EVIDENCE';
    v_block:='No initiative in this portfolio pool satisfies its pool-specific evidence threshold.';
    v_hash:=encode(extensions.digest(
      p_plan_key||'|'||v_ranking.ranking_hash||'|'||p_resource_type||'|BLOCKED',
      'sha256'),'hex');

    insert into ai_business_os_prod.portfolio_pool_allocation_plans(
      plan_key,ranking_id,pool_key,resource_type,total_units,allocations,status,
      block_reason,plan_hash,created_by_agent_id
    ) values (
      p_plan_key,v_ranking.id,v_pool.pool_key,p_resource_type,p_total_units,
      '[]'::jsonb,v_status,v_block,v_hash,p_created_by_agent_id
    )
    on conflict on constraint portfolio_pool_allocation_plans_plan_key_key
    do update set
      ranking_id=excluded.ranking_id,pool_key=excluded.pool_key,
      resource_type=excluded.resource_type,total_units=excluded.total_units,
      allocations=excluded.allocations,status=excluded.status,
      block_reason=excluded.block_reason,plan_hash=excluded.plan_hash,
      approval_request_key=null,execution_receipt_id=null,
      created_by_agent_id=excluded.created_by_agent_id,updated_at=now();

    return query select p_plan_key,v_status,v_hash;
    return;
  end if;

  if p_total_units is null or p_total_units<=0 then
    raise exception 'positive total units required';
  end if;

  v_max_share:=(v_pool.constraints->>'max_allocation_share')::numeric;
  for v_row in select * from jsonb_array_elements(v_rows)
  loop
    v_share:=least(v_max_share,(v_row->>'decision_support_score')::numeric/nullif(v_score_sum,0));
    v_units:=p_total_units*v_share;
    v_allocated:=v_allocated+v_units;
    v_allocations:=v_allocations||jsonb_build_array(jsonb_build_object(
      'initiative_key',v_row->>'initiative_key',
      'units',v_units,
      'share',v_units/p_total_units,
      'pool_key',v_pool.pool_key
    ));
  end loop;

  if v_allocated<p_total_units then
    v_allocations:=v_allocations||jsonb_build_array(jsonb_build_object(
      'initiative_key','__RESERVE__',
      'units',p_total_units-v_allocated,
      'share',(p_total_units-v_allocated)/p_total_units,
      'pool_key',v_pool.pool_key
    ));
  end if;

  v_status:='DRAFT';
  v_hash:=encode(extensions.digest(
    p_plan_key||'|'||v_ranking.ranking_hash||'|'||p_resource_type||'|'||
    p_total_units::text||'|'||v_allocations::text,'sha256'),'hex');

  insert into ai_business_os_prod.portfolio_pool_allocation_plans(
    plan_key,ranking_id,pool_key,resource_type,total_units,allocations,status,
    plan_hash,created_by_agent_id
  ) values (
    p_plan_key,v_ranking.id,v_pool.pool_key,p_resource_type,p_total_units,
    v_allocations,v_status,v_hash,p_created_by_agent_id
  )
  on conflict on constraint portfolio_pool_allocation_plans_plan_key_key
  do update set
    ranking_id=excluded.ranking_id,pool_key=excluded.pool_key,
    resource_type=excluded.resource_type,total_units=excluded.total_units,
    allocations=excluded.allocations,status=excluded.status,
    block_reason=null,plan_hash=excluded.plan_hash,
    approval_request_key=null,execution_receipt_id=null,
    created_by_agent_id=excluded.created_by_agent_id,updated_at=now();

  return query select p_plan_key,v_status,v_hash;
end;
$$;

revoke execute on function ai_business_os_prod.portfolio_score_consumer_snapshot(uuid,text)
from public,anon,authenticated;
revoke execute on function ai_business_os_prod.refresh_portfolio_pool_ranking(text,text,text)
from public,anon,authenticated;
revoke execute on function ai_business_os_prod.create_portfolio_pool_plan(text,text,text,numeric,text)
from public,anon,authenticated;

select * from ai_business_os_prod.refresh_portfolio_pool_ranking(
  'b2b-cash-flow-ranking-current','b2b-cash-flow','agent-finance'
);
select * from ai_business_os_prod.refresh_portfolio_pool_ranking(
  'consumer-rnd-ranking-current','consumer-rnd','agent-finance'
);

select * from ai_business_os_prod.create_portfolio_pool_plan(
  'b2b-engineering-readiness-current',
  'b2b-cash-flow-ranking-current','ENGINEERING_HOURS',null,'agent-finance'
);
select * from ai_business_os_prod.create_portfolio_pool_plan(
  'consumer-rnd-engineering-readiness-current',
  'consumer-rnd-ranking-current','ENGINEERING_HOURS',null,'agent-finance'
);

create or replace view ai_business_os_prod.portfolio_pool_ranking_status_v1
with (security_invoker=true)
as
select
  r.pool_key,
  p.name as pool_name,
  p.scoring_model,
  r.ranking_key,
  r.ranking_hash,
  r.as_of,
  x->>'initiative_key' as initiative_key,
  x->>'name' as initiative_name,
  (x->>'formula_rank')::integer as formula_rank,
  (x->>'eligible_for_allocation')::boolean as eligible_for_allocation,
  (x->>'evidence_coverage')::numeric as evidence_coverage,
  (x->>'decision_support_score')::numeric as decision_support_score,
  x->>'decision_state' as decision_state
from ai_business_os_prod.portfolio_pool_rankings r
join ai_business_os_prod.portfolio_pools p on p.pool_key=r.pool_key
cross join lateral jsonb_array_elements(r.rows) x
where r.ranking_key in ('b2b-cash-flow-ranking-current','consumer-rnd-ranking-current')
order by r.pool_key,(x->>'formula_rank')::integer;

create or replace view ai_business_os_prod.command_center_portfolio_pools_v1
with (security_invoker=true)
as
select jsonb_build_object(
  'pools',coalesce((
    select jsonb_agg(to_jsonb(s) order by s.pool_key)
    from ai_business_os_prod.portfolio_pool_status_v1 s
  ),'[]'::jsonb),
  'rankings',coalesce((
    select jsonb_agg(to_jsonb(r) order by r.pool_key,r.formula_rank)
    from ai_business_os_prod.portfolio_pool_ranking_status_v1 r
  ),'[]'::jsonb),
  'gaps',coalesce((
    select jsonb_agg(to_jsonb(g) order by g.pool_key,g.initiative_key)
    from ai_business_os_prod.portfolio_pool_gap_status_v1 g
  ),'[]'::jsonb),
  'plans',coalesce((
    select jsonb_agg(jsonb_build_object(
      'plan_key',plan_key,
      'pool_key',pool_key,
      'resource_type',resource_type,
      'status',status,
      'block_reason',block_reason,
      'plan_hash',plan_hash
    ) order by pool_key,resource_type)
    from ai_business_os_prod.portfolio_pool_allocation_plans
    where plan_key in (
      'b2b-engineering-readiness-current',
      'consumer-rnd-engineering-readiness-current'
    )
  ),'[]'::jsonb)
) as portfolio_pools;



-- MIGRATION 20260925134039 integrate_ai_business_os_portfolio_pools_command_center_v1

update ai_business_os_prod.portfolio_initiatives
set owner_agent_id='agent-product',updated_at=now()
where initiative_key='starblox';

create or replace view ai_business_os_prod.command_center_portfolio_allocator_v2
with (security_invoker=true)
as
select portfolio_pools as allocator
from ai_business_os_prod.command_center_portfolio_pools_v1;

drop function if exists ai_business_os_prod.refresh_command_center_snapshot(text);

create function ai_business_os_prod.refresh_command_center_snapshot(
  p_snapshot_key text
) returns table (
  out_snapshot_key text,
  out_snapshot_hash text,
  out_generated_at timestamptz
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_payload jsonb;
  v_hash text;
  v_generated timestamptz := now();
begin
  if coalesce(trim(p_snapshot_key),'')='' then
    raise exception 'snapshot key required';
  end if;

  select jsonb_build_object(
    'generated_at',v_generated,
    'system',(select to_jsonb(s) from ai_business_os_prod.command_center_system_v1 s),
    'portfolio',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from ai_business_os_prod.command_center_portfolio_v1 p),'[]'::jsonb),
    'agents',coalesce((select jsonb_agg(to_jsonb(a) order by a.display_name) from ai_business_os_prod.command_center_agents_v1 a),'[]'::jsonb),
    'revenue_loops',coalesce((select jsonb_agg(to_jsonb(r) order by r.business_name,r.loop_key) from ai_business_os_prod.command_center_revenue_loops_v1 r),'[]'::jsonb),
    'portfolio_allocator',(select allocator from ai_business_os_prod.command_center_portfolio_allocator_v2),
    'approval_queue',coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'request_key',q.request_key,
          'business_id',q.business_id,
          'title',q.title,
          'action_key',q.action_key,
          'status',q.status,
          'predicted_risk',q.predicted_risk,
          'expected_money_cents',q.expected_money_cents,
          'expires_at',q.expires_at,
          'intent_hash',q.intent_hash
        )
        order by q.expires_at
      )
      from ai_business_os_prod.approval_inbox q
      where q.status in ('PENDING','APPROVED')
    ),'[]'::jsonb)
  ) into v_payload;

  v_hash := encode(extensions.digest(v_payload::text,'sha256'),'hex');

  insert into ai_business_os_prod.command_center_snapshots(
    snapshot_key,snapshot_hash,payload,generated_at
  ) values (
    p_snapshot_key,v_hash,v_payload,v_generated
  )
  on conflict on constraint command_center_snapshots_snapshot_key_key
  do update set
    snapshot_hash=excluded.snapshot_hash,
    payload=excluded.payload,
    generated_at=excluded.generated_at;

  return query select p_snapshot_key,v_hash,v_generated;
end;
$$;

revoke execute on function ai_business_os_prod.refresh_command_center_snapshot(text)
from public,anon,authenticated;

select * from ai_business_os_prod.refresh_command_center_snapshot(
  'ceo-command-center-v2-portfolio-pools'
);

-- MIGRATION 20260925141123 normalize_ai_business_os_rights_provenance_v1

create table if not exists ai_business_os_prod.rights_subjects (
  id uuid primary key default gen_random_uuid(),
  subject_key text not null unique,
  subject_type text not null check (subject_type in (
    'REPOSITORY_CODE','DATASET','MODEL_WEIGHTS','STANDARD_SPEC','BUNDLED_ASSET',
    'TRADEMARK_PATENT','API_SERVICE','OTHER'
  )),
  source_locator text not null,
  revision text,
  public_license text,
  origin_subsystem text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.rights_evidence_objects (
  id uuid primary key default gen_random_uuid(),
  evidence_key text not null unique,
  evidence_class text not null check (evidence_class in (
    'PUBLIC_LICENSE_VERIFIED',
    'OWNER_ATTESTED',
    'EXECUTED_PERMISSION_VERIFIED',
    'UNKNOWN_REVIEW',
    'DENIED'
  )),
  evidence_location text,
  evidence_sha256 text check (
    evidence_sha256 is null or evidence_sha256 ~ '^[0-9a-f]{64}$'
  ),
  verification_status text not null check (
    verification_status in ('VERIFIED','UNVERIFIED','REJECTED')
  ),
  verifier_kind text not null check (
    verifier_kind in ('PUBLIC_SOURCE','OWNER','INDEPENDENT','SYSTEM','UNKNOWN')
  ),
  observed_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.rights_scope_state (
  subject_id uuid not null references ai_business_os_prod.rights_subjects(id),
  scope_key text not null check (scope_key in (
    'commercial_use','hosted_saas','redistribution','assignment','sublicensing',
    'change_of_control','datasets','model_weights','bundled_assets','trademarks_patents'
  )),
  scope_status text not null check (scope_status in (
    'ALLOWED','ALLOWED_WITH_CONDITIONS','DENIED','UNKNOWN_REVIEW','NOT_APPLICABLE'
  )),
  evidence_id uuid references ai_business_os_prod.rights_evidence_objects(id),
  conditions jsonb not null default '[]'::jsonb,
  rationale text not null,
  updated_at timestamptz not null default now(),
  primary key(subject_id,scope_key),
  check (
    scope_status='UNKNOWN_REVIEW'
    or evidence_id is not null
  )
);

create table if not exists ai_business_os_prod.rights_global_assertions (
  assertion_key text primary key,
  evidence_class text not null check (evidence_class in (
    'OWNER_ATTESTED','EXECUTED_PERMISSION_VERIFIED','UNKNOWN_REVIEW','DENIED'
  )),
  subject_selector text not null,
  statement text not null,
  automatic_scope_effect boolean not null default false,
  evidence_location text,
  evidence_sha256 text check (
    evidence_sha256 is null or evidence_sha256 ~ '^[0-9a-f]{64}$'
  ),
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.rights_subsystem_policy (
  subsystem_key text primary key,
  canonical_registry_required boolean not null default true,
  default_stage text not null check (default_stage in (
    'ANALYSIS','CONTROLLED_PILOT','HOSTED_SAAS','ACQUIRER_DILIGENCE'
  )),
  allow_global_assertion_auto_effect boolean not null default false,
  notes text not null,
  updated_at timestamptz not null default now()
);

alter table ai_business_os_prod.rights_subjects enable row level security;
alter table ai_business_os_prod.rights_evidence_objects enable row level security;
alter table ai_business_os_prod.rights_scope_state enable row level security;
alter table ai_business_os_prod.rights_global_assertions enable row level security;
alter table ai_business_os_prod.rights_subsystem_policy enable row level security;

revoke all on ai_business_os_prod.rights_subjects,
  ai_business_os_prod.rights_evidence_objects,
  ai_business_os_prod.rights_scope_state,
  ai_business_os_prod.rights_global_assertions,
  ai_business_os_prod.rights_subsystem_policy
from public,anon,authenticated;

create index if not exists idx_rights_subjects_origin
  on ai_business_os_prod.rights_subjects(origin_subsystem,subject_type);
create index if not exists idx_rights_scope_evidence
  on ai_business_os_prod.rights_scope_state(evidence_id);
create index if not exists idx_rights_evidence_class
  on ai_business_os_prod.rights_evidence_objects(evidence_class,verification_status);

insert into ai_business_os_prod.rights_subsystem_policy(
  subsystem_key,canonical_registry_required,default_stage,
  allow_global_assertion_auto_effect,notes
) values
('hunter',true,'ANALYSIS',false,'Standing owner assertion is recorded as provenance only and never auto-promotes repository scopes.'),
('freight',true,'CONTROLLED_PILOT',false,'Controlled-pilot runtime use requires scope-specific canonical rights readiness.'),
('recoveryworks',true,'ANALYSIS',false,'New runtime/imported components must resolve through canonical rights state before pilot promotion.'),
('ai_business_os',true,'ANALYSIS',false,'Production tools/components must not derive rights from graph presence or generic assertions.')
on conflict(subsystem_key) do update set
  canonical_registry_required=excluded.canonical_registry_required,
  default_stage=excluded.default_stage,
  allow_global_assertion_auto_effect=excluded.allow_global_assertion_auto_effect,
  notes=excluded.notes,
  updated_at=now();

insert into ai_business_os_prod.rights_global_assertions(
  assertion_key,evidence_class,subject_selector,statement,
  automatic_scope_effect,evidence_location,evidence_sha256
) values (
  'hunter-standing-owner-attestation-2026-09-19',
  'OWNER_ATTESTED',
  'repository_owned_public_code',
  'Owner states separate commercial permission exists for repository-owned public GitHub code/content used in the hunt.',
  false,
  'MASTER.md',
  null
)
on conflict(assertion_key) do update set
  evidence_class=excluded.evidence_class,
  subject_selector=excluded.subject_selector,
  statement=excluded.statement,
  automatic_scope_effect=false,
  evidence_location=excluded.evidence_location,
  evidence_sha256=excluded.evidence_sha256;

with seed as (
  select * from jsonb_to_recordset('[{"subject_key":"emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","repository":"emoss08/Trenova","revision":"95fcf816562025ad9af864ded4a5fce8a555bd65","public_license":"FSL-1.1-ALv2","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE_EXACT_REVISION","evidence_key":"owner-attestation:emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","repository":"kodekinetics79/opstrax-enterprise-build","revision":"fec2ba1432d6f8b4ba4c48be3d58e7e096819045","public_license":"NO_PUBLIC_LICENSE_RECORDED","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_PERMISSION","evidence_key":"owner-attestation:kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","repository":"sengtha/Kareya-Silo","revision":"a43eedea03add0728eadfc1f8ea35cc3ca6867cc","public_license":"Apache-2.0","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","repository":"vidyesh95/qatoto-backend","revision":"4f5f270f6ba5ef3ed4b230716997ccea049ce408","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","repository":"A-Jatin/freight-ratecon-extraction","revision":"a3dbbfec7f6b042176880d06c5114f81f29e57eb","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","repository":"OmarFaig/Assay","revision":"821303935ef2855908a9a9bd1efd4c33f9cd39d2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","repository":"srthck/trustmesh","revision":"5a93d70b37aafecaf61a5bc0296eaf831e5504ac","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_AND_USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE","evidence_key":"public-license:srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","repository":"mgilbir/formalis","revision":"2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","repository":"DominicFinn/open_tms","revision":"93d8c2b8ff78373ff69bb7ea546743e4703628b1","public_license":"MIT","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","repository":"justicebajaj161/Freight-Audit-Console","revision":"c2d4c07310a77e20ee21a74fc96d49df783c2e3a","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","repository":"WRBriska/InvoiceAudit","revision":"bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","repository":"AnsonLai/docx-redline-js","revision":"e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","repository":"kingsleyonoh/sla-penalty-settlement-engine","revision":"ea66727de51df7ee67a9f03f2549845fa6247b3d","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","repository":"yaogdu/AgentLedger","revision":"dd966e3b3d9eb54032c51701d30efcfbaa2379b0","public_license":"Apache-2.0","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","repository":"microsoft/duroxide-python","revision":"0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","repository":"fleetbase/fleetbase","revision":"4ff6980c6db6f3e8103b3ec425a089aa6d251af4","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","repository":"Budget-Lab-Yale/tariff-rate-tracker","revision":"5a977726af0ead299e7db9cbca018b04dc2cc2e6","public_license":"MIT","runtime_status":"PINNED_SOURCE_DATA_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"}]'::jsonb) as x(
    subject_key text,
    repository text,
    revision text,
    public_license text,
    runtime_status text,
    legacy_basis text,
    evidence_key text,
    evidence_class text,
    evidence_location text,
    evidence_sha text,
    commercial_status text,
    hosted_saas text,
    assignment text,
    sublicensing text,
    change_of_control text
  )
)
insert into ai_business_os_prod.rights_subjects(
  subject_key,subject_type,source_locator,revision,public_license,origin_subsystem,metadata
)
select
  s.subject_key,'REPOSITORY_CODE',s.repository,s.revision,s.public_license,'freight',
  jsonb_build_object(
    'runtime_status',s.runtime_status,
    'legacy_commercial_use_basis',s.legacy_basis,
    'imported_from','freight/COMPONENT_RIGHTS_REGISTRY.json'
  )
from seed s
on conflict(subject_key) do update set
  source_locator=excluded.source_locator,
  revision=excluded.revision,
  public_license=excluded.public_license,
  metadata=excluded.metadata,
  updated_at=now();

with seed as (
  select * from jsonb_to_recordset('[{"subject_key":"emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","repository":"emoss08/Trenova","revision":"95fcf816562025ad9af864ded4a5fce8a555bd65","public_license":"FSL-1.1-ALv2","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE_EXACT_REVISION","evidence_key":"owner-attestation:emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","repository":"kodekinetics79/opstrax-enterprise-build","revision":"fec2ba1432d6f8b4ba4c48be3d58e7e096819045","public_license":"NO_PUBLIC_LICENSE_RECORDED","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_PERMISSION","evidence_key":"owner-attestation:kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","repository":"sengtha/Kareya-Silo","revision":"a43eedea03add0728eadfc1f8ea35cc3ca6867cc","public_license":"Apache-2.0","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","repository":"vidyesh95/qatoto-backend","revision":"4f5f270f6ba5ef3ed4b230716997ccea049ce408","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","repository":"A-Jatin/freight-ratecon-extraction","revision":"a3dbbfec7f6b042176880d06c5114f81f29e57eb","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","repository":"OmarFaig/Assay","revision":"821303935ef2855908a9a9bd1efd4c33f9cd39d2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","repository":"srthck/trustmesh","revision":"5a93d70b37aafecaf61a5bc0296eaf831e5504ac","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_AND_USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE","evidence_key":"public-license:srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","repository":"mgilbir/formalis","revision":"2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","repository":"DominicFinn/open_tms","revision":"93d8c2b8ff78373ff69bb7ea546743e4703628b1","public_license":"MIT","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","repository":"justicebajaj161/Freight-Audit-Console","revision":"c2d4c07310a77e20ee21a74fc96d49df783c2e3a","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","repository":"WRBriska/InvoiceAudit","revision":"bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","repository":"AnsonLai/docx-redline-js","revision":"e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","repository":"kingsleyonoh/sla-penalty-settlement-engine","revision":"ea66727de51df7ee67a9f03f2549845fa6247b3d","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","repository":"yaogdu/AgentLedger","revision":"dd966e3b3d9eb54032c51701d30efcfbaa2379b0","public_license":"Apache-2.0","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","repository":"microsoft/duroxide-python","revision":"0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","repository":"fleetbase/fleetbase","revision":"4ff6980c6db6f3e8103b3ec425a089aa6d251af4","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","repository":"Budget-Lab-Yale/tariff-rate-tracker","revision":"5a977726af0ead299e7db9cbca018b04dc2cc2e6","public_license":"MIT","runtime_status":"PINNED_SOURCE_DATA_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"}]'::jsonb) as x(
    subject_key text,
    repository text,
    revision text,
    public_license text,
    runtime_status text,
    legacy_basis text,
    evidence_key text,
    evidence_class text,
    evidence_location text,
    evidence_sha text,
    commercial_status text,
    hosted_saas text,
    assignment text,
    sublicensing text,
    change_of_control text
  )
)
insert into ai_business_os_prod.rights_evidence_objects(
  evidence_key,evidence_class,evidence_location,evidence_sha256,
  verification_status,verifier_kind,observed_at,metadata
)
select
  s.evidence_key,
  s.evidence_class,
  s.evidence_location,
  nullif(s.evidence_sha,''),
  case when s.evidence_class='UNKNOWN_REVIEW' then 'UNVERIFIED' else 'VERIFIED' end,
  case
    when s.evidence_class='OWNER_ATTESTED' then 'OWNER'
    when s.evidence_class='PUBLIC_LICENSE_VERIFIED' then 'PUBLIC_SOURCE'
    else 'UNKNOWN'
  end,
  now(),
  jsonb_build_object(
    'subject_key',s.subject_key,
    'legacy_basis',s.legacy_basis,
    'imported_from','freight rights registries'
  )
from seed s
on conflict(evidence_key) do update set
  evidence_class=excluded.evidence_class,
  evidence_location=excluded.evidence_location,
  evidence_sha256=excluded.evidence_sha256,
  verification_status=excluded.verification_status,
  verifier_kind=excluded.verifier_kind,
  observed_at=excluded.observed_at,
  metadata=excluded.metadata;

with seed as (
  select * from jsonb_to_recordset('[{"subject_key":"emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","repository":"emoss08/Trenova","revision":"95fcf816562025ad9af864ded4a5fce8a555bd65","public_license":"FSL-1.1-ALv2","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE_EXACT_REVISION","evidence_key":"owner-attestation:emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","repository":"kodekinetics79/opstrax-enterprise-build","revision":"fec2ba1432d6f8b4ba4c48be3d58e7e096819045","public_license":"NO_PUBLIC_LICENSE_RECORDED","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_PERMISSION","evidence_key":"owner-attestation:kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","repository":"sengtha/Kareya-Silo","revision":"a43eedea03add0728eadfc1f8ea35cc3ca6867cc","public_license":"Apache-2.0","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","repository":"vidyesh95/qatoto-backend","revision":"4f5f270f6ba5ef3ed4b230716997ccea049ce408","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","repository":"A-Jatin/freight-ratecon-extraction","revision":"a3dbbfec7f6b042176880d06c5114f81f29e57eb","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","repository":"OmarFaig/Assay","revision":"821303935ef2855908a9a9bd1efd4c33f9cd39d2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","repository":"srthck/trustmesh","revision":"5a93d70b37aafecaf61a5bc0296eaf831e5504ac","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_AND_USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE","evidence_key":"public-license:srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","repository":"mgilbir/formalis","revision":"2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","repository":"DominicFinn/open_tms","revision":"93d8c2b8ff78373ff69bb7ea546743e4703628b1","public_license":"MIT","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","repository":"justicebajaj161/Freight-Audit-Console","revision":"c2d4c07310a77e20ee21a74fc96d49df783c2e3a","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","repository":"WRBriska/InvoiceAudit","revision":"bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","repository":"AnsonLai/docx-redline-js","revision":"e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","repository":"kingsleyonoh/sla-penalty-settlement-engine","revision":"ea66727de51df7ee67a9f03f2549845fa6247b3d","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","repository":"yaogdu/AgentLedger","revision":"dd966e3b3d9eb54032c51701d30efcfbaa2379b0","public_license":"Apache-2.0","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","repository":"microsoft/duroxide-python","revision":"0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","repository":"fleetbase/fleetbase","revision":"4ff6980c6db6f3e8103b3ec425a089aa6d251af4","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","repository":"Budget-Lab-Yale/tariff-rate-tracker","revision":"5a977726af0ead299e7db9cbca018b04dc2cc2e6","public_license":"MIT","runtime_status":"PINNED_SOURCE_DATA_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"}]'::jsonb) as x(
    subject_key text,
    repository text,
    revision text,
    public_license text,
    runtime_status text,
    legacy_basis text,
    evidence_key text,
    evidence_class text,
    evidence_location text,
    evidence_sha text,
    commercial_status text,
    hosted_saas text,
    assignment text,
    sublicensing text,
    change_of_control text
  )
), expanded as (
  select s.subject_key,s.evidence_key,'commercial_use'::text as scope_key,s.commercial_status as scope_status
  from seed s
  union all select s.subject_key,s.evidence_key,'hosted_saas',s.hosted_saas from seed s
  union all select s.subject_key,s.evidence_key,'assignment',s.assignment from seed s
  union all select s.subject_key,s.evidence_key,'sublicensing',s.sublicensing from seed s
  union all select s.subject_key,s.evidence_key,'change_of_control',s.change_of_control from seed s
  union all select s.subject_key,null,'redistribution','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'datasets','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'model_weights','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'bundled_assets','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'trademarks_patents','UNKNOWN_REVIEW' from seed s
)
insert into ai_business_os_prod.rights_scope_state(
  subject_id,scope_key,scope_status,evidence_id,conditions,rationale
)
select
  rs.id,
  e.scope_key,
  e.scope_status,
  case when e.scope_status='UNKNOWN_REVIEW' then null else reo.id end,
  case
    when e.scope_status='ALLOWED_WITH_CONDITIONS'
      then '["license/compliance obligations must be satisfied before runtime use"]'::jsonb
    else '[]'::jsonb
  end,
  case
    when e.scope_status='UNKNOWN_REVIEW' then 'No scope-specific evidence currently resolves this right.'
    when reo.evidence_class='OWNER_ATTESTED' then 'Scope resolved only to the extent stated by the owner attestation; no stronger evidence class is inferred.'
    when reo.evidence_class='PUBLIC_LICENSE_VERIFIED' then 'Scope reflects recorded public-license evidence; independently owned dependencies/data/assets remain separate.'
    else 'Canonical imported rights state.'
  end
from expanded e
join ai_business_os_prod.rights_subjects rs on rs.subject_key=e.subject_key
left join ai_business_os_prod.rights_evidence_objects reo on reo.evidence_key=e.evidence_key
on conflict(subject_id,scope_key) do update set
  scope_status=excluded.scope_status,
  evidence_id=excluded.evidence_id,
  conditions=excluded.conditions,
  rationale=excluded.rationale,
  updated_at=now();

create or replace view ai_business_os_prod.rights_canonical_status_v1
with (security_invoker=true)
as
select
  s.subject_key,
  s.subject_type,
  s.source_locator,
  s.revision,
  s.public_license,
  s.origin_subsystem,
  sc.scope_key,
  sc.scope_status,
  e.evidence_class,
  e.verification_status,
  e.evidence_location,
  e.evidence_sha256,
  sc.conditions,
  sc.rationale
from ai_business_os_prod.rights_subjects s
join ai_business_os_prod.rights_scope_state sc on sc.subject_id=s.id
left join ai_business_os_prod.rights_evidence_objects e on e.id=sc.evidence_id
order by s.subject_key,sc.scope_key;

create or replace function ai_business_os_prod.rights_stage_readiness_v1(
  p_subject_key text,
  p_stage text
) returns jsonb
language plpgsql
stable
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_subject uuid;
  v_required text[];
  v_missing text[] := '{}';
  v_denied text[] := '{}';
  v_conditional text[] := '{}';
  v_scope text;
  v_status text;
  v_evidence_class text;
  v_state text;
begin
  if p_stage not in ('ANALYSIS','CONTROLLED_PILOT','HOSTED_SAAS','ACQUIRER_DILIGENCE') then
    raise exception 'unsupported rights stage';
  end if;

  select id into v_subject
  from ai_business_os_prod.rights_subjects
  where subject_key=p_subject_key;

  if v_subject is null then
    return jsonb_build_object(
      'subject_key',p_subject_key,
      'stage',p_stage,
      'state','BLOCKED',
      'reason','SUBJECT_NOT_REGISTERED'
    );
  end if;

  if p_stage='ANALYSIS' then
    return jsonb_build_object(
      'subject_key',p_subject_key,
      'stage',p_stage,
      'state','ANALYSIS_ONLY',
      'reason','Analysis/provenance may proceed without implying runtime permission.'
    );
  elsif p_stage='CONTROLLED_PILOT' then
    v_required:=array['commercial_use'];
  elsif p_stage='HOSTED_SAAS' then
    v_required:=array['commercial_use','hosted_saas'];
  else
    v_required:=array[
      'commercial_use','hosted_saas','redistribution',
      'assignment','sublicensing','change_of_control'
    ];
  end if;

  foreach v_scope in array v_required
  loop
    select sc.scope_status,e.evidence_class
    into v_status,v_evidence_class
    from ai_business_os_prod.rights_scope_state sc
    left join ai_business_os_prod.rights_evidence_objects e on e.id=sc.evidence_id
    where sc.subject_id=v_subject and sc.scope_key=v_scope;

    if v_status is null or v_status='UNKNOWN_REVIEW' then
      v_missing:=array_append(v_missing,v_scope);
    elsif v_status='DENIED' then
      v_denied:=array_append(v_denied,v_scope);
    elsif v_status='ALLOWED_WITH_CONDITIONS' then
      v_conditional:=array_append(v_conditional,v_scope);
    elsif v_status='ALLOWED' and v_evidence_class not in (
      'PUBLIC_LICENSE_VERIFIED','OWNER_ATTESTED','EXECUTED_PERMISSION_VERIFIED'
    ) then
      v_missing:=array_append(v_missing,v_scope);
    end if;
  end loop;

  v_state:=case
    when cardinality(v_denied)>0 then 'BLOCKED'
    when cardinality(v_missing)>0 then 'BLOCKED'
    when cardinality(v_conditional)>0 then 'CONDITIONAL'
    else 'READY'
  end;

  return jsonb_build_object(
    'subject_key',p_subject_key,
    'stage',p_stage,
    'state',v_state,
    'missing_scopes',to_jsonb(v_missing),
    'denied_scopes',to_jsonb(v_denied),
    'conditional_scopes',to_jsonb(v_conditional),
    'global_assertions_auto_effect',false
  );
end;
$$;

revoke execute on function ai_business_os_prod.rights_stage_readiness_v1(text,text)
from public,anon,authenticated;



-- MIGRATION 20260925141435 harden_ai_business_os_rights_provenance_v1

alter table ai_business_os_prod.rights_evidence_objects
  add constraint rights_executed_permission_requires_verified_sha
  check (
    evidence_class <> 'EXECUTED_PERMISSION_VERIFIED'
    or (
      verification_status='VERIFIED'
      and evidence_sha256 is not null
      and evidence_sha256 ~ '^[0-9a-f]{64}$'
    )
  );

alter table ai_business_os_prod.rights_global_assertions
  add constraint rights_global_assertions_never_auto_scope
  check (automatic_scope_effect=false);

-- MIGRATION 20260925144434 create_ai_business_os_verified_external_outcomes_v1

create table if not exists ai_business_os_prod.external_outcomes (
  id uuid primary key default gen_random_uuid(),
  outcome_key text not null unique,
  initiative_id uuid not null references ai_business_os_prod.portfolio_initiatives(id),
  business_id uuid references ai_business_os_prod.businesses(id),
  product_id uuid references ai_business_os_prod.products(id),
  revenue_loop_id uuid references ai_business_os_prod.revenue_loops(id),
  opportunity_id uuid references ai_business_os_prod.opportunities(id),
  outcome_type text not null check (outcome_type in (
    'BUYER_POSITIVE_REPLY',
    'BUYER_NEGATIVE_REPLY',
    'SIGNED_ENGAGEMENT',
    'COLLECTED_REVENUE',
    'RECOVERED_FUNDS',
    'DELIVERY_HOURS',
    'DELIVERY_COST_CENTS',
    'AI_COST_CENTS',
    'EXPLICIT_NO_VALUE',
    'PLAYTEST_POSITIVE_SIGNAL',
    'PLAYTEST_NEGATIVE_SIGNAL',
    'PLAYTEST_RETENTION_SIGNAL'
  )),
  outcome_value_cents bigint check (outcome_value_cents is null or outcome_value_cents >= 0),
  outcome_value_numeric numeric check (outcome_value_numeric is null or outcome_value_numeric >= 0),
  unit text,
  occurred_at timestamptz not null,
  source_type text not null check (source_type in (
    'BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER','INVOICE',
    'SIGNED_CONTRACT','CRM','EMAIL','ANALYTICS','MANUAL_RECORD','PLAYTEST_ANALYTICS'
  )),
  source_ref text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  verification_status text not null check (
    verification_status in ('VERIFIED','REJECTED')
  ),
  created_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  verified_by_agent_id text not null references ai_business_os_prod.agents(agent_id),
  verified_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (created_by_agent_id <> verified_by_agent_id)
);

create table if not exists ai_business_os_prod.external_outcome_learning (
  outcome_id uuid primary key references ai_business_os_prod.external_outcomes(id),
  memory_id uuid not null references ai_business_os_prod.memory_items(id),
  memory_observation_id uuid not null references ai_business_os_prod.memory_observations(id),
  revenue_loop_learning_id uuid references ai_business_os_prod.revenue_loop_learning(id),
  reward numeric not null check (reward between -1 and 1),
  evidence_hash text not null check (evidence_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

alter table ai_business_os_prod.revenue_loop_outcomes
  add column if not exists external_outcome_id uuid
  references ai_business_os_prod.external_outcomes(id);

create unique index if not exists idx_revenue_loop_outcomes_external_outcome
  on ai_business_os_prod.revenue_loop_outcomes(external_outcome_id)
  where external_outcome_id is not null;

alter table ai_business_os_prod.external_outcomes enable row level security;
alter table ai_business_os_prod.external_outcome_learning enable row level security;
revoke all on ai_business_os_prod.external_outcomes,
  ai_business_os_prod.external_outcome_learning
from public,anon,authenticated;

create index if not exists idx_external_outcomes_initiative_time
  on ai_business_os_prod.external_outcomes(initiative_id,occurred_at desc);
create index if not exists idx_external_outcomes_business_type_time
  on ai_business_os_prod.external_outcomes(business_id,outcome_type,occurred_at desc);
create index if not exists idx_external_outcomes_opportunity_time
  on ai_business_os_prod.external_outcomes(opportunity_id,occurred_at desc);
create index if not exists idx_external_outcomes_loop_time
  on ai_business_os_prod.external_outcomes(revenue_loop_id,occurred_at desc);
create index if not exists idx_external_outcomes_verifier
  on ai_business_os_prod.external_outcomes(verified_by_agent_id,verified_at desc);

create or replace function ai_business_os_prod.validate_external_outcome_v1()
returns trigger
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_creator_role text;
  v_verifier_role text;
  v_initiative ai_business_os_prod.portfolio_initiatives%rowtype;
  v_loop ai_business_os_prod.revenue_loops%rowtype;
  v_opp ai_business_os_prod.opportunities%rowtype;
begin
  select * into v_initiative
  from ai_business_os_prod.portfolio_initiatives
  where id=new.initiative_id;

  if not found or v_initiative.status<>'ACTIVE' then
    raise exception 'external outcome requires an active initiative';
  end if;

  if new.business_id is distinct from v_initiative.business_id then
    raise exception 'external outcome business does not match initiative';
  end if;
  if new.product_id is distinct from v_initiative.product_id then
    raise exception 'external outcome product does not match initiative';
  end if;

  select role_key into v_creator_role
  from ai_business_os_prod.agents
  where agent_id=new.created_by_agent_id and status='ACTIVE';
  select role_key into v_verifier_role
  from ai_business_os_prod.agents
  where agent_id=new.verified_by_agent_id and status='ACTIVE';

  if v_creator_role is null or v_verifier_role is null then
    raise exception 'creator and verifier must be active agents';
  end if;
  if v_verifier_role not in ('AUDITOR_REDTEAM','FINANCE_ANALYTICS') then
    raise exception 'external outcome verifier must be Auditor/Red Team or Finance/Analytics';
  end if;

  if new.verification_status='VERIFIED' and new.verified_at < new.occurred_at then
    raise exception 'verified_at cannot predate occurred_at';
  end if;

  if new.revenue_loop_id is not null then
    select * into v_loop
    from ai_business_os_prod.revenue_loops
    where id=new.revenue_loop_id;
    if not found then raise exception 'unknown revenue loop'; end if;
    if v_loop.business_id is distinct from new.business_id then
      raise exception 'revenue loop business mismatch';
    end if;
    if v_loop.product_id is distinct from new.product_id then
      raise exception 'revenue loop product mismatch';
    end if;
  end if;

  if new.opportunity_id is not null then
    select * into v_opp
    from ai_business_os_prod.opportunities
    where id=new.opportunity_id;
    if not found then raise exception 'unknown opportunity'; end if;
    if v_opp.business_id is distinct from new.business_id then
      raise exception 'opportunity business mismatch';
    end if;
    if v_opp.product_id is distinct from new.product_id then
      raise exception 'opportunity product mismatch';
    end if;
  end if;

  if new.outcome_type in (
    'BUYER_POSITIVE_REPLY','BUYER_NEGATIVE_REPLY','SIGNED_ENGAGEMENT',
    'COLLECTED_REVENUE','RECOVERED_FUNDS','EXPLICIT_NO_VALUE'
  ) and new.opportunity_id is null then
    raise exception 'buyer/commercial outcome requires opportunity_id';
  end if;

  if new.outcome_type='SIGNED_ENGAGEMENT' then
    if new.outcome_value_cents is null then
      raise exception 'SIGNED_ENGAGEMENT requires outcome_value_cents';
    end if;
    if new.source_type not in ('SIGNED_CONTRACT','CRM') then
      raise exception 'SIGNED_ENGAGEMENT requires SIGNED_CONTRACT or CRM evidence';
    end if;
  elsif new.outcome_type='COLLECTED_REVENUE' then
    if new.outcome_value_cents is null then
      raise exception 'COLLECTED_REVENUE requires outcome_value_cents';
    end if;
    if new.source_type not in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER') then
      raise exception 'COLLECTED_REVENUE requires cash-ledger evidence';
    end if;
  elsif new.outcome_type='RECOVERED_FUNDS' then
    if new.outcome_value_cents is null then
      raise exception 'RECOVERED_FUNDS requires outcome_value_cents';
    end if;
    if new.source_type not in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER','CRM') then
      raise exception 'RECOVERED_FUNDS requires settlement/customer evidence';
    end if;
  elsif new.outcome_type='DELIVERY_COST_CENTS' then
    if new.outcome_value_cents is null then
      raise exception 'DELIVERY_COST_CENTS requires outcome_value_cents';
    end if;
    if new.source_type not in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER','INVOICE') then
      raise exception 'DELIVERY_COST_CENTS requires cost-ledger evidence';
    end if;
  elsif new.outcome_type='AI_COST_CENTS' then
    if new.outcome_value_cents is null then
      raise exception 'AI_COST_CENTS requires outcome_value_cents';
    end if;
    if new.source_type not in ('PAYMENT_PROCESSOR','GENERAL_LEDGER','INVOICE') then
      raise exception 'AI_COST_CENTS requires invoice/ledger evidence';
    end if;
  elsif new.outcome_type='DELIVERY_HOURS' then
    if new.outcome_value_numeric is null or coalesce(new.unit,'')<>'hours' then
      raise exception 'DELIVERY_HOURS requires numeric hours';
    end if;
    if new.source_type not in ('ANALYTICS','MANUAL_RECORD') then
      raise exception 'DELIVERY_HOURS requires analytics/manual evidence';
    end if;
  elsif new.outcome_type in ('BUYER_POSITIVE_REPLY','BUYER_NEGATIVE_REPLY','EXPLICIT_NO_VALUE') then
    if new.source_type not in ('CRM','EMAIL','ANALYTICS','MANUAL_RECORD') then
      raise exception 'buyer response outcome requires customer-response evidence';
    end if;
  elsif new.outcome_type in ('PLAYTEST_POSITIVE_SIGNAL','PLAYTEST_NEGATIVE_SIGNAL') then
    if new.source_type not in ('PLAYTEST_ANALYTICS','ANALYTICS','MANUAL_RECORD') then
      raise exception 'playtest outcome requires playtest/analytics evidence';
    end if;
  elsif new.outcome_type='PLAYTEST_RETENTION_SIGNAL' then
    if new.outcome_value_numeric is null
       or new.outcome_value_numeric < 0
       or new.outcome_value_numeric > 1 then
      raise exception 'PLAYTEST_RETENTION_SIGNAL requires numeric value in [0,1]';
    end if;
    if new.source_type not in ('PLAYTEST_ANALYTICS','ANALYTICS') then
      raise exception 'PLAYTEST_RETENTION_SIGNAL requires analytics evidence';
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_validate_external_outcome_v1
on ai_business_os_prod.external_outcomes;

create trigger trg_validate_external_outcome_v1
before insert or update on ai_business_os_prod.external_outcomes
for each row execute function ai_business_os_prod.validate_external_outcome_v1();

create or replace function ai_business_os_prod.portfolio_source_quality(p_source_type text)
returns numeric
language sql
immutable
set search_path = pg_temp
as $$
select case upper(p_source_type)
  when 'VERIFIED_OUTCOME_LEDGER' then 1.00
  when 'BANK' then 1.00
  when 'PAYMENT_PROCESSOR' then 0.95
  when 'GENERAL_LEDGER' then 0.95
  when 'SIGNED_CONTRACT' then 0.90
  when 'INVOICE' then 0.85
  when 'CRM' then 0.60
  when 'ANALYTICS' then 0.70
  when 'MANUAL_RECORD' then 0.50
  when 'MODEL_ESTIMATE' then 0.20
  else 0.00
end::numeric;
$$;

create or replace function ai_business_os_prod.portfolio_metric_allowed_source(
  p_metric text,
  p_source_type text
) returns boolean
language sql
immutable
set search_path = pg_temp
as $$
select case p_metric
  when 'cash_collected_30d' then upper(p_source_type) in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER','VERIFIED_OUTCOME_LEDGER')
  when 'revenue_recognized_30d' then upper(p_source_type) in ('GENERAL_LEDGER','INVOICE','VERIFIED_OUTCOME_LEDGER')
  when 'cash_costs_30d' then upper(p_source_type) in ('BANK','GENERAL_LEDGER','INVOICE','VERIFIED_OUTCOME_LEDGER')
  when 'ai_cost_30d' then upper(p_source_type) in ('INVOICE','GENERAL_LEDGER','PAYMENT_PROCESSOR','VERIFIED_OUTCOME_LEDGER')
  when 'contracted_pipeline_value_90d' then upper(p_source_type) in ('SIGNED_CONTRACT','CRM','VERIFIED_OUTCOME_LEDGER')
  when 'qualified_pipeline_value_90d' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','VERIFIED_OUTCOME_LEDGER')
  when 'human_hours_30d' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','VERIFIED_OUTCOME_LEDGER')
  when 'remaining_effort_hours' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'time_to_cash_days' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE','VERIFIED_OUTCOME_LEDGER')
  when 'retention_signal' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE','VERIFIED_OUTCOME_LEDGER')
  when 'market_evidence_signal' then upper(p_source_type) in ('CRM','ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE','VERIFIED_OUTCOME_LEDGER')
  when 'strategic_reuse_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','MODEL_ESTIMATE')
  when 'release_readiness_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'playtest_evidence_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD','VERIFIED_OUTCOME_LEDGER')
  when 'product_quality_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  when 'content_pipeline_stability_signal' then upper(p_source_type) in ('ANALYTICS','MANUAL_RECORD')
  else false
end;
$$;



-- MIGRATION 20260925144636 wire_ai_business_os_outcomes_to_allocator_memory_v1

create or replace function ai_business_os_prod.refresh_external_outcome_snapshot_v1(
  p_initiative_id uuid,
  p_trigger_outcome_key text,
  p_actor_agent_id text
) returns uuid
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_i ai_business_os_prod.portfolio_initiatives%rowtype;
  v_pool ai_business_os_prod.portfolio_pools%rowtype;
  v_prev ai_business_os_prod.portfolio_snapshots%rowtype;
  v_metrics jsonb := '{}'::jsonb;
  v_evidence jsonb := '{}'::jsonb;
  v_as_of timestamptz := now();
  v_count integer;
  v_positive integer;
  v_sum_cents numeric;
  v_sum_numeric numeric;
  v_avg numeric;
  v_latest timestamptz;
  v_hash text;
  v_source_hash text;
  v_snapshot_key text;
  v_snapshot_id uuid;
  v_signed_count integer;
  v_open_signed_cents numeric;
begin
  select * into v_i
  from ai_business_os_prod.portfolio_initiatives
  where id=p_initiative_id and status='ACTIVE';
  if not found then raise exception 'unknown active initiative'; end if;

  select * into v_pool
  from ai_business_os_prod.portfolio_pools
  where pool_key=v_i.pool_key and status='ACTIVE';
  if not found then raise exception 'initiative pool missing/inactive'; end if;

  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_actor_agent_id and status='ACTIVE'
  ) then
    raise exception 'snapshot actor must be active';
  end if;

  select * into v_prev
  from ai_business_os_prod.portfolio_snapshots
  where initiative_id=p_initiative_id
  order by as_of desc,created_at desc
  limit 1;

  if found then
    v_metrics:=coalesce(v_prev.metrics,'{}'::jsonb);
    v_evidence:=coalesce(v_prev.evidence,'{}'::jsonb);
  end if;

  if v_pool.scoring_model='B2B_CASH_FLOW' then
    -- Collected business revenue in the last 30 days.
    select count(*),coalesce(sum(outcome_value_cents),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='COLLECTED_REVENUE'
      and occurred_at >= v_as_of-interval '30 days'
      and occurred_at <= v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{cash_collected_30d}',to_jsonb(v_sum_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{cash_collected_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER',
        'source_ref','external-outcomes:'||v_i.initiative_key||':cash_collected_30d',
        'source_sha256',v_source_hash,
        'observed_at',v_latest,
        'allocation_grade',true,
        'sample_count',v_count,
        'basis','verified collected-revenue outcomes only'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='cash_collected_30d';
    elsif v_evidence->'cash_collected_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'cash_collected_30d';
      v_evidence:=v_evidence-'cash_collected_30d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='cash_collected_30d';
    end if;

    -- Verified delivery costs in the last 30 days.
    select count(*),coalesce(sum(outcome_value_cents),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='DELIVERY_COST_CENTS'
      and occurred_at >= v_as_of-interval '30 days'
      and occurred_at <= v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{cash_costs_30d}',to_jsonb(v_sum_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{cash_costs_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':cash_costs_30d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'sample_count',v_count,'basis','verified delivery-cost outcomes only'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='cash_costs_30d';
    elsif v_evidence->'cash_costs_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'cash_costs_30d';
      v_evidence:=v_evidence-'cash_costs_30d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='cash_costs_30d';
    end if;

    -- Verified AI/tool costs in the last 30 days.
    select count(*),coalesce(sum(outcome_value_cents),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='AI_COST_CENTS'
      and occurred_at >= v_as_of-interval '30 days'
      and occurred_at <= v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{ai_cost_30d}',to_jsonb(v_sum_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{ai_cost_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':ai_cost_30d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'sample_count',v_count,'basis','verified AI/tool-cost outcomes only'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='ai_cost_30d';
    elsif v_evidence->'ai_cost_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'ai_cost_30d';
      v_evidence:=v_evidence-'ai_cost_30d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='ai_cost_30d';
    end if;

    -- Signed-but-not-yet-collected engagements are contracted pipeline.
    select
      count(*),
      coalesce(sum(case when not exists(
        select 1
        from ai_business_os_prod.external_outcomes c
        where c.initiative_id=s.initiative_id
          and c.opportunity_id=s.opportunity_id
          and c.verification_status='VERIFIED'
          and c.outcome_type='COLLECTED_REVENUE'
          and c.occurred_at>=s.occurred_at
      ) then s.outcome_value_cents else 0 end),0),
      max(s.occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(s.outcome_key||':'||s.source_sha256,'|' order by s.outcome_key),''),
        'sha256'
      ),'hex')
    into v_signed_count,v_open_signed_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes s
    where s.initiative_id=p_initiative_id
      and s.verification_status='VERIFIED'
      and s.outcome_type='SIGNED_ENGAGEMENT'
      and s.occurred_at>=v_as_of-interval '90 days'
      and s.occurred_at<=v_as_of;

    if v_signed_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{contracted_pipeline_value_90d}',to_jsonb(v_open_signed_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{contracted_pipeline_value_90d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':contracted_pipeline_value_90d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'signed_engagement_count',v_signed_count,
        'basis','verified signed engagements less opportunities with verified collected revenue'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='contracted_pipeline_value_90d';
    elsif v_evidence->'contracted_pipeline_value_90d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'contracted_pipeline_value_90d';
      v_evidence:=v_evidence-'contracted_pipeline_value_90d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='contracted_pipeline_value_90d';
    end if;

    -- Actual delivery hours are useful efficiency evidence.
    select count(*),coalesce(sum(outcome_value_numeric),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_numeric,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='DELIVERY_HOURS'
      and occurred_at>=v_as_of-interval '30 days'
      and occurred_at<=v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{human_hours_30d}',to_jsonb(v_sum_numeric),true);
      v_evidence:=jsonb_set(v_evidence,'{human_hours_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':human_hours_30d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'sample_count',v_count,'basis','verified delivery-hour outcomes'
      ),true);
    elsif v_evidence->'human_hours_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'human_hours_30d';
      v_evidence:=v_evidence-'human_hours_30d';
    end if;

    -- Market evidence uses the latest verified buyer disposition per opportunity.
    with terminal as (
      select distinct on (opportunity_id)
        opportunity_id,outcome_type,occurred_at,outcome_key,source_sha256
      from ai_business_os_prod.external_outcomes
      where initiative_id=p_initiative_id
        and verification_status='VERIFIED'
        and opportunity_id is not null
        and outcome_type in (
          'BUYER_POSITIVE_REPLY','BUYER_NEGATIVE_REPLY','SIGNED_ENGAGEMENT',
          'COLLECTED_REVENUE','RECOVERED_FUNDS','EXPLICIT_NO_VALUE'
        )
        and occurred_at>=v_as_of-interval '90 days'
        and occurred_at<=v_as_of
      order by opportunity_id,occurred_at desc,outcome_key desc
    )
    select
      count(*),
      count(*) filter(where outcome_type in (
        'BUYER_POSITIVE_REPLY','SIGNED_ENGAGEMENT','COLLECTED_REVENUE','RECOVERED_FUNDS'
      )),
      max(occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),
        'sha256'
      ),'hex')
    into v_count,v_positive,v_latest,v_source_hash
    from terminal;

    if v_count>0 then
      v_avg:=v_positive::numeric/v_count::numeric;
      v_metrics:=jsonb_set(v_metrics,'{market_evidence_signal}',to_jsonb(v_avg),true);
      v_evidence:=jsonb_set(v_evidence,'{market_evidence_signal}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':market_evidence_signal',
        'source_sha256',v_source_hash,'observed_at',v_latest,
        'allocation_grade',(v_count>=3),
        'buyer_outcome_count',v_count,'positive_buyer_outcomes',v_positive,
        'basis','latest verified market disposition per opportunity'
      ),true);
      if v_count>=3 then
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=now()
        where initiative_id=p_initiative_id and metric_key='market_evidence_signal';
      else
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=null
        where initiative_id=p_initiative_id and metric_key='market_evidence_signal';
      end if;
    elsif v_evidence->'market_evidence_signal'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'market_evidence_signal';
      v_evidence:=v_evidence-'market_evidence_signal';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='market_evidence_signal';
    end if;

    -- Actual first-contact -> collected-cash duration.
    with collected as (
      select distinct on (e.opportunity_id)
        e.opportunity_id,e.occurred_at,e.outcome_key,e.source_sha256,o.first_contact_at
      from ai_business_os_prod.external_outcomes e
      join ai_business_os_prod.opportunities o on o.id=e.opportunity_id
      where e.initiative_id=p_initiative_id
        and e.verification_status='VERIFIED'
        and e.outcome_type='COLLECTED_REVENUE'
        and o.first_contact_at is not null
        and e.occurred_at>=o.first_contact_at
      order by e.opportunity_id,e.occurred_at asc,e.outcome_key
    )
    select
      count(*),
      avg(extract(epoch from (occurred_at-first_contact_at))/86400.0),
      max(occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),
        'sha256'
      ),'hex')
    into v_count,v_avg,v_latest,v_source_hash
    from collected;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{time_to_cash_days}',to_jsonb(v_avg),true);
      v_evidence:=jsonb_set(v_evidence,'{time_to_cash_days}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':time_to_cash_days',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'collected_opportunity_count',v_count,
        'basis','actual first-contact to first collected-revenue duration'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='time_to_cash_days';
    elsif v_evidence->'time_to_cash_days'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'time_to_cash_days';
      v_evidence:=v_evidence-'time_to_cash_days';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='time_to_cash_days';
    end if;

  elsif v_pool.scoring_model='CONSUMER_RND' then
    -- Real playtest outcomes drive the consumer/R&D playtest evidence metric.
    with playtest as (
      select outcome_key,outcome_type,outcome_value_numeric,occurred_at,source_sha256
      from ai_business_os_prod.external_outcomes
      where initiative_id=p_initiative_id
        and verification_status='VERIFIED'
        and outcome_type in (
          'PLAYTEST_POSITIVE_SIGNAL','PLAYTEST_NEGATIVE_SIGNAL','PLAYTEST_RETENTION_SIGNAL'
        )
        and occurred_at>=v_as_of-interval '30 days'
        and occurred_at<=v_as_of
    )
    select
      count(*),
      avg(case
        when outcome_type='PLAYTEST_POSITIVE_SIGNAL' then 1.0
        when outcome_type='PLAYTEST_NEGATIVE_SIGNAL' then 0.0
        else outcome_value_numeric
      end),
      max(occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),
        'sha256'
      ),'hex')
    into v_count,v_avg,v_latest,v_source_hash
    from playtest;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{playtest_evidence_signal}',to_jsonb(v_avg),true);
      v_evidence:=jsonb_set(v_evidence,'{playtest_evidence_signal}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':playtest_evidence_signal',
        'source_sha256',v_source_hash,'observed_at',v_latest,
        'allocation_grade',(v_count>=5),
        'playtest_outcome_count',v_count,
        'basis','verified real playtest outcomes; repository activity excluded'
      ),true);
      if v_count>=5 then
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=now()
        where initiative_id=p_initiative_id and metric_key='playtest_evidence_signal';
      else
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=null
        where initiative_id=p_initiative_id and metric_key='playtest_evidence_signal';
      end if;
    elsif v_evidence->'playtest_evidence_signal'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'playtest_evidence_signal';
      v_evidence:=v_evidence-'playtest_evidence_signal';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='playtest_evidence_signal';
    end if;
  end if;

  v_snapshot_key:='external-outcome:'||v_i.initiative_key||':'||p_trigger_outcome_key;
  v_hash:=encode(extensions.digest(
    v_snapshot_key||'|'||v_as_of::text||'|'||v_metrics::text||'|'||v_evidence::text,
    'sha256'
  ),'hex');

  insert into ai_business_os_prod.portfolio_snapshots(
    snapshot_key,initiative_id,as_of,metrics,evidence,snapshot_hash,created_by_agent_id
  ) values (
    v_snapshot_key,p_initiative_id,v_as_of,v_metrics,v_evidence,v_hash,p_actor_agent_id
  )
  on conflict(snapshot_key) do update set
    as_of=excluded.as_of,
    metrics=excluded.metrics,
    evidence=excluded.evidence,
    snapshot_hash=excluded.snapshot_hash,
    created_by_agent_id=excluded.created_by_agent_id,
    created_at=now()
  returning id into v_snapshot_id;

  perform * from ai_business_os_prod.refresh_portfolio_pool_ranking(
    case v_i.pool_key
      when 'b2b-cash-flow' then 'b2b-cash-flow-ranking-current'
      when 'consumer-rnd' then 'consumer-rnd-ranking-current'
      else v_i.pool_key||'-ranking-current'
    end,
    v_i.pool_key,
    p_actor_agent_id
  );

  return v_snapshot_id;
end;
$$;

create or replace function ai_business_os_prod.record_verified_external_outcome_v1(
  p_outcome_key text,
  p_initiative_key text,
  p_outcome_type text,
  p_occurred_at timestamptz,
  p_source_type text,
  p_source_ref text,
  p_source_sha256 text,
  p_created_by_agent_id text,
  p_verified_by_agent_id text,
  p_opportunity_id uuid default null,
  p_revenue_loop_key text default null,
  p_outcome_value_cents bigint default null,
  p_outcome_value_numeric numeric default null,
  p_unit text default null,
  p_metadata jsonb default '{}'::jsonb
) returns table(
  outcome_id uuid,
  portfolio_snapshot_id uuid,
  revenue_loop_outcome_id uuid
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_i ai_business_os_prod.portfolio_initiatives%rowtype;
  v_loop ai_business_os_prod.revenue_loops%rowtype;
  v_outcome_id uuid;
  v_snapshot_id uuid;
  v_revenue_outcome_id uuid;
begin
  if coalesce(trim(p_outcome_key),'')='' then raise exception 'outcome_key required'; end if;
  if p_source_sha256 !~ '^[0-9a-f]{64}$' then raise exception 'source SHA-256 required'; end if;
  if p_occurred_at>now() then raise exception 'outcome cannot occur in the future'; end if;

  select * into v_i
  from ai_business_os_prod.portfolio_initiatives
  where initiative_key=p_initiative_key and status='ACTIVE';
  if not found then raise exception 'unknown active initiative'; end if;

  if p_revenue_loop_key is not null then
    select * into v_loop
    from ai_business_os_prod.revenue_loops
    where loop_key=p_revenue_loop_key;
    if not found then raise exception 'unknown revenue loop'; end if;
    if v_loop.business_id is distinct from v_i.business_id
       or v_loop.product_id is distinct from v_i.product_id then
      raise exception 'revenue loop does not belong to initiative';
    end if;
  end if;

  insert into ai_business_os_prod.external_outcomes(
    outcome_key,initiative_id,business_id,product_id,revenue_loop_id,opportunity_id,
    outcome_type,outcome_value_cents,outcome_value_numeric,unit,occurred_at,
    source_type,source_ref,source_sha256,verification_status,
    created_by_agent_id,verified_by_agent_id,verified_at,metadata
  ) values (
    p_outcome_key,v_i.id,v_i.business_id,v_i.product_id,
    case when p_revenue_loop_key is null then null else v_loop.id end,
    p_opportunity_id,p_outcome_type,p_outcome_value_cents,p_outcome_value_numeric,p_unit,
    p_occurred_at,upper(p_source_type),p_source_ref,lower(p_source_sha256),'VERIFIED',
    p_created_by_agent_id,p_verified_by_agent_id,now(),coalesce(p_metadata,'{}'::jsonb)
  )
  returning id into v_outcome_id;

  if p_revenue_loop_key is not null then
    insert into ai_business_os_prod.revenue_loop_outcomes(
      loop_id,outcome_type,outcome_value_cents,outcome_value_numeric,unit,
      verified,source_ref,evidence_hash,occurred_at,metadata,external_outcome_id
    ) values (
      v_loop.id,p_outcome_type,p_outcome_value_cents,p_outcome_value_numeric,p_unit,
      true,p_source_ref,lower(p_source_sha256),p_occurred_at,
      coalesce(p_metadata,'{}'::jsonb)||jsonb_build_object('external_outcome_key',p_outcome_key),
      v_outcome_id
    )
    returning id into v_revenue_outcome_id;
  end if;

  v_snapshot_id:=ai_business_os_prod.refresh_external_outcome_snapshot_v1(
    v_i.id,p_outcome_key,p_verified_by_agent_id
  );

  return query select v_outcome_id,v_snapshot_id,v_revenue_outcome_id;
end;
$$;

create or replace function ai_business_os_prod.finalize_external_outcome_learning_v1(
  p_outcome_key text,
  p_actor_agent_id text
) returns table(
  memory_id uuid,
  memory_observation_id uuid,
  reward numeric
)
language plpgsql
security invoker
set search_path = ai_business_os_prod, extensions, pg_temp
as $$
declare
  v_o ai_business_os_prod.external_outcomes%rowtype;
  v_i ai_business_os_prod.portfolio_initiatives%rowtype;
  v_memory_id uuid;
  v_observation_id uuid;
  v_revenue_outcome_id uuid;
  v_learning_id uuid;
  v_total_attr numeric;
  v_reward numeric;
  v_content jsonb;
  v_content_hash text;
begin
  select * into v_o
  from ai_business_os_prod.external_outcomes
  where outcome_key=p_outcome_key
  for update;
  if not found then raise exception 'unknown external outcome'; end if;
  if v_o.verification_status<>'VERIFIED' then
    raise exception 'only verified external outcomes may become memory';
  end if;

  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_actor_agent_id
      and status='ACTIVE'
      and role_key in ('AUDITOR_REDTEAM','FINANCE_ANALYTICS')
  ) then
    raise exception 'learning finalizer must be Finance/Analytics or Auditor/Red Team';
  end if;

  if exists(
    select 1 from ai_business_os_prod.external_outcome_learning
    where outcome_id=v_o.id
  ) then
    raise exception 'external outcome already finalized into memory';
  end if;

  select * into v_i
  from ai_business_os_prod.portfolio_initiatives
  where id=v_o.initiative_id;

  if v_o.revenue_loop_id is not null then
    select id into v_revenue_outcome_id
    from ai_business_os_prod.revenue_loop_outcomes
    where external_outcome_id=v_o.id;

    if v_revenue_outcome_id is null then
      raise exception 'revenue-loop mirror missing';
    end if;

    select coalesce(sum(attribution_fraction),0)
    into v_total_attr
    from ai_business_os_prod.revenue_loop_attribution
    where outcome_id=v_revenue_outcome_id;

    if abs(v_total_attr-1.0)>0.000000001 then
      raise exception 'revenue-loop outcome must be fully attributed before learning';
    end if;
  end if;

  v_reward:=case v_o.outcome_type
    when 'COLLECTED_REVENUE' then 1.0
    when 'RECOVERED_FUNDS' then 1.0
    when 'SIGNED_ENGAGEMENT' then 0.8
    when 'BUYER_POSITIVE_REPLY' then 0.4
    when 'BUYER_NEGATIVE_REPLY' then -0.5
    when 'EXPLICIT_NO_VALUE' then -1.0
    when 'PLAYTEST_POSITIVE_SIGNAL' then 0.5
    when 'PLAYTEST_NEGATIVE_SIGNAL' then -0.5
    when 'PLAYTEST_RETENTION_SIGNAL' then greatest(-1.0,least(1.0,(coalesce(v_o.outcome_value_numeric,0.5)*2.0)-1.0))
    else 0.0
  end;

  v_content:=jsonb_build_object(
    'initiative_key',v_i.initiative_key,
    'pool_key',v_i.pool_key,
    'objective','learn only from independently verified external outcomes',
    'reward_policy_version','external-outcome-reward-v1'
  );
  v_content_hash:=encode(extensions.digest(v_content::text,'sha256'),'hex');

  insert into ai_business_os_prod.memory_items(
    memory_key,version,scope,objective,content,content_hash,status
  ) values (
    'verified-external-outcomes:'||v_i.initiative_key,
    'v1',
    v_i.initiative_key,
    'verified_external_outcomes',
    v_content,
    v_content_hash,
    'ACTIVE'
  )
  on conflict(memory_key,version,scope,objective) do nothing;

  select id into v_memory_id
  from ai_business_os_prod.memory_items
  where memory_key='verified-external-outcomes:'||v_i.initiative_key
    and version='v1'
    and scope=v_i.initiative_key
    and objective='verified_external_outcomes';

  insert into ai_business_os_prod.memory_observations(
    memory_id,event_id,reward,attribution_fraction,evidence_hash,
    verification_status,verified_at
  ) values (
    v_memory_id,
    'external-outcome:'||v_o.outcome_key,
    v_reward,
    1.0,
    v_o.source_sha256,
    'VERIFIED',
    now()
  )
  returning id into v_observation_id;

  if v_o.revenue_loop_id is not null then
    insert into ai_business_os_prod.revenue_loop_learning(
      loop_id,memory_id,memory_observation_id,learning_status,evidence_hash
    ) values (
      v_o.revenue_loop_id,v_memory_id,v_observation_id,'VERIFIED',v_o.source_sha256
    )
    returning id into v_learning_id;
  end if;

  insert into ai_business_os_prod.external_outcome_learning(
    outcome_id,memory_id,memory_observation_id,revenue_loop_learning_id,reward,evidence_hash
  ) values (
    v_o.id,v_memory_id,v_observation_id,v_learning_id,v_reward,v_o.source_sha256
  );

  return query select v_memory_id,v_observation_id,v_reward;
end;
$$;

revoke execute on function ai_business_os_prod.refresh_external_outcome_snapshot_v1(uuid,text,text)
from public,anon,authenticated;
revoke execute on function ai_business_os_prod.record_verified_external_outcome_v1(
  text,text,text,timestamptz,text,text,text,text,text,uuid,text,bigint,numeric,text,jsonb
) from public,anon,authenticated;
revoke execute on function ai_business_os_prod.finalize_external_outcome_learning_v1(text,text)
from public,anon,authenticated;

create or replace view ai_business_os_prod.external_outcome_status_v1
with (security_invoker=true)
as
select
  e.outcome_key,
  i.initiative_key,
  i.pool_key,
  b.slug as business_slug,
  e.outcome_type,
  e.outcome_value_cents,
  e.outcome_value_numeric,
  e.unit,
  e.occurred_at,
  e.source_type,
  e.verification_status,
  e.created_by_agent_id,
  e.verified_by_agent_id,
  (l.outcome_id is not null) as learned,
  l.reward
from ai_business_os_prod.external_outcomes e
join ai_business_os_prod.portfolio_initiatives i on i.id=e.initiative_id
left join ai_business_os_prod.businesses b on b.id=e.business_id
left join ai_business_os_prod.external_outcome_learning l on l.outcome_id=e.id
order by e.occurred_at desc,e.outcome_key;



-- MIGRATION 20260925144741 add_ai_business_os_opportunity_first_contact_v1

alter table ai_business_os_prod.opportunities
  add column if not exists first_contact_at timestamptz;

create index if not exists idx_opportunities_first_contact
  on ai_business_os_prod.opportunities(first_contact_at)
  where first_contact_at is not null;



-- MIGRATION 20260925145057 fix_ai_business_os_external_outcome_snapshot_ordering_v1
CREATE OR REPLACE FUNCTION ai_business_os_prod.refresh_external_outcome_snapshot_v1(p_initiative_id uuid, p_trigger_outcome_key text, p_actor_agent_id text)
 RETURNS uuid
 LANGUAGE plpgsql
 SET search_path TO 'ai_business_os_prod', 'extensions', 'pg_temp'
AS $function$
declare
  v_i ai_business_os_prod.portfolio_initiatives%rowtype;
  v_pool ai_business_os_prod.portfolio_pools%rowtype;
  v_prev ai_business_os_prod.portfolio_snapshots%rowtype;
  v_metrics jsonb := '{}'::jsonb;
  v_evidence jsonb := '{}'::jsonb;
  v_as_of timestamptz := clock_timestamp();
  v_count integer;
  v_positive integer;
  v_sum_cents numeric;
  v_sum_numeric numeric;
  v_avg numeric;
  v_latest timestamptz;
  v_hash text;
  v_source_hash text;
  v_snapshot_key text;
  v_snapshot_id uuid;
  v_signed_count integer;
  v_open_signed_cents numeric;
begin
  select * into v_i
  from ai_business_os_prod.portfolio_initiatives
  where id=p_initiative_id and status='ACTIVE';
  if not found then raise exception 'unknown active initiative'; end if;

  select * into v_pool
  from ai_business_os_prod.portfolio_pools
  where pool_key=v_i.pool_key and status='ACTIVE';
  if not found then raise exception 'initiative pool missing/inactive'; end if;

  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_actor_agent_id and status='ACTIVE'
  ) then
    raise exception 'snapshot actor must be active';
  end if;

  select * into v_prev
  from ai_business_os_prod.portfolio_snapshots
  where initiative_id=p_initiative_id
  order by as_of desc,created_at desc
  limit 1;

  if found then
    v_metrics:=coalesce(v_prev.metrics,'{}'::jsonb);
    v_evidence:=coalesce(v_prev.evidence,'{}'::jsonb);
  end if;

  if v_pool.scoring_model='B2B_CASH_FLOW' then
    -- Collected business revenue in the last 30 days.
    select count(*),coalesce(sum(outcome_value_cents),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='COLLECTED_REVENUE'
      and occurred_at >= v_as_of-interval '30 days'
      and occurred_at <= v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{cash_collected_30d}',to_jsonb(v_sum_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{cash_collected_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER',
        'source_ref','external-outcomes:'||v_i.initiative_key||':cash_collected_30d',
        'source_sha256',v_source_hash,
        'observed_at',v_latest,
        'allocation_grade',true,
        'sample_count',v_count,
        'basis','verified collected-revenue outcomes only'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='cash_collected_30d';
    elsif v_evidence->'cash_collected_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'cash_collected_30d';
      v_evidence:=v_evidence-'cash_collected_30d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='cash_collected_30d';
    end if;

    -- Verified delivery costs in the last 30 days.
    select count(*),coalesce(sum(outcome_value_cents),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='DELIVERY_COST_CENTS'
      and occurred_at >= v_as_of-interval '30 days'
      and occurred_at <= v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{cash_costs_30d}',to_jsonb(v_sum_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{cash_costs_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':cash_costs_30d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'sample_count',v_count,'basis','verified delivery-cost outcomes only'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='cash_costs_30d';
    elsif v_evidence->'cash_costs_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'cash_costs_30d';
      v_evidence:=v_evidence-'cash_costs_30d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='cash_costs_30d';
    end if;

    -- Verified AI/tool costs in the last 30 days.
    select count(*),coalesce(sum(outcome_value_cents),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='AI_COST_CENTS'
      and occurred_at >= v_as_of-interval '30 days'
      and occurred_at <= v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{ai_cost_30d}',to_jsonb(v_sum_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{ai_cost_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':ai_cost_30d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'sample_count',v_count,'basis','verified AI/tool-cost outcomes only'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='ai_cost_30d';
    elsif v_evidence->'ai_cost_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'ai_cost_30d';
      v_evidence:=v_evidence-'ai_cost_30d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='ai_cost_30d';
    end if;

    -- Signed-but-not-yet-collected engagements are contracted pipeline.
    select
      count(*),
      coalesce(sum(case when not exists(
        select 1
        from ai_business_os_prod.external_outcomes c
        where c.initiative_id=s.initiative_id
          and c.opportunity_id=s.opportunity_id
          and c.verification_status='VERIFIED'
          and c.outcome_type='COLLECTED_REVENUE'
          and c.occurred_at>=s.occurred_at
      ) then s.outcome_value_cents else 0 end),0),
      max(s.occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(s.outcome_key||':'||s.source_sha256,'|' order by s.outcome_key),''),
        'sha256'
      ),'hex')
    into v_signed_count,v_open_signed_cents,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes s
    where s.initiative_id=p_initiative_id
      and s.verification_status='VERIFIED'
      and s.outcome_type='SIGNED_ENGAGEMENT'
      and s.occurred_at>=v_as_of-interval '90 days'
      and s.occurred_at<=v_as_of;

    if v_signed_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{contracted_pipeline_value_90d}',to_jsonb(v_open_signed_cents),true);
      v_evidence:=jsonb_set(v_evidence,'{contracted_pipeline_value_90d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':contracted_pipeline_value_90d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'signed_engagement_count',v_signed_count,
        'basis','verified signed engagements less opportunities with verified collected revenue'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='contracted_pipeline_value_90d';
    elsif v_evidence->'contracted_pipeline_value_90d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'contracted_pipeline_value_90d';
      v_evidence:=v_evidence-'contracted_pipeline_value_90d';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='contracted_pipeline_value_90d';
    end if;

    -- Actual delivery hours are useful efficiency evidence.
    select count(*),coalesce(sum(outcome_value_numeric),0),max(occurred_at),
           encode(extensions.digest(coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),'sha256'),'hex')
    into v_count,v_sum_numeric,v_latest,v_source_hash
    from ai_business_os_prod.external_outcomes
    where initiative_id=p_initiative_id
      and verification_status='VERIFIED'
      and outcome_type='DELIVERY_HOURS'
      and occurred_at>=v_as_of-interval '30 days'
      and occurred_at<=v_as_of;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{human_hours_30d}',to_jsonb(v_sum_numeric),true);
      v_evidence:=jsonb_set(v_evidence,'{human_hours_30d}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':human_hours_30d',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'sample_count',v_count,'basis','verified delivery-hour outcomes'
      ),true);
    elsif v_evidence->'human_hours_30d'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'human_hours_30d';
      v_evidence:=v_evidence-'human_hours_30d';
    end if;

    -- Market evidence uses the latest verified buyer disposition per opportunity.
    with terminal as (
      select distinct on (opportunity_id)
        opportunity_id,outcome_type,occurred_at,outcome_key,source_sha256
      from ai_business_os_prod.external_outcomes
      where initiative_id=p_initiative_id
        and verification_status='VERIFIED'
        and opportunity_id is not null
        and outcome_type in (
          'BUYER_POSITIVE_REPLY','BUYER_NEGATIVE_REPLY','SIGNED_ENGAGEMENT',
          'COLLECTED_REVENUE','RECOVERED_FUNDS','EXPLICIT_NO_VALUE'
        )
        and occurred_at>=v_as_of-interval '90 days'
        and occurred_at<=v_as_of
      order by opportunity_id,occurred_at desc,outcome_key desc
    )
    select
      count(*),
      count(*) filter(where outcome_type in (
        'BUYER_POSITIVE_REPLY','SIGNED_ENGAGEMENT','COLLECTED_REVENUE','RECOVERED_FUNDS'
      )),
      max(occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),
        'sha256'
      ),'hex')
    into v_count,v_positive,v_latest,v_source_hash
    from terminal;

    if v_count>0 then
      v_avg:=v_positive::numeric/v_count::numeric;
      v_metrics:=jsonb_set(v_metrics,'{market_evidence_signal}',to_jsonb(v_avg),true);
      v_evidence:=jsonb_set(v_evidence,'{market_evidence_signal}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':market_evidence_signal',
        'source_sha256',v_source_hash,'observed_at',v_latest,
        'allocation_grade',(v_count>=3),
        'buyer_outcome_count',v_count,'positive_buyer_outcomes',v_positive,
        'basis','latest verified market disposition per opportunity'
      ),true);
      if v_count>=3 then
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=now()
        where initiative_id=p_initiative_id and metric_key='market_evidence_signal';
      else
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=null
        where initiative_id=p_initiative_id and metric_key='market_evidence_signal';
      end if;
    elsif v_evidence->'market_evidence_signal'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'market_evidence_signal';
      v_evidence:=v_evidence-'market_evidence_signal';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='market_evidence_signal';
    end if;

    -- Actual first-contact -> collected-cash duration.
    with collected as (
      select distinct on (e.opportunity_id)
        e.opportunity_id,e.occurred_at,e.outcome_key,e.source_sha256,o.first_contact_at
      from ai_business_os_prod.external_outcomes e
      join ai_business_os_prod.opportunities o on o.id=e.opportunity_id
      where e.initiative_id=p_initiative_id
        and e.verification_status='VERIFIED'
        and e.outcome_type='COLLECTED_REVENUE'
        and o.first_contact_at is not null
        and e.occurred_at>=o.first_contact_at
      order by e.opportunity_id,e.occurred_at asc,e.outcome_key
    )
    select
      count(*),
      avg(extract(epoch from (occurred_at-first_contact_at))/86400.0),
      max(occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),
        'sha256'
      ),'hex')
    into v_count,v_avg,v_latest,v_source_hash
    from collected;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{time_to_cash_days}',to_jsonb(v_avg),true);
      v_evidence:=jsonb_set(v_evidence,'{time_to_cash_days}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':time_to_cash_days',
        'source_sha256',v_source_hash,'observed_at',v_latest,'allocation_grade',true,
        'collected_opportunity_count',v_count,
        'basis','actual first-contact to first collected-revenue duration'
      ),true);
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=now()
      where initiative_id=p_initiative_id and metric_key='time_to_cash_days';
    elsif v_evidence->'time_to_cash_days'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'time_to_cash_days';
      v_evidence:=v_evidence-'time_to_cash_days';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='time_to_cash_days';
    end if;

  elsif v_pool.scoring_model='CONSUMER_RND' then
    -- Real playtest outcomes drive the consumer/R&D playtest evidence metric.
    with playtest as (
      select outcome_key,outcome_type,outcome_value_numeric,occurred_at,source_sha256
      from ai_business_os_prod.external_outcomes
      where initiative_id=p_initiative_id
        and verification_status='VERIFIED'
        and outcome_type in (
          'PLAYTEST_POSITIVE_SIGNAL','PLAYTEST_NEGATIVE_SIGNAL','PLAYTEST_RETENTION_SIGNAL'
        )
        and occurred_at>=v_as_of-interval '30 days'
        and occurred_at<=v_as_of
    )
    select
      count(*),
      avg(case
        when outcome_type='PLAYTEST_POSITIVE_SIGNAL' then 1.0
        when outcome_type='PLAYTEST_NEGATIVE_SIGNAL' then 0.0
        else outcome_value_numeric
      end),
      max(occurred_at),
      encode(extensions.digest(
        coalesce(string_agg(outcome_key||':'||source_sha256,'|' order by outcome_key),''),
        'sha256'
      ),'hex')
    into v_count,v_avg,v_latest,v_source_hash
    from playtest;

    if v_count>0 then
      v_metrics:=jsonb_set(v_metrics,'{playtest_evidence_signal}',to_jsonb(v_avg),true);
      v_evidence:=jsonb_set(v_evidence,'{playtest_evidence_signal}',jsonb_build_object(
        'source_type','VERIFIED_OUTCOME_LEDGER','source_ref','external-outcomes:'||v_i.initiative_key||':playtest_evidence_signal',
        'source_sha256',v_source_hash,'observed_at',v_latest,
        'allocation_grade',(v_count>=5),
        'playtest_outcome_count',v_count,
        'basis','verified real playtest outcomes; repository activity excluded'
      ),true);
      if v_count>=5 then
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=now()
        where initiative_id=p_initiative_id and metric_key='playtest_evidence_signal';
      else
        update ai_business_os_prod.portfolio_data_gaps
        set resolved_at=null
        where initiative_id=p_initiative_id and metric_key='playtest_evidence_signal';
      end if;
    elsif v_evidence->'playtest_evidence_signal'->>'source_type'='VERIFIED_OUTCOME_LEDGER' then
      v_metrics:=v_metrics-'playtest_evidence_signal';
      v_evidence:=v_evidence-'playtest_evidence_signal';
      update ai_business_os_prod.portfolio_data_gaps
      set resolved_at=null
      where initiative_id=p_initiative_id and metric_key='playtest_evidence_signal';
    end if;
  end if;

  v_snapshot_key:='external-outcome:'||v_i.initiative_key||':'||p_trigger_outcome_key;
  v_hash:=encode(extensions.digest(
    v_snapshot_key||'|'||v_as_of::text||'|'||v_metrics::text||'|'||v_evidence::text,
    'sha256'
  ),'hex');

  insert into ai_business_os_prod.portfolio_snapshots(
    snapshot_key,initiative_id,as_of,metrics,evidence,snapshot_hash,created_by_agent_id
  ) values (
    v_snapshot_key,p_initiative_id,v_as_of,v_metrics,v_evidence,v_hash,p_actor_agent_id
  )
  on conflict(snapshot_key) do update set
    as_of=excluded.as_of,
    metrics=excluded.metrics,
    evidence=excluded.evidence,
    snapshot_hash=excluded.snapshot_hash,
    created_by_agent_id=excluded.created_by_agent_id,
    created_at=now()
  returning id into v_snapshot_id;

  perform * from ai_business_os_prod.refresh_portfolio_pool_ranking(
    case v_i.pool_key
      when 'b2b-cash-flow' then 'b2b-cash-flow-ranking-current'
      when 'consumer-rnd' then 'consumer-rnd-ranking-current'
      else v_i.pool_key||'-ranking-current'
    end,
    v_i.pool_key,
    p_actor_agent_id
  );

  return v_snapshot_id;
end;
$function$



-- MIGRATION 20260925145220 integrate_ai_business_os_external_outcomes_command_center_v1
CREATE OR REPLACE FUNCTION ai_business_os_prod.record_verified_external_outcome_v1(p_outcome_key text, p_initiative_key text, p_outcome_type text, p_occurred_at timestamp with time zone, p_source_type text, p_source_ref text, p_source_sha256 text, p_created_by_agent_id text, p_verified_by_agent_id text, p_opportunity_id uuid DEFAULT NULL::uuid, p_revenue_loop_key text DEFAULT NULL::text, p_outcome_value_cents bigint DEFAULT NULL::bigint, p_outcome_value_numeric numeric DEFAULT NULL::numeric, p_unit text DEFAULT NULL::text, p_metadata jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(outcome_id uuid, portfolio_snapshot_id uuid, revenue_loop_outcome_id uuid)
 LANGUAGE plpgsql
 SET search_path TO 'ai_business_os_prod', 'extensions', 'pg_temp'
AS $function$
declare
  v_i ai_business_os_prod.portfolio_initiatives%rowtype;
  v_loop ai_business_os_prod.revenue_loops%rowtype;
  v_outcome_id uuid;
  v_snapshot_id uuid;
  v_revenue_outcome_id uuid;
begin
  if coalesce(trim(p_outcome_key),'')='' then raise exception 'outcome_key required'; end if;
  if p_source_sha256 !~ '^[0-9a-f]{64}$' then raise exception 'source SHA-256 required'; end if;
  if p_occurred_at>now() then raise exception 'outcome cannot occur in the future'; end if;

  select * into v_i
  from ai_business_os_prod.portfolio_initiatives
  where initiative_key=p_initiative_key and status='ACTIVE';
  if not found then raise exception 'unknown active initiative'; end if;

  if p_revenue_loop_key is not null then
    select * into v_loop
    from ai_business_os_prod.revenue_loops
    where loop_key=p_revenue_loop_key;
    if not found then raise exception 'unknown revenue loop'; end if;
    if v_loop.business_id is distinct from v_i.business_id
       or v_loop.product_id is distinct from v_i.product_id then
      raise exception 'revenue loop does not belong to initiative';
    end if;
  end if;

  insert into ai_business_os_prod.external_outcomes(
    outcome_key,initiative_id,business_id,product_id,revenue_loop_id,opportunity_id,
    outcome_type,outcome_value_cents,outcome_value_numeric,unit,occurred_at,
    source_type,source_ref,source_sha256,verification_status,
    created_by_agent_id,verified_by_agent_id,verified_at,metadata
  ) values (
    p_outcome_key,v_i.id,v_i.business_id,v_i.product_id,
    case when p_revenue_loop_key is null then null else v_loop.id end,
    p_opportunity_id,p_outcome_type,p_outcome_value_cents,p_outcome_value_numeric,p_unit,
    p_occurred_at,upper(p_source_type),p_source_ref,lower(p_source_sha256),'VERIFIED',
    p_created_by_agent_id,p_verified_by_agent_id,now(),coalesce(p_metadata,'{}'::jsonb)
  )
  returning id into v_outcome_id;

  if p_revenue_loop_key is not null then
    insert into ai_business_os_prod.revenue_loop_outcomes(
      loop_id,outcome_type,outcome_value_cents,outcome_value_numeric,unit,
      verified,source_ref,evidence_hash,occurred_at,metadata,external_outcome_id
    ) values (
      v_loop.id,p_outcome_type,p_outcome_value_cents,p_outcome_value_numeric,p_unit,
      true,p_source_ref,lower(p_source_sha256),p_occurred_at,
      coalesce(p_metadata,'{}'::jsonb)||jsonb_build_object('external_outcome_key',p_outcome_key),
      v_outcome_id
    )
    returning id into v_revenue_outcome_id;
  end if;

  v_snapshot_id:=ai_business_os_prod.refresh_external_outcome_snapshot_v1(
    v_i.id,p_outcome_key,p_verified_by_agent_id
  );

  if p_revenue_loop_key is null then
    perform * from ai_business_os_prod.finalize_external_outcome_learning_v1(
      p_outcome_key,p_verified_by_agent_id
    );
  end if;

  return query select v_outcome_id,v_snapshot_id,v_revenue_outcome_id;
end;
$function$;

create or replace view ai_business_os_prod.command_center_external_outcomes_v1
with (security_invoker=true)
as
select
  i.initiative_key,
  i.pool_key,
  i.name as initiative_name,
  count(e.id) filter(where e.verification_status='VERIFIED') as verified_outcomes,
  count(l.outcome_id) as learned_outcomes,
  count(e.id) filter(where e.outcome_type='BUYER_POSITIVE_REPLY' and e.verification_status='VERIFIED') as buyer_positive_replies,
  count(e.id) filter(where e.outcome_type in ('BUYER_NEGATIVE_REPLY','EXPLICIT_NO_VALUE') and e.verification_status='VERIFIED') as buyer_negative_or_no_value,
  coalesce(sum(e.outcome_value_cents) filter(
    where e.outcome_type='COLLECTED_REVENUE'
      and e.verification_status='VERIFIED'
      and e.occurred_at>=now()-interval '30 days'
  ),0) as collected_revenue_cents_30d,
  coalesce(sum(e.outcome_value_cents) filter(
    where e.outcome_type='RECOVERED_FUNDS'
      and e.verification_status='VERIFIED'
      and e.occurred_at>=now()-interval '90 days'
  ),0) as customer_recovered_funds_cents_90d,
  max(e.occurred_at) filter(where e.verification_status='VERIFIED') as latest_verified_outcome_at
from ai_business_os_prod.portfolio_initiatives i
left join ai_business_os_prod.external_outcomes e on e.initiative_id=i.id
left join ai_business_os_prod.external_outcome_learning l on l.outcome_id=e.id
where i.status='ACTIVE'
group by i.initiative_key,i.pool_key,i.name
order by i.pool_key,i.initiative_key;



-- MIGRATION 20260925145237 add_ai_business_os_external_outcomes_to_ceo_snapshot_v1
CREATE OR REPLACE FUNCTION ai_business_os_prod.refresh_command_center_snapshot(p_snapshot_key text)
 RETURNS TABLE(out_snapshot_key text, out_snapshot_hash text, out_generated_at timestamp with time zone)
 LANGUAGE plpgsql
 SET search_path TO 'ai_business_os_prod', 'extensions', 'pg_temp'
AS $function$
declare
  v_payload jsonb;
  v_hash text;
  v_generated timestamptz := now();
begin
  if coalesce(trim(p_snapshot_key),'')='' then
    raise exception 'snapshot key required';
  end if;

  select jsonb_build_object(
    'generated_at',v_generated,
    'system',(select to_jsonb(s) from ai_business_os_prod.command_center_system_v1 s),
    'portfolio',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from ai_business_os_prod.command_center_portfolio_v1 p),'[]'::jsonb),
    'agents',coalesce((select jsonb_agg(to_jsonb(a) order by a.display_name) from ai_business_os_prod.command_center_agents_v1 a),'[]'::jsonb),
    'revenue_loops',coalesce((select jsonb_agg(to_jsonb(r) order by r.business_name,r.loop_key) from ai_business_os_prod.command_center_revenue_loops_v1 r),'[]'::jsonb),
    'portfolio_allocator',(select allocator from ai_business_os_prod.command_center_portfolio_allocator_v2),
    'external_outcomes',coalesce((
      select jsonb_agg(to_jsonb(o) order by o.pool_key,o.initiative_key)
      from ai_business_os_prod.command_center_external_outcomes_v1 o
    ),'[]'::jsonb),
    'approval_queue',coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'request_key',q.request_key,
          'business_id',q.business_id,
          'title',q.title,
          'action_key',q.action_key,
          'status',q.status,
          'predicted_risk',q.predicted_risk,
          'expected_money_cents',q.expected_money_cents,
          'expires_at',q.expires_at,
          'intent_hash',q.intent_hash
        )
        order by q.expires_at
      )
      from ai_business_os_prod.approval_inbox q
      where q.status in ('PENDING','APPROVED')
    ),'[]'::jsonb)
  ) into v_payload;

  v_hash := encode(extensions.digest(v_payload::text,'sha256'),'hex');

  insert into ai_business_os_prod.command_center_snapshots(
    snapshot_key,snapshot_hash,payload,generated_at
  ) values (
    p_snapshot_key,v_hash,v_payload,v_generated
  )
  on conflict on constraint command_center_snapshots_snapshot_key_key
  do update set
    snapshot_hash=excluded.snapshot_hash,
    payload=excluded.payload,
    generated_at=excluded.generated_at;

  return query select p_snapshot_key,v_hash,v_generated;
end;
$function$;

-- MIGRATION 20260925151646 add_ai_business_os_persistent_worker_control_v1
alter table ai_business_os_prod.agent_goals
  add column if not exists claimed_by_worker_id text,
  add column if not exists lease_generation bigint not null default 0,
  add column if not exists lease_expires_at timestamptz,
  add column if not exists last_lease_heartbeat_at timestamptz,
  add column if not exists current_run_id uuid references ai_business_os_prod.agent_runs(id),
  add column if not exists last_error text;

alter table ai_business_os_prod.agent_runs
  add column if not exists worker_instance_id text,
  add column if not exists lease_generation bigint not null default 0,
  add column if not exists last_heartbeat_at timestamptz,
  add column if not exists outcome text,
  add column if not exists error text;

create unique index if not exists uq_ai_business_os_one_live_worker_lease_per_agent
  on ai_business_os_prod.agent_goals(agent_id)
  where status='ACTIVE' and lease_expires_at is not null;

create index if not exists idx_ai_business_os_worker_goal_queue
  on ai_business_os_prod.agent_goals(agent_id,status,priority desc,created_at)
  where status='PENDING';

create index if not exists idx_ai_business_os_worker_lease_expiry
  on ai_business_os_prod.agent_goals(lease_expires_at)
  where status='ACTIVE' and lease_expires_at is not null;

create or replace function ai_business_os_prod.agent_worker_requeue_expired_v1()
returns integer
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_catalog
as $$
declare
  v_count integer := 0;
begin
  update ai_business_os_prod.agent_runs r
     set ended_at = now(),
         status = 'LEASE_EXPIRED',
         outcome = 'LEASE_EXPIRED',
         error = 'lease expired before verification submission',
         metadata = coalesce(r.metadata,'{}'::jsonb)
           || jsonb_build_object('lease_recovered_at',now())
    from ai_business_os_prod.agent_goals g
   where g.current_run_id = r.id
     and g.status = 'ACTIVE'
     and g.lease_expires_at is not null
     and g.lease_expires_at <= now()
     and r.ended_at is null;

  update ai_business_os_prod.agent_goals
     set status = 'PENDING',
         claimed_by_worker_id = null,
         lease_expires_at = null,
         last_lease_heartbeat_at = null,
         current_run_id = null,
         last_error = 'lease expired; automatically requeued',
         updated_at = now()
   where status = 'ACTIVE'
     and lease_expires_at is not null
     and lease_expires_at <= now();

  get diagnostics v_count = row_count;
  return v_count;
end
$$;

create or replace function ai_business_os_prod.agent_worker_claim_v1(
  p_agent_id text,
  p_worker_instance_id text,
  p_goal_types jsonb,
  p_lease_seconds integer default 180
)
returns jsonb
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_catalog
as $$
declare
  v_goal ai_business_os_prod.agent_goals%rowtype;
  v_run_id uuid;
  v_generation bigint;
  v_role text;
begin
  if coalesce(trim(p_agent_id),'')='' or coalesce(trim(p_worker_instance_id),'')='' then
    raise exception 'agent_id and worker_instance_id are required';
  end if;
  if p_lease_seconds < 30 or p_lease_seconds > 900 then
    raise exception 'lease_seconds must be between 30 and 900';
  end if;
  if jsonb_typeof(p_goal_types) <> 'array' or jsonb_array_length(p_goal_types)=0 then
    raise exception 'goal_types must be a non-empty json array';
  end if;

  select role_key into v_role
    from ai_business_os_prod.agents
   where agent_id=p_agent_id and status='ACTIVE';
  if v_role is null then
    raise exception 'agent is not active';
  end if;

  perform ai_business_os_prod.agent_worker_requeue_expired_v1();

  if exists (
    select 1
      from ai_business_os_prod.agent_goals
     where agent_id=p_agent_id
       and status='ACTIVE'
       and lease_expires_at is not null
       and lease_expires_at > now()
  ) then
    return jsonb_build_object('goal',null,'reason','agent_busy');
  end if;

  select *
    into v_goal
    from ai_business_os_prod.agent_goals
   where agent_id=p_agent_id
     and status='PENDING'
     and goal_type in (select jsonb_array_elements_text(p_goal_types))
   order by priority desc, created_at asc
   for update skip locked
   limit 1;

  if v_goal.id is null then
    return jsonb_build_object('goal',null,'reason','no_eligible_goal');
  end if;

  v_generation := v_goal.lease_generation + 1;

  insert into ai_business_os_prod.agent_runs(
    agent_id,role,goal_id,status,started_at,worker_instance_id,lease_generation,last_heartbeat_at,metadata
  ) values (
    p_agent_id,v_role,v_goal.id::text,'RUNNING',now(),p_worker_instance_id,v_generation,now(),
    jsonb_build_object('worker_instance_id',p_worker_instance_id,'lease_generation',v_generation)
  )
  returning id into v_run_id;

  update ai_business_os_prod.agent_goals
     set status='ACTIVE',
         claimed_by_worker_id=p_worker_instance_id,
         lease_generation=v_generation,
         lease_expires_at=now()+make_interval(secs=>p_lease_seconds),
         last_lease_heartbeat_at=now(),
         current_run_id=v_run_id,
         last_error=null,
         updated_at=now()
   where id=v_goal.id and status='PENDING';

  insert into ai_business_os_prod.agent_heartbeats(agent_id,last_heartbeat_at,generation,state,updated_at)
  values (
    p_agent_id,now(),1,
    jsonb_build_object(
      'phase','RUNNING',
      'worker_instance_id',p_worker_instance_id,
      'goal_id',v_goal.id,
      'run_id',v_run_id,
      'lease_generation',v_generation
    ),
    now()
  )
  on conflict(agent_id) do update
    set generation = case
      when ai_business_os_prod.agent_heartbeats.state->>'worker_instance_id'
           is distinct from p_worker_instance_id
      then ai_business_os_prod.agent_heartbeats.generation + 1
      else ai_business_os_prod.agent_heartbeats.generation
    end,
    last_heartbeat_at=now(),
    state=excluded.state,
    updated_at=now();

  return jsonb_build_object(
    'goal',jsonb_build_object(
      'id',v_goal.id,
      'agent_id',v_goal.agent_id,
      'goal_type',v_goal.goal_type,
      'title',v_goal.title,
      'priority',v_goal.priority,
      'constraints',v_goal.constraints,
      'evidence_requirements',v_goal.evidence_requirements
    ),
    'run_id',v_run_id,
    'lease_generation',v_generation,
    'lease_expires_at',now()+make_interval(secs=>p_lease_seconds)
  );
end
$$;

create or replace function ai_business_os_prod.agent_worker_heartbeat_v1(
  p_agent_id text,
  p_worker_instance_id text,
  p_goal_id uuid,
  p_run_id uuid,
  p_lease_generation bigint,
  p_extend_seconds integer default 180
)
returns jsonb
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_catalog
as $$
declare
  v_goal ai_business_os_prod.agent_goals%rowtype;
  v_expires timestamptz;
begin
  if p_extend_seconds < 30 or p_extend_seconds > 900 then
    raise exception 'extend_seconds must be between 30 and 900';
  end if;

  select * into v_goal
    from ai_business_os_prod.agent_goals
   where id=p_goal_id
   for update;

  if v_goal.id is null then raise exception 'goal not found'; end if;
  if v_goal.agent_id <> p_agent_id
     or v_goal.status <> 'ACTIVE'
     or v_goal.claimed_by_worker_id <> p_worker_instance_id
     or v_goal.current_run_id <> p_run_id
     or v_goal.lease_generation <> p_lease_generation
     or v_goal.lease_expires_at is null
     or v_goal.lease_expires_at <= now()
  then
    raise exception 'stale or invalid worker lease';
  end if;

  v_expires := now()+make_interval(secs=>p_extend_seconds);

  update ai_business_os_prod.agent_goals
     set lease_expires_at=v_expires,
         last_lease_heartbeat_at=now(),
         updated_at=now()
   where id=p_goal_id;

  update ai_business_os_prod.agent_runs
     set last_heartbeat_at=now()
   where id=p_run_id and ended_at is null;

  update ai_business_os_prod.agent_heartbeats
     set last_heartbeat_at=now(),
         state=jsonb_build_object(
           'phase','RUNNING',
           'worker_instance_id',p_worker_instance_id,
           'goal_id',p_goal_id,
           'run_id',p_run_id,
           'lease_generation',p_lease_generation
         ),
         updated_at=now()
   where agent_id=p_agent_id;

  return jsonb_build_object('goal_id',p_goal_id,'run_id',p_run_id,'lease_generation',p_lease_generation,'lease_expires_at',v_expires);
end
$$;

create or replace function ai_business_os_prod.agent_worker_submit_v1(
  p_agent_id text,
  p_worker_instance_id text,
  p_goal_id uuid,
  p_run_id uuid,
  p_lease_generation bigint,
  p_output_hash text,
  p_evidence_refs jsonb,
  p_summary text
)
returns jsonb
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_catalog
as $$
declare
  v_goal ai_business_os_prod.agent_goals%rowtype;
begin
  if p_output_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'output_hash must be lowercase sha256';
  end if;
  if jsonb_typeof(p_evidence_refs) <> 'array' then
    raise exception 'evidence_refs must be an array';
  end if;

  select * into v_goal
    from ai_business_os_prod.agent_goals
   where id=p_goal_id
   for update;

  if v_goal.id is null then raise exception 'goal not found'; end if;
  if v_goal.agent_id <> p_agent_id
     or v_goal.status <> 'ACTIVE'
     or v_goal.claimed_by_worker_id <> p_worker_instance_id
     or v_goal.current_run_id <> p_run_id
     or v_goal.lease_generation <> p_lease_generation
     or v_goal.lease_expires_at is null
     or v_goal.lease_expires_at <= now()
  then
    raise exception 'stale or invalid worker lease';
  end if;

  update ai_business_os_prod.agent_runs
     set ended_at=now(),
         status='SUBMITTED_FOR_VERIFICATION',
         outcome='VERIFYING',
         output_hash=p_output_hash,
         metadata=coalesce(metadata,'{}'::jsonb)
           || jsonb_build_object('evidence_refs',p_evidence_refs,'summary',p_summary)
   where id=p_run_id and ended_at is null;

  update ai_business_os_prod.agent_goals
     set status='VERIFYING',
         claimed_by_worker_id=null,
         lease_expires_at=null,
         last_lease_heartbeat_at=null,
         current_run_id=null,
         last_error=null,
         updated_at=now()
   where id=p_goal_id;

  update ai_business_os_prod.agent_heartbeats
     set last_heartbeat_at=now(),
         state=jsonb_build_object('phase','IDLE','worker_instance_id',p_worker_instance_id,'last_goal_id',p_goal_id),
         updated_at=now()
   where agent_id=p_agent_id;

  return jsonb_build_object(
    'goal_id',p_goal_id,
    'run_id',p_run_id,
    'lease_generation',p_lease_generation,
    'status','VERIFYING',
    'output_hash',p_output_hash
  );
end
$$;

create or replace function ai_business_os_prod.agent_worker_fail_v1(
  p_agent_id text,
  p_worker_instance_id text,
  p_goal_id uuid,
  p_run_id uuid,
  p_lease_generation bigint,
  p_error text,
  p_requeue boolean default false
)
returns jsonb
language plpgsql
security invoker
set search_path = ai_business_os_prod, pg_catalog
as $$
declare
  v_goal ai_business_os_prod.agent_goals%rowtype;
  v_status text;
begin
  select * into v_goal
    from ai_business_os_prod.agent_goals
   where id=p_goal_id
   for update;

  if v_goal.id is null then raise exception 'goal not found'; end if;
  if v_goal.agent_id <> p_agent_id
     or v_goal.status <> 'ACTIVE'
     or v_goal.claimed_by_worker_id <> p_worker_instance_id
     or v_goal.current_run_id <> p_run_id
     or v_goal.lease_generation <> p_lease_generation
     or v_goal.lease_expires_at is null
     or v_goal.lease_expires_at <= now()
  then
    raise exception 'stale or invalid worker lease';
  end if;

  v_status := case when p_requeue then 'PENDING' else 'BLOCKED' end;

  update ai_business_os_prod.agent_runs
     set ended_at=now(),
         status=case when p_requeue then 'REQUEUED' else 'FAILED_BLOCKED' end,
         outcome=v_status,
         error=left(coalesce(p_error,'worker failure'),1000)
   where id=p_run_id and ended_at is null;

  update ai_business_os_prod.agent_goals
     set status=v_status,
         claimed_by_worker_id=null,
         lease_expires_at=null,
         last_lease_heartbeat_at=null,
         current_run_id=null,
         last_error=left(coalesce(p_error,'worker failure'),1000),
         updated_at=now()
   where id=p_goal_id;

  update ai_business_os_prod.agent_heartbeats
     set last_heartbeat_at=now(),
         state=jsonb_build_object(
           'phase',case when p_requeue then 'IDLE_REQUEUED' else 'BLOCKED' end,
           'worker_instance_id',p_worker_instance_id,
           'last_goal_id',p_goal_id
         ),
         updated_at=now()
   where agent_id=p_agent_id;

  return jsonb_build_object('goal_id',p_goal_id,'run_id',p_run_id,'lease_generation',p_lease_generation,'status',v_status);
end
$$;

revoke all on function ai_business_os_prod.agent_worker_requeue_expired_v1() from public, anon, authenticated;
revoke all on function ai_business_os_prod.agent_worker_claim_v1(text,text,jsonb,integer) from public, anon, authenticated;
revoke all on function ai_business_os_prod.agent_worker_heartbeat_v1(text,text,uuid,uuid,bigint,integer) from public, anon, authenticated;
revoke all on function ai_business_os_prod.agent_worker_submit_v1(text,text,uuid,uuid,bigint,text,jsonb,text) from public, anon, authenticated;
revoke all on function ai_business_os_prod.agent_worker_fail_v1(text,text,uuid,uuid,bigint,text,boolean) from public, anon, authenticated;

select cron.schedule(
  'aibos-agent-worker-stale-recovery-v1',
  '* * * * *',
  'select ai_business_os_prod.agent_worker_requeue_expired_v1();'
);

-- MIGRATION 20260925164427 add_ai_business_os_outreach_delivery_failure_outcome_v1

alter table ai_business_os_prod.external_outcomes
  drop constraint external_outcomes_outcome_type_check;

alter table ai_business_os_prod.external_outcomes
  add constraint external_outcomes_outcome_type_check
  check (outcome_type = any(array[
    'BUYER_POSITIVE_REPLY'::text,
    'BUYER_NEGATIVE_REPLY'::text,
    'OUTREACH_DELIVERY_FAILURE'::text,
    'SIGNED_ENGAGEMENT'::text,
    'COLLECTED_REVENUE'::text,
    'RECOVERED_FUNDS'::text,
    'DELIVERY_HOURS'::text,
    'DELIVERY_COST_CENTS'::text,
    'AI_COST_CENTS'::text,
    'EXPLICIT_NO_VALUE'::text,
    'PLAYTEST_POSITIVE_SIGNAL'::text,
    'PLAYTEST_NEGATIVE_SIGNAL'::text,
    'PLAYTEST_RETENTION_SIGNAL'::text
  ]));

CREATE OR REPLACE FUNCTION ai_business_os_prod.validate_external_outcome_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'ai_business_os_prod', 'pg_temp'
AS $function$
declare
  v_creator_role text;
  v_verifier_role text;
  v_initiative ai_business_os_prod.portfolio_initiatives%rowtype;
  v_loop ai_business_os_prod.revenue_loops%rowtype;
  v_opp ai_business_os_prod.opportunities%rowtype;
begin
  select * into v_initiative
  from ai_business_os_prod.portfolio_initiatives
  where id=new.initiative_id;

  if not found or v_initiative.status<>'ACTIVE' then
    raise exception 'external outcome requires an active initiative';
  end if;

  if new.business_id is distinct from v_initiative.business_id then
    raise exception 'external outcome business does not match initiative';
  end if;
  if new.product_id is distinct from v_initiative.product_id then
    raise exception 'external outcome product does not match initiative';
  end if;

  select role_key into v_creator_role
  from ai_business_os_prod.agents
  where agent_id=new.created_by_agent_id and status='ACTIVE';
  select role_key into v_verifier_role
  from ai_business_os_prod.agents
  where agent_id=new.verified_by_agent_id and status='ACTIVE';

  if v_creator_role is null or v_verifier_role is null then
    raise exception 'creator and verifier must be active agents';
  end if;
  if v_verifier_role not in ('AUDITOR_REDTEAM','FINANCE_ANALYTICS') then
    raise exception 'external outcome verifier must be Auditor/Red Team or Finance/Analytics';
  end if;

  if new.verification_status='VERIFIED' and new.verified_at < new.occurred_at then
    raise exception 'verified_at cannot predate occurred_at';
  end if;

  if new.revenue_loop_id is not null then
    select * into v_loop
    from ai_business_os_prod.revenue_loops
    where id=new.revenue_loop_id;
    if not found then raise exception 'unknown revenue loop'; end if;
    if v_loop.business_id is distinct from new.business_id then
      raise exception 'revenue loop business mismatch';
    end if;
    if v_loop.product_id is distinct from new.product_id then
      raise exception 'revenue loop product mismatch';
    end if;
  end if;

  if new.opportunity_id is not null then
    select * into v_opp
    from ai_business_os_prod.opportunities
    where id=new.opportunity_id;
    if not found then raise exception 'unknown opportunity'; end if;
    if v_opp.business_id is distinct from new.business_id then
      raise exception 'opportunity business mismatch';
    end if;
    if v_opp.product_id is distinct from new.product_id then
      raise exception 'opportunity product mismatch';
    end if;
  end if;

  if new.outcome_type in (
    'BUYER_POSITIVE_REPLY','BUYER_NEGATIVE_REPLY','OUTREACH_DELIVERY_FAILURE','SIGNED_ENGAGEMENT',
    'COLLECTED_REVENUE','RECOVERED_FUNDS','EXPLICIT_NO_VALUE'
  ) and new.opportunity_id is null then
    raise exception 'buyer/commercial outcome requires opportunity_id';
  end if;

  if new.outcome_type='SIGNED_ENGAGEMENT' then
    if new.outcome_value_cents is null then
      raise exception 'SIGNED_ENGAGEMENT requires outcome_value_cents';
    end if;
    if new.source_type not in ('SIGNED_CONTRACT','CRM') then
      raise exception 'SIGNED_ENGAGEMENT requires SIGNED_CONTRACT or CRM evidence';
    end if;
  elsif new.outcome_type='COLLECTED_REVENUE' then
    if new.outcome_value_cents is null then
      raise exception 'COLLECTED_REVENUE requires outcome_value_cents';
    end if;
    if new.source_type not in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER') then
      raise exception 'COLLECTED_REVENUE requires cash-ledger evidence';
    end if;
  elsif new.outcome_type='RECOVERED_FUNDS' then
    if new.outcome_value_cents is null then
      raise exception 'RECOVERED_FUNDS requires outcome_value_cents';
    end if;
    if new.source_type not in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER','CRM') then
      raise exception 'RECOVERED_FUNDS requires settlement/customer evidence';
    end if;
  elsif new.outcome_type='DELIVERY_COST_CENTS' then
    if new.outcome_value_cents is null then
      raise exception 'DELIVERY_COST_CENTS requires outcome_value_cents';
    end if;
    if new.source_type not in ('BANK','PAYMENT_PROCESSOR','GENERAL_LEDGER','INVOICE') then
      raise exception 'DELIVERY_COST_CENTS requires cost-ledger evidence';
    end if;
  elsif new.outcome_type='AI_COST_CENTS' then
    if new.outcome_value_cents is null then
      raise exception 'AI_COST_CENTS requires outcome_value_cents';
    end if;
    if new.source_type not in ('PAYMENT_PROCESSOR','GENERAL_LEDGER','INVOICE') then
      raise exception 'AI_COST_CENTS requires invoice/ledger evidence';
    end if;
  elsif new.outcome_type='DELIVERY_HOURS' then
    if new.outcome_value_numeric is null or coalesce(new.unit,'')<>'hours' then
      raise exception 'DELIVERY_HOURS requires numeric hours';
    end if;
    if new.source_type not in ('ANALYTICS','MANUAL_RECORD') then
      raise exception 'DELIVERY_HOURS requires analytics/manual evidence';
    end if;
  elsif new.outcome_type in ('BUYER_POSITIVE_REPLY','BUYER_NEGATIVE_REPLY','OUTREACH_DELIVERY_FAILURE','EXPLICIT_NO_VALUE') then
    if new.source_type not in ('CRM','EMAIL','ANALYTICS','MANUAL_RECORD') then
      raise exception 'buyer response outcome requires customer-response evidence';
    end if;
  elsif new.outcome_type in ('PLAYTEST_POSITIVE_SIGNAL','PLAYTEST_NEGATIVE_SIGNAL') then
    if new.source_type not in ('PLAYTEST_ANALYTICS','ANALYTICS','MANUAL_RECORD') then
      raise exception 'playtest outcome requires playtest/analytics evidence';
    end if;
  elsif new.outcome_type='PLAYTEST_RETENTION_SIGNAL' then
    if new.outcome_value_numeric is null
       or new.outcome_value_numeric < 0
       or new.outcome_value_numeric > 1 then
      raise exception 'PLAYTEST_RETENTION_SIGNAL requires numeric value in [0,1]';
    end if;
    if new.source_type not in ('PLAYTEST_ANALYTICS','ANALYTICS') then
      raise exception 'PLAYTEST_RETENTION_SIGNAL requires analytics evidence';
    end if;
  end if;

  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION ai_business_os_prod.finalize_external_outcome_learning_v1(p_outcome_key text, p_actor_agent_id text)
 RETURNS TABLE(memory_id uuid, memory_observation_id uuid, reward numeric)
 LANGUAGE plpgsql
 SET search_path TO 'ai_business_os_prod', 'extensions', 'pg_temp'
AS $function$
declare
  v_o ai_business_os_prod.external_outcomes%rowtype;
  v_i ai_business_os_prod.portfolio_initiatives%rowtype;
  v_memory_id uuid;
  v_observation_id uuid;
  v_revenue_outcome_id uuid;
  v_learning_id uuid;
  v_total_attr numeric;
  v_reward numeric;
  v_content jsonb;
  v_content_hash text;
begin
  select * into v_o
  from ai_business_os_prod.external_outcomes
  where outcome_key=p_outcome_key
  for update;
  if not found then raise exception 'unknown external outcome'; end if;
  if v_o.verification_status<>'VERIFIED' then
    raise exception 'only verified external outcomes may become memory';
  end if;

  if not exists(
    select 1 from ai_business_os_prod.agents
    where agent_id=p_actor_agent_id
      and status='ACTIVE'
      and role_key in ('AUDITOR_REDTEAM','FINANCE_ANALYTICS')
  ) then
    raise exception 'learning finalizer must be Finance/Analytics or Auditor/Red Team';
  end if;

  if exists(
    select 1 from ai_business_os_prod.external_outcome_learning
    where outcome_id=v_o.id
  ) then
    raise exception 'external outcome already finalized into memory';
  end if;

  select * into v_i
  from ai_business_os_prod.portfolio_initiatives
  where id=v_o.initiative_id;

  if v_o.revenue_loop_id is not null then
    select id into v_revenue_outcome_id
    from ai_business_os_prod.revenue_loop_outcomes
    where external_outcome_id=v_o.id;

    if v_revenue_outcome_id is null then
      raise exception 'revenue-loop mirror missing';
    end if;

    select coalesce(sum(attribution_fraction),0)
    into v_total_attr
    from ai_business_os_prod.revenue_loop_attribution
    where outcome_id=v_revenue_outcome_id;

    if abs(v_total_attr-1.0)>0.000000001 then
      raise exception 'revenue-loop outcome must be fully attributed before learning';
    end if;
  end if;

  v_reward:=case v_o.outcome_type
    when 'COLLECTED_REVENUE' then 1.0
    when 'RECOVERED_FUNDS' then 1.0
    when 'SIGNED_ENGAGEMENT' then 0.8
    when 'BUYER_POSITIVE_REPLY' then 0.4
    when 'BUYER_NEGATIVE_REPLY' then -0.5
    when 'OUTREACH_DELIVERY_FAILURE' then -0.2
    when 'EXPLICIT_NO_VALUE' then -1.0
    when 'PLAYTEST_POSITIVE_SIGNAL' then 0.5
    when 'PLAYTEST_NEGATIVE_SIGNAL' then -0.5
    when 'PLAYTEST_RETENTION_SIGNAL' then greatest(-1.0,least(1.0,(coalesce(v_o.outcome_value_numeric,0.5)*2.0)-1.0))
    else 0.0
  end;

  v_content:=jsonb_build_object(
    'initiative_key',v_i.initiative_key,
    'pool_key',v_i.pool_key,
    'objective','learn only from independently verified external outcomes',
    'reward_policy_version','external-outcome-reward-v1'
  );
  v_content_hash:=encode(extensions.digest(v_content::text,'sha256'),'hex');

  insert into ai_business_os_prod.memory_items(
    memory_key,version,scope,objective,content,content_hash,status
  ) values (
    'verified-external-outcomes:'||v_i.initiative_key,
    'v1',
    v_i.initiative_key,
    'verified_external_outcomes',
    v_content,
    v_content_hash,
    'ACTIVE'
  )
  on conflict(memory_key,version,scope,objective) do nothing;

  select id into v_memory_id
  from ai_business_os_prod.memory_items
  where memory_key='verified-external-outcomes:'||v_i.initiative_key
    and version='v1'
    and scope=v_i.initiative_key
    and objective='verified_external_outcomes';

  insert into ai_business_os_prod.memory_observations(
    memory_id,event_id,reward,attribution_fraction,evidence_hash,
    verification_status,verified_at
  ) values (
    v_memory_id,
    'external-outcome:'||v_o.outcome_key,
    v_reward,
    1.0,
    v_o.source_sha256,
    'VERIFIED',
    now()
  )
  returning id into v_observation_id;

  if v_o.revenue_loop_id is not null then
    insert into ai_business_os_prod.revenue_loop_learning(
      loop_id,memory_id,memory_observation_id,learning_status,evidence_hash
    ) values (
      v_o.revenue_loop_id,v_memory_id,v_observation_id,'VERIFIED',v_o.source_sha256
    )
    returning id into v_learning_id;
  end if;

  insert into ai_business_os_prod.external_outcome_learning(
    outcome_id,memory_id,memory_observation_id,revenue_loop_learning_id,reward,evidence_hash
  ) values (
    v_o.id,v_memory_id,v_observation_id,v_learning_id,v_reward,v_o.source_sha256
  );

  return query select v_memory_id,v_observation_id,v_reward;
end;
$function$;



-- MIGRATION 20260925164737 surface_ai_business_os_outreach_delivery_evidence_v1

create or replace view ai_business_os_prod.outreach_delivery_status_v1
with (security_invoker=true)
as
with latest as (
  select distinct on (loop_id,metric_key)
    loop_id,metric_key,metric_value,unit,observed_at,metadata
  from ai_business_os_prod.revenue_loop_measurements
  where metric_key in (
    'outreach_sent_count','delivered_outreach_count',
    'delivery_failure_count','external_reply_count'
  )
  order by loop_id,metric_key,observed_at desc,id desc
)
select
  l.loop_key,
  b.slug as business_slug,
  max(metric_value) filter(where metric_key='outreach_sent_count') as outreach_sent_count,
  max(metric_value) filter(where metric_key='delivered_outreach_count') as delivered_outreach_count,
  max(metric_value) filter(where metric_key='delivery_failure_count') as delivery_failure_count,
  max(metric_value) filter(where metric_key='external_reply_count') as external_reply_count,
  max(observed_at) as last_checked_at
from ai_business_os_prod.revenue_loops l
join ai_business_os_prod.businesses b on b.id=l.business_id
left join latest m on m.loop_id=l.id
group by l.loop_key,b.slug
order by b.slug,l.loop_key;

create or replace view ai_business_os_prod.command_center_external_outcomes_v1
with (security_invoker=true)
as
select
  i.initiative_key,
  i.pool_key,
  i.name as initiative_name,
  count(e.id) filter(where e.verification_status='VERIFIED') as verified_outcomes,
  count(l.outcome_id) as learned_outcomes,
  count(e.id) filter(
    where e.outcome_type='BUYER_POSITIVE_REPLY'
      and e.verification_status='VERIFIED'
  ) as buyer_positive_replies,
  count(e.id) filter(
    where e.outcome_type in ('BUYER_NEGATIVE_REPLY','EXPLICIT_NO_VALUE')
      and e.verification_status='VERIFIED'
  ) as buyer_negative_or_no_value,
  coalesce(sum(e.outcome_value_cents) filter(
    where e.outcome_type='COLLECTED_REVENUE'
      and e.verification_status='VERIFIED'
      and e.occurred_at>=now()-interval '30 days'
  ),0) as collected_revenue_cents_30d,
  coalesce(sum(e.outcome_value_cents) filter(
    where e.outcome_type='RECOVERED_FUNDS'
      and e.verification_status='VERIFIED'
      and e.occurred_at>=now()-interval '90 days'
  ),0) as customer_recovered_funds_cents_90d,
  max(e.occurred_at) filter(where e.verification_status='VERIFIED') as latest_verified_outcome_at,
  count(e.id) filter(
    where e.outcome_type='OUTREACH_DELIVERY_FAILURE'
      and e.verification_status='VERIFIED'
  ) as outreach_delivery_failures
from ai_business_os_prod.portfolio_initiatives i
left join ai_business_os_prod.external_outcomes e on e.initiative_id=i.id
left join ai_business_os_prod.external_outcome_learning l on l.outcome_id=e.id
where i.status='ACTIVE'
group by i.initiative_key,i.pool_key,i.name
order by i.pool_key,i.initiative_key;


