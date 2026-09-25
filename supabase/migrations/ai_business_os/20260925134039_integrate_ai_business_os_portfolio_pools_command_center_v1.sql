-- Exact live migration statement. Contains no customer/provider identifiers.

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

