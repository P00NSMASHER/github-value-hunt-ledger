-- Exact live migration statement. Contains no customer/provider identifiers.

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

