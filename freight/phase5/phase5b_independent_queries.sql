-- PHASE 5B. READ ONLY. Execute through Floot query_database on QA.
-- NEVER run mutations against production.
-- First verify independent source:
SELECT system_identifier::text AS qa_system_identifier FROM pg_control_system();

-- Committed synthetic test events in real QA handler tables:
SELECT tenant_id,instruction_id,count(*)::int AS events,
 count(DISTINCT event_hash)::int AS hashes,
 count(DISTINCT provider_reference)::int AS references,
 string_agg(state,' -> ' ORDER BY occurred_at) AS state_sequence
FROM public.recovery_payment_events
WHERE tenant_id LIKE 'SIM-P5B-HANDLER-%'
GROUP BY tenant_id,instruction_id ORDER BY tenant_id,instruction_id;

-- Actual PostgreSQL stored-function concurrency results (separate test surface):
SELECT tenant_id,instruction_id,count(*)::int AS events,
 min(event_id) AS first_event_id,max(event_seq) AS max_sequence,
 count(DISTINCT provider_reference)::int AS refs
FROM phase5_qa.events
WHERE tenant_id LIKE 'SIM-P5B-%'
GROUP BY tenant_id,instruction_id ORDER BY tenant_id,instruction_id;

-- Confirm two critical unique indexes protect events as database constraints:
SELECT indexname,indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='recovery_payment_events'
ORDER BY indexname;

-- Production identity must be read separately with production READ ONLY
-- query_database, never using this or other QA code to mutate production.
