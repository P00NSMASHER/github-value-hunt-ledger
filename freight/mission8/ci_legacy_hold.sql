-- Synthetic historical financial history compatibility check. All changes rolled back.
BEGIN;
INSERT INTO users(email,display_name,role) VALUES('legacy.owner@example.invalid','Synthetic Legacy Owner','user');
INSERT INTO recovery_tenants(id,name,slug) VALUES('legacy_t','Synthetic Legacy Customer','legacy-only');
INSERT INTO recovery_tenant_memberships(tenant_id,user_id,role)
 SELECT 'legacy_t',id,'owner' FROM users WHERE email='legacy.owner@example.invalid';
INSERT INTO recovery_populations(id,tenant_id,buyer_id,business_unit,population_hash,status)
VALUES('legacy_pop','legacy_t','LEGACY','BU',repeat('a',64),'FROZEN');
INSERT INTO recovery_freight_records(id,tenant_id,population_id,buyer_id,business_unit,invoice_id,shipment_id,mode,currency,billed_total_cents,record_hash,payload)
VALUES('legacy_rec','legacy_t','legacy_pop','LEGACY','BU','INV','SHIP','LTL','USD',100000,repeat('1',64),'{"synthetic":true}');
INSERT INTO recovery_challenge_findings(id,tenant_id,population_id,economic_key,record_hash,incumbent_snapshot_hash,category,billed_cents,expected_cents,variance_cents,net_new_candidate_cents,attribution_state,confidence_ppm,blocker_codes,evidence,matched_incumbent_matter_ids,finding_hash)
VALUES('legacy_finding','legacy_t','legacy_pop','LEGACY_ECON',repeat('1',64),repeat('a',64),'TEST',100000,0,100000,100000,'CHALLENGER_ONLY',950000,'[]','["synthetic"]','[]',repeat('3',64));
INSERT INTO recovery_review_dispositions(id,tenant_id,finding_id,reviewer_user_id,decision,reason,disposition_hash)
 SELECT 'legacy_review','legacy_t','legacy_finding',id,'CONFIRM','Synthetic legacy review',repeat('4',64)
 FROM users WHERE email='legacy.owner@example.invalid';
INSERT INTO recovery_eligibility_certifications(tenant_id,economic_key,currency,canonical_finding_id,finding_hash,source_hash,authority_hash,buyer_attestation_hash,eligible_cents,certified_by)
 SELECT 'legacy_t','LEGACY_ECON','USD','legacy_finding',repeat('3',64),repeat('1',64),repeat('5',64),repeat('6',64),100000,id
 FROM users WHERE email='legacy.owner@example.invalid';
INSERT INTO recovery_payment_instructions(id,tenant_id,payer_id,payee_id,currency,amount_cents,purpose,finding_ids,idempotency_key,instruction_hash,created_by)
 SELECT 'legacy_instruction','legacy_t','PAYER','PAYEE','USD',100000,'Pre-migration synthetic commitment','["legacy_finding"]','old-legacy-0001',repeat('7',64),id
 FROM users WHERE email='legacy.owner@example.invalid';
DO $legacy$
DECLARE actor bigint; rejected boolean:=false; original_count bigint;
BEGIN
 SELECT id INTO actor FROM users WHERE email='legacy.owner@example.invalid';
 SELECT count(*) INTO original_count FROM recovery_payment_instructions WHERE tenant_id='legacy_t';
 BEGIN
   PERFORM recovery_prepare_financial_instruction('legacy_t',actor,
   '{"schema":1,"tenant_id":"legacy_t","payer_id":"PAYER","payee_id":"PAYEE","currency":"USD","amount_cents":100000,"purpose":"New attempted allocation","finding_ids":["legacy_finding"],"idempotency_key":"new-legacy-0001"}'::jsonb,repeat('8',64));
 EXCEPTION WHEN OTHERS THEN
   IF position('legacy commitment requires review' in SQLERRM)>0 THEN rejected:=true; ELSE RAISE; END IF;
 END;
 IF NOT rejected THEN RAISE EXCEPTION 'legacy commitment was not blocked'; END IF;
 IF (SELECT count(*) FROM recovery_payment_instructions WHERE tenant_id='legacy_t')<>original_count
 THEN RAISE EXCEPTION 'legacy immutable instruction altered'; END IF;
END $legacy$;
ROLLBACK;
