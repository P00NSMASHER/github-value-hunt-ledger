-- Exact live migration statement. Contains no customer/provider identifiers.

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

