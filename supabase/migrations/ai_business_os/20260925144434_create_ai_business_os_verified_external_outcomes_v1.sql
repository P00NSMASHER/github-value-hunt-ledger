-- Exact live migration statement. Contains no customer/provider identifiers.

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

