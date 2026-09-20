CREATE TABLE IF NOT EXISTS recovery_claims (
  claim_id TEXT PRIMARY KEY,
  reference TEXT NOT NULL,
  payer_id TEXT NOT NULL,
  payee_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  issued_at TEXT NOT NULL,
  source_hash TEXT NOT NULL UNIQUE,
  fee_disqualified INTEGER NOT NULL DEFAULT 0 CHECK(fee_disqualified IN (0,1))
);
CREATE TABLE IF NOT EXISTS review_claims (
  claim_id TEXT PRIMARY KEY REFERENCES recovery_claims(claim_id),
  flagged_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settlement_events (
  event_id TEXT PRIMARY KEY,
  reference TEXT NOT NULL,
  payer_id TEXT NOT NULL,
  payee_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  booked_at TEXT NOT NULL,
  source_hash TEXT NOT NULL UNIQUE,
  source_kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS allocations (
  allocation_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES recovery_claims(claim_id),
  event_id TEXT NOT NULL REFERENCES settlement_events(event_id),
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  mode TEXT NOT NULL CHECK(mode IN ('AUTO','REVIEW')),
  fee_eligible_cents INTEGER NOT NULL CHECK(fee_eligible_cents BETWEEN 0 AND amount_cents),
  created_at TEXT NOT NULL,
  UNIQUE(claim_id,event_id)
);
CREATE TABLE IF NOT EXISTS counter_events (
  counter_id TEXT PRIMARY KEY,
  original_event_id TEXT NOT NULL REFERENCES settlement_events(event_id),
  currency TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  observed_at TEXT NOT NULL,
  source_hash TEXT NOT NULL UNIQUE,
  source_kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reversal_edges (
  reversal_id TEXT PRIMARY KEY,
  counter_id TEXT NOT NULL REFERENCES counter_events(counter_id),
  allocation_id TEXT NOT NULL REFERENCES allocations(allocation_id),
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  created_at TEXT NOT NULL,
  UNIQUE(counter_id,allocation_id)
);
CREATE INDEX IF NOT EXISTS idx_claim_match ON recovery_claims(reference,payer_id,payee_id,currency,issued_at);
CREATE INDEX IF NOT EXISTS idx_alloc_claim ON allocations(claim_id);
CREATE INDEX IF NOT EXISTS idx_alloc_event ON allocations(event_id);
CREATE INDEX IF NOT EXISTS idx_reverse_alloc ON reversal_edges(allocation_id);

CREATE TRIGGER IF NOT EXISTS immutable_claim_u BEFORE UPDATE ON recovery_claims BEGIN SELECT RAISE(ABORT,'recovery claim is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_claim_d BEFORE DELETE ON recovery_claims BEGIN SELECT RAISE(ABORT,'recovery claim is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_u BEFORE UPDATE ON settlement_events BEGIN SELECT RAISE(ABORT,'settlement event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_d BEFORE DELETE ON settlement_events BEGIN SELECT RAISE(ABORT,'settlement event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_alloc_u BEFORE UPDATE ON allocations BEGIN SELECT RAISE(ABORT,'allocation edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_alloc_d BEFORE DELETE ON allocations BEGIN SELECT RAISE(ABORT,'allocation edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_counter_u BEFORE UPDATE ON counter_events BEGIN SELECT RAISE(ABORT,'counter event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_counter_d BEFORE DELETE ON counter_events BEGIN SELECT RAISE(ABORT,'counter event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_reverse_u BEFORE UPDATE ON reversal_edges BEGIN SELECT RAISE(ABORT,'reversal edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_reverse_d BEFORE DELETE ON reversal_edges BEGIN SELECT RAISE(ABORT,'reversal edge is immutable'); END;

CREATE TRIGGER IF NOT EXISTS allocation_event_capacity BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM allocations WHERE event_id=NEW.event_id)+NEW.amount_cents
    > (SELECT amount_cents FROM settlement_events WHERE event_id=NEW.event_id)
  THEN RAISE(ABORT,'settlement event capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_claim_capacity BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM allocations WHERE claim_id=NEW.claim_id)
    - (SELECT COALESCE(SUM(r.amount_cents),0) FROM reversal_edges r JOIN allocations a ON a.allocation_id=r.allocation_id WHERE a.claim_id=NEW.claim_id)
    + NEW.amount_cents
    > (SELECT amount_cents FROM recovery_claims WHERE claim_id=NEW.claim_id)
  THEN RAISE(ABORT,'recovery claim capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_currency BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT currency FROM recovery_claims WHERE claim_id=NEW.claim_id)
    <> (SELECT currency FROM settlement_events WHERE event_id=NEW.event_id)
  THEN RAISE(ABORT,'allocation currency mismatch') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_auto_review_lock BEFORE INSERT ON allocations WHEN NEW.mode='AUTO' BEGIN
  SELECT CASE WHEN EXISTS(SELECT 1 FROM review_claims WHERE claim_id=NEW.claim_id)
  THEN RAISE(ABORT,'review claim cannot auto allocate') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_review_flag AFTER INSERT ON allocations WHEN NEW.mode='REVIEW' BEGIN
  INSERT OR IGNORE INTO review_claims(claim_id,flagged_at) VALUES(NEW.claim_id,NEW.created_at);
END;
CREATE TRIGGER IF NOT EXISTS reversal_alloc_capacity BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges WHERE allocation_id=NEW.allocation_id)+NEW.amount_cents
    > (SELECT amount_cents FROM allocations WHERE allocation_id=NEW.allocation_id)
  THEN RAISE(ABORT,'allocation reversal capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS reversal_counter_capacity BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges WHERE counter_id=NEW.counter_id)+NEW.amount_cents
    > (SELECT amount_cents FROM counter_events WHERE counter_id=NEW.counter_id)
  THEN RAISE(ABORT,'counter event capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS reversal_event_match BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    (SELECT original_event_id FROM counter_events WHERE counter_id=NEW.counter_id)
    <> (SELECT event_id FROM allocations WHERE allocation_id=NEW.allocation_id)
  THEN RAISE(ABORT,'counter event does not fund allocation') END;
END;
