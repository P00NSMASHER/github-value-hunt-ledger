-- RETALLY restricted inquiry database. Run against D1 before backend activation.
-- Only approved RETALLY operators may access the D1 database; never expose read APIs.
CREATE TABLE IF NOT EXISTS inquiries (
 reference TEXT PRIMARY KEY,
 idempotency_key TEXT NOT NULL UNIQUE,
 fingerprint TEXT NOT NULL,
 full_name TEXT NOT NULL,
 work_email TEXT NOT NULL,
 company_name TEXT NOT NULL,
 annual_spend TEXT NOT NULL,
 modes_json TEXT NOT NULL,
 details_json TEXT NOT NULL,
 accepted_at INTEGER NOT NULL,
 notification_status TEXT NOT NULL DEFAULT 'pending' CHECK (notification_status IN ('pending','provider_accepted','delivery_verified')),
 notified_at INTEGER
);
CREATE INDEX IF NOT EXISTS inquiries_accepted_at_idx ON inquiries(accepted_at);
CREATE INDEX IF NOT EXISTS inquiries_notification_status_idx ON inquiries(notification_status,accepted_at);
CREATE TABLE IF NOT EXISTS inquiry_limits (
 bucket TEXT PRIMARY KEY,
 hits INTEGER NOT NULL,
 expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS inquiry_limits_expiration_idx ON inquiry_limits(expires_at);
