CREATE TABLE IF NOT EXISTS recovery_claims (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  reference TEXT NOT NULL,
  payer_id TEXT NOT NULL,
  payee_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  issued_at TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  fee_disqualified INTEGER NOT NULL DEFAULT 0 CHECK(fee_disqualified IN (0,1)),
  PRIMARY KEY (buyer_id,business_unit,claim_id),
  UNIQUE (buyer_id,business_unit,source_hash)
);
CREATE TABLE IF NOT EXISTS review_claims (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  flagged_at TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,claim_id),
  FOREIGN KEY (buyer_id,business_unit,claim_id)
    REFERENCES recovery_claims(buyer_id,business_unit,claim_id)
);
CREATE TABLE IF NOT EXISTS settlement_events (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  event_id TEXT NOT NULL,
  reference TEXT NOT NULL,
  payer_id TEXT NOT NULL,
  payee_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  booked_at TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,event_id),
  UNIQUE (buyer_id,business_unit,source_hash)
);
CREATE TABLE IF NOT EXISTS allocations (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  allocation_id TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  mode TEXT NOT NULL CHECK(mode IN ('AUTO','REVIEW')),
  fee_eligible_cents INTEGER NOT NULL CHECK(fee_eligible_cents BETWEEN 0 AND amount_cents),
  created_at TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,allocation_id),
  UNIQUE (buyer_id,business_unit,claim_id,event_id),
  FOREIGN KEY (buyer_id,business_unit,claim_id)
    REFERENCES recovery_claims(buyer_id,business_unit,claim_id),
  FOREIGN KEY (buyer_id,business_unit,event_id)
    REFERENCES settlement_events(buyer_id,business_unit,event_id)
);
CREATE TABLE IF NOT EXISTS counter_events (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  counter_id TEXT NOT NULL,
  original_event_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  observed_at TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,counter_id),
  UNIQUE (buyer_id,business_unit,source_hash),
  FOREIGN KEY (buyer_id,business_unit,original_event_id)
    REFERENCES settlement_events(buyer_id,business_unit,event_id)
);
CREATE TABLE IF NOT EXISTS reversal_edges (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  reversal_id TEXT NOT NULL,
  counter_id TEXT NOT NULL,
  allocation_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  created_at TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,reversal_id),
  UNIQUE (buyer_id,business_unit,counter_id,allocation_id),
  FOREIGN KEY (buyer_id,business_unit,counter_id)
    REFERENCES counter_events(buyer_id,business_unit,counter_id),
  FOREIGN KEY (buyer_id,business_unit,allocation_id)
    REFERENCES allocations(buyer_id,business_unit,allocation_id)
);
CREATE INDEX IF NOT EXISTS idx_claim_match ON recovery_claims(buyer_id,business_unit,reference,payer_id,payee_id,currency,issued_at);
CREATE INDEX IF NOT EXISTS idx_alloc_claim ON allocations(buyer_id,business_unit,claim_id);
CREATE INDEX IF NOT EXISTS idx_alloc_event ON allocations(buyer_id,business_unit,event_id);
CREATE INDEX IF NOT EXISTS idx_reverse_alloc ON reversal_edges(buyer_id,business_unit,allocation_id);

