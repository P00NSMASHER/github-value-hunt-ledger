-- Synthetic dedicated 20-session race population; separate CI database.
INSERT INTO users(email,display_name,role) VALUES ('handler.owner@example.invalid','Synthetic Handler Owner','user');
INSERT INTO recovery_tenants(id,name,slug) VALUES('handler_t','Synthetic Race','handler-only');
INSERT INTO recovery_tenant_memberships(tenant_id,user_id,role)
 SELECT 'handler_t',id,'owner' FROM users WHERE email='handler.owner@example.invalid';
INSERT INTO recovery_populations(id,tenant_id,buyer_id,business_unit,population_hash,status)
 VALUES ('handler_pop','handler_t','HANDLER','BU',repeat('a',64),'FROZEN');
INSERT INTO recovery_freight_records(id,tenant_id,population_id,buyer_id,business_unit,invoice_id,shipment_id,mode,currency,billed_total_cents,record_hash,payload)
 VALUES('handler_record','handler_t','handler_pop','HANDLER','BU','INV','SHIP','LTL','USD',100000,repeat('1',64),'{"synthetic":true}');
INSERT INTO recovery_challenge_findings(id,tenant_id,population_id,economic_key,record_hash,incumbent_snapshot_hash,category,billed_cents,expected_cents,variance_cents,net_new_candidate_cents,attribution_state,confidence_ppm,blocker_codes,evidence,matched_incumbent_matter_ids,finding_hash)
 VALUES('handler_finding','handler_t','handler_pop','HANDLER_ECON','1'||repeat('1',63),repeat('a',64),'TEST',100000,0,100000,100000,'CHALLENGER_ONLY',950000,'[]','["synthetic"]','[]',repeat('3',64));
INSERT INTO recovery_review_dispositions(id,tenant_id,finding_id,reviewer_user_id,decision,reason,disposition_hash)
 SELECT 'handler_review','handler_t','handler_finding',id,'CONFIRM','Synthetic concurrent review',repeat('4',64) FROM users WHERE email='handler.owner@example.invalid';
INSERT INTO recovery_eligibility_certifications(tenant_id,economic_key,currency,canonical_finding_id,finding_hash,source_hash,authority_hash,buyer_attestation_hash,eligible_cents,certified_by)
 SELECT 'handler_t','HANDLER_ECON','USD','handler_finding',repeat('3',64),repeat('1',64),repeat('5',64),repeat('6',64),100000,id FROM users WHERE email='handler.owner@example.invalid';

-- CI-only user/session needed to test the real Floot cookie and membership validation.
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url text;
CREATE TABLE IF NOT EXISTS sessions (id text PRIMARY KEY, user_id bigint NOT NULL REFERENCES users(id),created_at timestamptz NOT NULL,last_accessed timestamptz NOT NULL,expires_at timestamptz NOT NULL);
INSERT INTO sessions(id,user_id,created_at,last_accessed,expires_at) SELECT 'm11-authenticated-session-local',id,now(),now(),now()+interval '4 hours' FROM users WHERE email='handler.owner@example.invalid';
