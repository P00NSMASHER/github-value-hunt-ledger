-- Exact live migration statement. Contains no customer/provider identifiers.

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