CREATE TRIGGER IF NOT EXISTS immutable_claim_u BEFORE UPDATE ON recovery_claims BEGIN SELECT RAISE(ABORT,'recovery claim is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_review_claim_u BEFORE UPDATE ON review_claims BEGIN SELECT RAISE(ABORT,'review claim is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_review_claim_d BEFORE DELETE ON review_claims BEGIN SELECT RAISE(ABORT,'review claim is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_claim_d BEFORE DELETE ON recovery_claims BEGIN SELECT RAISE(ABORT,'recovery claim is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_u BEFORE UPDATE ON settlement_events BEGIN SELECT RAISE(ABORT,'settlement event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_d BEFORE DELETE ON settlement_events BEGIN SELECT RAISE(ABORT,'settlement event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_alloc_u BEFORE UPDATE ON allocations BEGIN SELECT RAISE(ABORT,'allocation edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_alloc_d BEFORE DELETE ON allocations BEGIN SELECT RAISE(ABORT,'allocation edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_counter_u BEFORE UPDATE ON counter_events BEGIN SELECT RAISE(ABORT,'counter event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_counter_d BEFORE DELETE ON counter_events BEGIN SELECT RAISE(ABORT,'counter event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_reverse_u BEFORE UPDATE ON reversal_edges BEGIN SELECT RAISE(ABORT,'reversal edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_reverse_d BEFORE DELETE ON reversal_edges BEGIN SELECT RAISE(ABORT,'reversal edge is immutable'); END;

CREATE TRIGGER IF NOT EXISTS claim_input_guard BEFORE INSERT ON recovery_claims BEGIN
  SELECT CASE WHEN
    length(NEW.source_hash)<>64 OR NEW.source_hash GLOB '*[^0-9a-f]*'
  THEN RAISE(ABORT,'claim source_hash must be lowercase SHA-256') END;
  SELECT CASE WHEN
    length(NEW.currency)<>3 OR NEW.currency GLOB '*[^A-Z]*'
  THEN RAISE(ABORT,'claim currency must be three uppercase letters') END;
  SELECT CASE WHEN
    length(NEW.issued_at)<>27 OR NEW.issued_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
    OR julianday(NEW.issued_at) IS NULL
    OR strftime('%Y-%m-%dT%H:%M:%S',NEW.issued_at)<>substr(NEW.issued_at,1,19)
  THEN RAISE(ABORT,'claim issued_at must be canonical UTC') END;
END;
CREATE TRIGGER IF NOT EXISTS settlement_input_guard BEFORE INSERT ON settlement_events BEGIN
  SELECT CASE WHEN
    length(NEW.source_hash)<>64 OR NEW.source_hash GLOB '*[^0-9a-f]*'
  THEN RAISE(ABORT,'settlement source_hash must be lowercase SHA-256') END;
  SELECT CASE WHEN
    length(NEW.currency)<>3 OR NEW.currency GLOB '*[^A-Z]*'
  THEN RAISE(ABORT,'settlement currency must be three uppercase letters') END;
  SELECT CASE WHEN
    length(NEW.booked_at)<>27 OR NEW.booked_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
    OR julianday(NEW.booked_at) IS NULL
    OR strftime('%Y-%m-%dT%H:%M:%S',NEW.booked_at)<>substr(NEW.booked_at,1,19)
  THEN RAISE(ABORT,'settlement booked_at must be canonical UTC') END;
END;
CREATE TRIGGER IF NOT EXISTS counter_input_guard BEFORE INSERT ON counter_events BEGIN
  SELECT CASE WHEN
    length(NEW.source_hash)<>64 OR NEW.source_hash GLOB '*[^0-9a-f]*'
  THEN RAISE(ABORT,'counter source_hash must be lowercase SHA-256') END;
  SELECT CASE WHEN
    length(NEW.currency)<>3 OR NEW.currency GLOB '*[^A-Z]*'
  THEN RAISE(ABORT,'counter currency must be three uppercase letters') END;
  SELECT CASE WHEN
    length(NEW.observed_at)<>27 OR NEW.observed_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
    OR julianday(NEW.observed_at) IS NULL
    OR strftime('%Y-%m-%dT%H:%M:%S',NEW.observed_at)<>substr(NEW.observed_at,1,19)
  THEN RAISE(ABORT,'counter observed_at must be canonical UTC') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_input_guard BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    length(NEW.created_at)<>27 OR NEW.created_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
    OR julianday(NEW.created_at) IS NULL
    OR strftime('%Y-%m-%dT%H:%M:%S',NEW.created_at)<>substr(NEW.created_at,1,19)
  THEN RAISE(ABORT,'allocation created_at must be canonical UTC') END;
END;
CREATE TRIGGER IF NOT EXISTS review_claim_input_guard BEFORE INSERT ON review_claims BEGIN
  SELECT CASE WHEN
    length(NEW.flagged_at)<>27 OR NEW.flagged_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
    OR julianday(NEW.flagged_at) IS NULL
    OR strftime('%Y-%m-%dT%H:%M:%S',NEW.flagged_at)<>substr(NEW.flagged_at,1,19)
  THEN RAISE(ABORT,'review claim flagged_at must be canonical UTC') END;
  SELECT CASE WHEN NEW.flagged_at < (
    SELECT issued_at FROM recovery_claims
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND claim_id=NEW.claim_id
  ) THEN RAISE(ABORT,'review claim predates issued claim') END;
END;
CREATE TRIGGER IF NOT EXISTS reversal_input_guard BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    length(NEW.created_at)<>27 OR NEW.created_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
    OR julianday(NEW.created_at) IS NULL
    OR strftime('%Y-%m-%dT%H:%M:%S',NEW.created_at)<>substr(NEW.created_at,1,19)
  THEN RAISE(ABORT,'reversal created_at must be canonical UTC') END;
END;

CREATE TRIGGER IF NOT EXISTS counter_chronology BEFORE INSERT ON counter_events BEGIN
  SELECT CASE WHEN NEW.observed_at < (
    SELECT booked_at FROM settlement_events
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND event_id=NEW.original_event_id
  ) THEN RAISE(ABORT,'counter event predates original settlement') END;
  SELECT CASE WHEN NEW.currency <> (
    SELECT currency FROM settlement_events
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND event_id=NEW.original_event_id
  ) THEN RAISE(ABORT,'counter currency mismatch') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_chronology BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN NEW.created_at < (
    SELECT booked_at FROM settlement_events
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND event_id=NEW.event_id
  ) THEN RAISE(ABORT,'allocation predates settlement event') END;
  SELECT CASE WHEN (
    SELECT booked_at FROM settlement_events
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND event_id=NEW.event_id
  ) < (
    SELECT issued_at FROM recovery_claims
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND claim_id=NEW.claim_id
  ) THEN RAISE(ABORT,'settlement event predates issued claim') END;
END;
CREATE TRIGGER IF NOT EXISTS reversal_chronology BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN NEW.created_at < (
    SELECT observed_at FROM counter_events
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND counter_id=NEW.counter_id
  ) THEN RAISE(ABORT,'reversal predates counter event') END;
  SELECT CASE WHEN NEW.created_at < (
    SELECT created_at FROM allocations
    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
      AND allocation_id=NEW.allocation_id
  ) THEN RAISE(ABORT,'reversal predates allocation') END;
END;

CREATE TRIGGER IF NOT EXISTS allocation_event_capacity BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM allocations WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND event_id=NEW.event_id)+NEW.amount_cents
    > (SELECT amount_cents FROM settlement_events WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND event_id=NEW.event_id)
  THEN RAISE(ABORT,'settlement event capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_claim_capacity BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM allocations WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND claim_id=NEW.claim_id)
    - (SELECT COALESCE(SUM(r.amount_cents),0) FROM reversal_edges r JOIN allocations a
         ON a.buyer_id=r.buyer_id AND a.business_unit=r.business_unit AND a.allocation_id=r.allocation_id
         WHERE a.buyer_id=NEW.buyer_id AND a.business_unit=NEW.business_unit AND a.claim_id=NEW.claim_id)
    + NEW.amount_cents
    > (SELECT amount_cents FROM recovery_claims WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND claim_id=NEW.claim_id)
  THEN RAISE(ABORT,'recovery claim capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_counterparty BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT payer_id FROM recovery_claims WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND claim_id=NEW.claim_id)
      <> (SELECT payer_id FROM settlement_events WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND event_id=NEW.event_id)
    OR
    (SELECT payee_id FROM recovery_claims WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND claim_id=NEW.claim_id)
      <> (SELECT payee_id FROM settlement_events WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND event_id=NEW.event_id)
  THEN RAISE(ABORT,'allocation payer/payee mismatch') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_currency BEFORE INSERT ON allocations BEGIN
  SELECT CASE WHEN
    (SELECT currency FROM recovery_claims WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND claim_id=NEW.claim_id)
    <> (SELECT currency FROM settlement_events WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND event_id=NEW.event_id)
  THEN RAISE(ABORT,'allocation currency mismatch') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_auto_review_lock BEFORE INSERT ON allocations WHEN NEW.mode='AUTO' BEGIN
  SELECT CASE WHEN EXISTS(SELECT 1 FROM review_claims WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND claim_id=NEW.claim_id)
  THEN RAISE(ABORT,'review claim cannot auto allocate') END;
END;
CREATE TRIGGER IF NOT EXISTS allocation_review_flag AFTER INSERT ON allocations WHEN NEW.mode='REVIEW' BEGIN
  INSERT OR IGNORE INTO review_claims(buyer_id,business_unit,claim_id,flagged_at)
  VALUES(NEW.buyer_id,NEW.business_unit,NEW.claim_id,NEW.created_at);
END;
CREATE TRIGGER IF NOT EXISTS reversal_alloc_capacity BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND allocation_id=NEW.allocation_id)+NEW.amount_cents
    > (SELECT amount_cents FROM allocations WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND allocation_id=NEW.allocation_id)
  THEN RAISE(ABORT,'allocation reversal capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS reversal_counter_capacity BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    (SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND counter_id=NEW.counter_id)+NEW.amount_cents
    > (SELECT amount_cents FROM counter_events WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND counter_id=NEW.counter_id)
  THEN RAISE(ABORT,'counter event capacity exceeded') END;
END;
CREATE TRIGGER IF NOT EXISTS reversal_event_match BEFORE INSERT ON reversal_edges BEGIN
  SELECT CASE WHEN
    (SELECT original_event_id FROM counter_events WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND counter_id=NEW.counter_id)
    <> (SELECT event_id FROM allocations WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit AND allocation_id=NEW.allocation_id)
  THEN RAISE(ABORT,'counter event does not fund allocation') END;
END;
