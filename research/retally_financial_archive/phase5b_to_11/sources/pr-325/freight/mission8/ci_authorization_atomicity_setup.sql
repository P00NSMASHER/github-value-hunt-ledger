-- M10 independent PostgreSQL authorization-race fixtures.
-- Ephemeral CI only, uses AUTHENTIC RecoveryOS Phase 1/2/3/M8 database schema.
-- This SQL models the ORIGINAL unlocked TypeScript check/insert and FIXED
-- TypeScript SELECT FOR UPDATE transaction. Not hosted HTTP parity.
CREATE TABLE IF NOT EXISTS m10_authorization_targets (
  label text PRIMARY KEY, instruction_id text NOT NULL
);
INSERT INTO m10_authorization_targets(label,instruction_id)
SELECT 'unsafe', instruction_id
FROM recovery_prepare_financial_instruction(
  'exact_t',(SELECT id FROM users WHERE email='exact.owner@example.invalid'),
  '{"schema":1,"tenant_id":"exact_t","payer_id":"SYNTHETIC","payee_id":"SYNTHETIC","currency":"USD","amount_cents":1000,"purpose":"Original race counterexample","finding_ids":["exact_finding"],"idempotency_key":"m10-unsafe-authorization"}'::jsonb,
  repeat('c',64));
INSERT INTO m10_authorization_targets(label,instruction_id)
SELECT 'locked', instruction_id
FROM recovery_prepare_financial_instruction(
  'exact_t',(SELECT id FROM users WHERE email='exact.owner@example.invalid'),
  '{"schema":1,"tenant_id":"exact_t","payer_id":"SYNTHETIC","payee_id":"SYNTHETIC","currency":"USD","amount_cents":2000,"purpose":"Fixed race acceptance","finding_ids":["exact_finding"],"idempotency_key":"m10-locked-authorization"}'::jsonb,
  repeat('d',64));

CREATE OR REPLACE FUNCTION m10_unsafe_authorize(p_label text,p_reference text)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE instr text; amount bigint; auth_id text; u bigint;
BEGIN
 SELECT instruction_id INTO instr FROM m10_authorization_targets WHERE label=p_label;
 SELECT id INTO auth_id FROM recovery_payment_authorizations
 WHERE tenant_id='exact_t' AND instruction_id=instr;
 IF FOUND THEN RETURN 'REPLAY:'||auth_id; END IF;
 -- Force callers to see the same empty pre-insert snapshot, exposing the race.
 PERFORM pg_sleep(0.9);
 SELECT amount_cents INTO amount FROM recovery_payment_instructions
 WHERE tenant_id='exact_t' AND id=instr;
 SELECT id INTO u FROM users WHERE email='exact.owner@example.invalid';
 auth_id='m10u_'||md5(p_reference);
 INSERT INTO recovery_payment_authorizations
 (id,tenant_id,instruction_id,authorized_cents,authorized_by,reason,authorization_hash)
 VALUES(auth_id,'exact_t',instr,amount,u,p_reference,md5(p_reference)||md5('different-'||p_reference));
 RETURN 'INSERT:'||auth_id;
END $$;

CREATE OR REPLACE FUNCTION m10_locked_authorize(p_label text,p_reference text)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE instr text; amount bigint; auth_id text; u bigint;
BEGIN
 SELECT instruction_id INTO instr FROM m10_authorization_targets WHERE label=p_label;
 SELECT amount_cents INTO amount FROM recovery_payment_instructions
 WHERE tenant_id='exact_t' AND id=instr FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'MISSING_INSTRUCTION'; END IF;
 SELECT id INTO auth_id FROM recovery_payment_authorizations
 WHERE tenant_id='exact_t' AND instruction_id=instr;
 IF FOUND THEN RETURN 'REPLAY:'||auth_id; END IF;
 SELECT id INTO u FROM users WHERE email='exact.owner@example.invalid';
 auth_id='m10s_'||md5(p_reference);
 INSERT INTO recovery_payment_authorizations
 (id,tenant_id,instruction_id,authorized_cents,authorized_by,reason,authorization_hash)
 VALUES(auth_id,'exact_t',instr,amount,u,p_reference,md5(p_reference)||md5('different-'||p_reference));
 RETURN 'INSERT:'||auth_id;
END $$;
