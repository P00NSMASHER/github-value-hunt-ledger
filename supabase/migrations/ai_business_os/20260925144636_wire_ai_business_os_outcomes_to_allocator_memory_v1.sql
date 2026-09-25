-- Exact live migration statement. Contains no customer/provider identifiers.

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

