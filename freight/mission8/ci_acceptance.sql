-- Independent staging fixture, all effects rolled back. No real customer data.
BEGIN;
INSERT INTO users(email,display_name,role) VALUES('m8.qa1@example.invalid','Synthetic Owner A','user'),('m8.qa2@example.invalid','Synthetic Owner B','user');
INSERT INTO recovery_tenants(id,name,slug) VALUES('ci_a','Synthetic A','ci-a'),('ci_b','Synthetic B','ci-b');
INSERT INTO recovery_tenant_memberships(tenant_id,user_id,role)
SELECT 'ci_a',id,'owner' FROM users WHERE email='m8.qa1@example.invalid'
UNION ALL SELECT 'ci_b',id,'owner' FROM users WHERE email='m8.qa2@example.invalid';
INSERT INTO recovery_populations(id,tenant_id,buyer_id,business_unit,population_hash,status)
VALUES('ci_pop_a','ci_a','TEST_A','BU_A',repeat('a',64),'FROZEN'),('ci_pop_b','ci_b','TEST_B','BU_B',repeat('b',64),'FROZEN');
INSERT INTO recovery_freight_records(id,tenant_id,population_id,buyer_id,business_unit,invoice_id,shipment_id,mode,currency,billed_total_cents,record_hash,payload)
VALUES ('ci_rec_a','ci_a','ci_pop_a','TEST_A','BU_A','INV_A','SHIP_A','LTL','USD',120000,repeat('1',64),'{"synthetic":true}'::jsonb),
 ('ci_rec_b','ci_b','ci_pop_b','TEST_B','BU_B','INV_B','SHIP_B','LTL','EUR',100000,repeat('2',64),'{"synthetic":true}'::jsonb);
