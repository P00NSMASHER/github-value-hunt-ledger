-- Exact live migration statement. Contains no customer/provider identifiers.

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

