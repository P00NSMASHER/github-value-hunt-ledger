-- Synthetic dedicated 20-session race population; separate CI database.
INSERT INTO users(email,display_name,role) VALUES ('race.owner@example.invalid','Synthetic Race Owner','user');
INSERT INTO recovery_tenants(id,name,slug) VALUES('race_t','Synthetic Race','race-only');
INSERT INTO recovery_tenant_memberships(tenant_id,user_id,role)
 SELECT 'race_t',id,'owner' FROM users WHERE email='race.owner@example.invalid';
INSERT INTO recovery_populations(id,tenant_id,buyer_id,business_unit,population_hash,status)
 VALUES ('race_pop','race_t','RACE','BU',repeat('a',64),'FROZEN');
INSERT INTO recovery_freight_records(id,tenant_id,population_id,buyer_id,business_unit,invoice_id,shipment_id,mode,currency,billed_total_cents,record_hash,payload)
 VALUES('race_record','race_t','race_pop','RACE','BU','INV','SHIP','LTL','USD',100000,repeat('1',64),'{"synthetic":true}');
INSERT INTO recovery_challenge_findings(id,tenant_id,population_id,economic_key,record_hash,incumbent_snapshot_hash,category,billed_cents,expected_cents,variance_cents,net_new_candidate_cents,attribution_state,confidence_ppm,blocker_codes,evidence,matched_incumbent_matter_ids,finding_hash)
 VALUES('race_finding','race_t','race_pop','RACE_ECON','1'||repeat('1',63),repeat('a',64),'TEST',100000,0,100000,100000,'CHALLENGER_ONLY',950000,'[]','["synthetic"]','[]',repeat('3',64));
INSERT INTO recovery_review_dispositions(id,tenant_id,finding_id,reviewer_user_id,decision,reason,disposition_hash)
 SELECT 'race_review','race_t','race_finding',id,'CONFIRM','Synthetic concurrent review',repeat('4',64) FROM users WHERE email='race.owner@example.invalid';
INSERT INTO recovery_eligibility_certifications(tenant_id,economic_key,currency,canonical_finding_id,finding_hash,source_hash,authority_hash,buyer_attestation_hash,eligible_cents,certified_by)
 SELECT 'race_t','RACE_ECON','USD','race_finding',repeat('3',64),repeat('1',64),repeat('5',64),repeat('6',64),100000,id FROM users WHERE email='race.owner@example.invalid';
