INSERT INTO m7_tenants(id) VALUES ('CI_RACE_TENANT');
INSERT INTO m7_findings(tenant_id,id,economic_key,currency,candidate_cents,net_new_candidate_cents,attribution_state,confirmed,authority_verified,source_verified,buyer_eligibility_verified,blockers)
 VALUES('CI_RACE_TENANT','RACE_FINDING','RACE_ECONOMIC_KEY','USD',100000,100000,'CHALLENGER_ONLY',true,true,true,true,'[]');
