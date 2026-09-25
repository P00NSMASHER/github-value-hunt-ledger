
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
