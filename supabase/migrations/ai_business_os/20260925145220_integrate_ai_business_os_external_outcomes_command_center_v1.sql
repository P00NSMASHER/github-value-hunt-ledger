-- Exact live migration statement. Contains no customer/provider identifiers.
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

