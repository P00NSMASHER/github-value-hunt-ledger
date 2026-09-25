-- Exact live migration statement. Contains no customer/provider identifiers.

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

