-- Browser-intent COUNTS ONLY. Never store IPs, contact fields, URLs, user-agent strings or raw UTM values.
-- Events are self-reported browser interactions, NOT verified people, qualified leads, or revenue.
CREATE TABLE IF NOT EXISTS marketing_funnel_daily (
  day_utc TEXT NOT NULL CHECK (length(day_utc)=10),
  event TEXT NOT NULL CHECK (event IN ('freight_landing_viewed','freight_free_audit_cta_clicked','freight_audit_form_started','freight_audit_request_prepared')),
  channel TEXT NOT NULL CHECK (channel IN ('direct','organic_search','referral','campaign')),
  offer TEXT NOT NULL CHECK (offer IN ('general','founding','second_look')),
  interactions INTEGER NOT NULL DEFAULT 0 CHECK (interactions >= 0),
  PRIMARY KEY (day_utc, event, channel, offer)
);