INSERT INTO recovery_challenge_findings(id,tenant_id,population_id,economic_key,record_hash,incumbent_snapshot_hash,category,billed_cents,expected_cents,variance_cents,net_new_candidate_cents,attribution_state,confidence_ppm,blocker_codes,evidence,matched_incumbent_matter_ids,finding_hash)
VALUES
('ci_f_usd','ci_a','ci_pop_a','CI_USD',repeat('1',64),repeat('a',64),'TEST',100000,0,100000,100000,'CHALLENGER_ONLY',950000,'[]','["synthetic"]','[]',repeat('3',64)),
('ci_f_inc','ci_a','ci_pop_a','CI_INC',repeat('1',64),repeat('a',64),'TEST',100000,0,100000,0,'INCUMBENT_KNOWN',950000,'[]','["synthetic"]','[]',repeat('4',64)),
('ci_f_eur','ci_b','ci_pop_b','CI_EUR',repeat('2',64),repeat('b',64),'TEST',100000,0,100000,100000,'CHALLENGER_ONLY',950000,'[]','["synthetic"]','[]',repeat('5',64));
INSERT INTO recovery_review_dispositions(id,tenant_id,finding_id,reviewer_user_id,decision,reason,disposition_hash)
SELECT 'r_usd','ci_a','ci_f_usd',id,'CONFIRM','Synthetic independent QA',repeat('6',64) FROM users WHERE email='m8.qa1@example.invalid'
UNION ALL SELECT 'r_inc','ci_a','ci_f_inc',id,'CONFIRM','Synthetic independent QA',repeat('7',64) FROM users WHERE email='m8.qa1@example.invalid'
UNION ALL SELECT 'r_eur','ci_b','ci_f_eur',id,'CONFIRM','Synthetic independent QA',repeat('8',64) FROM users WHERE email='m8.qa2@example.invalid';
INSERT INTO recovery_eligibility_certifications(tenant_id,economic_key,currency,canonical_finding_id,finding_hash,source_hash,authority_hash,buyer_attestation_hash,eligible_cents,certified_by)
SELECT 'ci_a','CI_USD','USD','ci_f_usd',repeat('3',64),repeat('1',64),repeat('9',64),repeat('a',64),100000,id
FROM users WHERE email='m8.qa1@example.invalid';
DO $m8$
DECLARE actor bigint; payload jsonb; payment text; was_replay boolean; rejected boolean;
BEGIN
 SELECT id INTO actor FROM users WHERE email='m8.qa1@example.invalid';
 payload:='{"schema":1,"tenant_id":"ci_a","payer_id":"PAYER","payee_id":"PAYEE","currency":"USD","amount_cents":100000,"purpose":"Synthetic QA case","finding_ids":["ci_f_usd"],"idempotency_key":"ci-alloc-0001"}'::jsonb;
 SELECT instruction_id INTO payment FROM recovery_prepare_financial_instruction('ci_a',actor,payload,repeat('b',64));
 IF payment IS NULL THEN RAISE EXCEPTION 'initial instruction missing'; END IF;
 SELECT replayed INTO was_replay FROM recovery_prepare_financial_instruction('ci_a',actor,payload,repeat('b',64));
 IF NOT was_replay THEN RAISE EXCEPTION 'idempotency replay not recognized'; END IF;

 rejected:=false;
 BEGIN
   PERFORM recovery_prepare_financial_instruction('ci_a',actor,jsonb_set(payload,'{idempotency_key}','"ci-alloc-0002"'::jsonb),repeat('c',64));
 EXCEPTION WHEN OTHERS THEN IF position('capacity exceeded' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF; END;
 IF NOT rejected THEN RAISE EXCEPTION 'second full claim accepted'; END IF;

 rejected:=false;
 BEGIN
   PERFORM recovery_prepare_financial_instruction('ci_a',actor,jsonb_set(jsonb_set(payload,'{currency}','"EUR"'::jsonb),'{idempotency_key}','"ci-alloc-0005"'::jsonb),repeat('d',64));
 EXCEPTION WHEN OTHERS THEN IF position('certified entitlement' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF; END;
 IF NOT rejected THEN RAISE EXCEPTION 'cross currency claim accepted'; END IF;

 rejected:=false;
 BEGIN
   PERFORM recovery_prepare_financial_instruction('ci_a',actor,jsonb_set(payload,'{amount_cents}','90000'::jsonb),repeat('b',64));
 EXCEPTION WHEN OTHERS THEN IF position('idempotency' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF; END;
 IF NOT rejected THEN RAISE EXCEPTION 'conflicting replay accepted'; END IF;

 rejected:=false;
 BEGIN
   PERFORM recovery_prepare_financial_instruction('ci_a',actor,jsonb_set(jsonb_set(payload,'{finding_ids}','["ci_f_inc"]'::jsonb),'{idempotency_key}','"ci-alloc-0003"'::jsonb),repeat('e',64));
 EXCEPTION WHEN OTHERS THEN IF position('finding not eligible' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF; END;
 IF NOT rejected THEN RAISE EXCEPTION 'incumbent-known accepted'; END IF;

 rejected:=false;
 BEGIN
   PERFORM recovery_prepare_financial_instruction('ci_a',actor,jsonb_set(jsonb_set(payload,'{finding_ids}','["ci_f_eur"]'::jsonb),'{idempotency_key}','"ci-alloc-0004"'::jsonb),repeat('f',64));
 EXCEPTION WHEN OTHERS THEN IF position('finding not eligible' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF; END;
 IF NOT rejected THEN RAISE EXCEPTION 'cross tenant accepted'; END IF;

 rejected:=false;
 BEGIN
   INSERT INTO recovery_value_allocations(id,tenant_id,instruction_id,finding_id,economic_key,currency,amount_cents)
    VALUES('unsafe','ci_a',payment,'ci_f_usd','CI_USD','USD',1);
 EXCEPTION WHEN OTHERS THEN IF position('economic capacity exceeded' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF; END;
 IF NOT rejected THEN RAISE EXCEPTION 'direct allocation bypass succeeded'; END IF;

 IF (SELECT coalesce(sum(amount_cents),0) FROM recovery_value_allocations WHERE tenant_id='ci_a')<>100000
 THEN RAISE EXCEPTION 'financial conservation violated'; END IF;
 IF (SELECT count(*) FROM recovery_m8_verified_cash_by_currency)<>0
 THEN RAISE EXCEPTION 'unverified cash represented as realized'; END IF;
END $m8$;
DO $chain$
DECLARE v record;
BEGIN
 SELECT * INTO v FROM recovery_verify_audit_chain('ci_a');
 IF v.total_events < 2 OR v.invalid_hashes<>0 OR v.broken_links<>0
 THEN RAISE EXCEPTION 'financial audit-chain acceptance failed'; END IF;
 IF (SELECT count(*) FROM recovery_audit_events WHERE tenant_id='ci_a'
 AND source_table IN ('recovery_eligibility_certifications','recovery_value_allocations'))<2
 THEN RAISE EXCEPTION 'financial certification/allocation missing from audit chain'; END IF;
END $chain$;
ROLLBACK;
