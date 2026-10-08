-- Run ONLY against M7 isolated staging schema; rolls back all inserted test fixtures.
BEGIN;
INSERT INTO m7_tenants(id) VALUES ('ACCEPT_T1'),('ACCEPT_T2');
INSERT INTO m7_findings(tenant_id,id,economic_key,currency,candidate_cents,net_new_candidate_cents,attribution_state,confirmed,authority_verified,source_verified,buyer_eligibility_verified,blockers) VALUES
 ('ACCEPT_T1','USD1','U1','USD',100000,100000,'CHALLENGER_ONLY',true,true,true,true,'[]'),
 ('ACCEPT_T1','EUR1','E1','EUR',50000,50000,'CHALLENGER_ONLY',true,true,true,true,'[]'),
 ('ACCEPT_T1','INC1','I1','USD',100000,0,'INCUMBENT_KNOWN',true,true,true,true,'[]'),
 ('ACCEPT_T1','BLOCK1','B1','USD',100000,100000,'CHALLENGER_ONLY',true,true,true,true,'["DISPUTED"]'),
 ('ACCEPT_T2','OTHER','O1','USD',100000,100000,'CHALLENGER_ONLY',true,true,true,true,'[]');
DO $m7$
DECLARE
 a jsonb := '{"payerId":"BUYER","payeeId":"CARRIER","currency":"USD","amountCents":100000,"purpose":"Staging synthetic acceptance","allocations":[{"findingId":"USD1","amountCents":100000}]}'::jsonb;
 v uuid;
 replay boolean;
BEGIN
 SELECT instruction_id INTO v FROM m7_prepare_instruction('ACCEPT_T1','accept-key-0001',a);
 IF v IS NULL THEN RAISE EXCEPTION 'first allocation missing'; END IF;
 SELECT p.replayed INTO replay FROM m7_prepare_instruction('ACCEPT_T1','accept-key-0001',a) p;
 IF NOT replay THEN RAISE EXCEPTION 'exact replay not idempotent'; END IF;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-0002',a);
   RAISE EXCEPTION 'double allocation accepted';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='double allocation accepted' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-0003',jsonb_set(a,'{currency}','"EUR"'::jsonb));
   RAISE EXCEPTION 'mixed currency accepted';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='mixed currency accepted' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-0001',jsonb_set(a,'{amountCents}','50000'::jsonb));
   RAISE EXCEPTION 'conflicting replay accepted';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='conflicting replay accepted' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-0004',replace(a::text,'USD1','INC1')::jsonb);
   RAISE EXCEPTION 'incumbent known allocated';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='incumbent known allocated' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-0005',replace(a::text,'USD1','BLOCK1')::jsonb);
   RAISE EXCEPTION 'blocked finding allocated';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='blocked finding allocated' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-0006',replace(a::text,'USD1','OTHER')::jsonb);
   RAISE EXCEPTION 'cross tenant allocated';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='cross tenant allocated' THEN RAISE; END IF;
 END;
 BEGIN
   INSERT INTO m7_allocations(tenant_id,instruction_id,finding_id,economic_key,currency,amount_cents)
   VALUES('ACCEPT_T1',v,'USD1','U1','USD',1);
   RAISE EXCEPTION 'direct allocation overflow accepted';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='direct allocation overflow accepted' THEN RAISE; END IF;
 END;
 BEGIN
   UPDATE m7_findings SET net_new_candidate_cents=1 WHERE tenant_id='ACCEPT_T1' AND id='USD1';
   RAISE EXCEPTION 'economic entitlement mutation accepted';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='economic entitlement mutation accepted' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM m7_prepare_instruction('ACCEPT_T1','accept-key-jpy1',replace(a::text,'"USD"','"JPY"')::jsonb);
   RAISE EXCEPTION 'unsupported currency accepted';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM='unsupported currency accepted' THEN RAISE; END IF;
 END;
 IF (SELECT count(*) FROM m7_reconciled_cash_by_currency)<>0
   THEN RAISE EXCEPTION 'unverified cash was reported'; END IF;
 IF (SELECT sum(amount_cents) FROM m7_allocations WHERE tenant_id='ACCEPT_T1' AND finding_id='USD1')<>100000
   THEN RAISE EXCEPTION 'conservation failed'; END IF;
END $m7$;
ROLLBACK;
