PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS carrier_execution_intents (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  execution_key TEXT NOT NULL,
  intent_hash TEXT NOT NULL,
  prepared_at TEXT NOT NULL,
  intent_json TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,execution_key),
  UNIQUE (buyer_id,business_unit,intent_hash)
);

CREATE TABLE IF NOT EXISTS carrier_execution_attempts (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  execution_key TEXT NOT NULL,
  intent_hash TEXT NOT NULL,
  started_at TEXT NOT NULL,
  attempt_hash TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,attempt_id),
  UNIQUE (buyer_id,business_unit,attempt_hash),
  FOREIGN KEY (buyer_id,business_unit,execution_key)
    REFERENCES carrier_execution_intents(buyer_id,business_unit,execution_key)
);

CREATE TABLE IF NOT EXISTS carrier_execution_send_slots (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  execution_key TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,execution_key),
  UNIQUE (buyer_id,business_unit,attempt_id),
  FOREIGN KEY (buyer_id,business_unit,attempt_id)
    REFERENCES carrier_execution_attempts(buyer_id,business_unit,attempt_id)
);

CREATE TABLE IF NOT EXISTS carrier_execution_receipts (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  receipt_hash TEXT NOT NULL,
  execution_key TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  intent_hash TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('FAILED','SUBMITTED','DELIVERED')),
  action_submitted INTEGER NOT NULL CHECK (action_submitted IN (0,1)),
  delivery_confirmed INTEGER NOT NULL CHECK (delivery_confirmed IN (0,1)),
  executed_at TEXT NOT NULL,
  receipt_json TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,receipt_hash),
  UNIQUE (buyer_id,business_unit,attempt_id),
  FOREIGN KEY (buyer_id,business_unit,attempt_id)
    REFERENCES carrier_execution_attempts(buyer_id,business_unit,attempt_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS one_successful_carrier_submission
ON carrier_execution_receipts(buyer_id,business_unit,execution_key)
WHERE action_submitted=1;

CREATE TABLE IF NOT EXISTS carrier_delivery_receipts (
  buyer_id TEXT NOT NULL,
  business_unit TEXT NOT NULL,
  delivery_receipt_hash TEXT NOT NULL,
  execution_key TEXT NOT NULL,
  submitted_receipt_hash TEXT NOT NULL,
  delivered_at TEXT NOT NULL,
  delivery_json TEXT NOT NULL,
  PRIMARY KEY (buyer_id,business_unit,delivery_receipt_hash),
  UNIQUE (buyer_id,business_unit,execution_key),
  UNIQUE (buyer_id,business_unit,submitted_receipt_hash),
  FOREIGN KEY (buyer_id,business_unit,submitted_receipt_hash)
    REFERENCES carrier_execution_receipts(buyer_id,business_unit,receipt_hash)
);

CREATE TRIGGER IF NOT EXISTS carrier_send_slot_attempt_match
BEFORE INSERT ON carrier_execution_send_slots
BEGIN
  SELECT CASE WHEN
    (SELECT execution_key FROM carrier_execution_attempts
      WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
        AND attempt_id=NEW.attempt_id) <> NEW.execution_key
  THEN RAISE(ABORT,'send slot attempt mismatch') END;
END;

CREATE TRIGGER IF NOT EXISTS carrier_receipt_attempt_match
BEFORE INSERT ON carrier_execution_receipts
BEGIN
  SELECT CASE WHEN
    (SELECT execution_key FROM carrier_execution_attempts
      WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
        AND attempt_id=NEW.attempt_id) <> NEW.execution_key
  THEN RAISE(ABORT,'execution receipt attempt mismatch') END;
  SELECT CASE WHEN
    (SELECT intent_hash FROM carrier_execution_attempts
      WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
        AND attempt_id=NEW.attempt_id) <> NEW.intent_hash
  THEN RAISE(ABORT,'execution receipt intent mismatch') END;
END;

CREATE TRIGGER IF NOT EXISTS carrier_delivery_submission_match
BEFORE INSERT ON carrier_delivery_receipts
BEGIN
  SELECT CASE WHEN
    COALESCE((SELECT action_submitted FROM carrier_execution_receipts
      WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
        AND receipt_hash=NEW.submitted_receipt_hash),0) <> 1
  THEN RAISE(ABORT,'delivery requires submitted execution receipt') END;
  SELECT CASE WHEN
    COALESCE((SELECT delivery_confirmed FROM carrier_execution_receipts
      WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
        AND receipt_hash=NEW.submitted_receipt_hash),1) <> 0
  THEN RAISE(ABORT,'delivery receipt already confirmed in execution receipt') END;
  SELECT CASE WHEN
    (SELECT execution_key FROM carrier_execution_receipts
      WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
        AND receipt_hash=NEW.submitted_receipt_hash) <> NEW.execution_key
  THEN RAISE(ABORT,'delivery execution key mismatch') END;
END;

CREATE TRIGGER IF NOT EXISTS immutable_carrier_intent_u
BEFORE UPDATE ON carrier_execution_intents BEGIN
  SELECT RAISE(ABORT,'carrier execution intent is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_intent_d
BEFORE DELETE ON carrier_execution_intents BEGIN
  SELECT RAISE(ABORT,'carrier execution intent is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_attempt_u
BEFORE UPDATE ON carrier_execution_attempts BEGIN
  SELECT RAISE(ABORT,'carrier execution attempt is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_attempt_d
BEFORE DELETE ON carrier_execution_attempts BEGIN
  SELECT RAISE(ABORT,'carrier execution attempt is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_receipt_u
BEFORE UPDATE ON carrier_execution_receipts BEGIN
  SELECT RAISE(ABORT,'carrier execution receipt is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_receipt_d
BEFORE DELETE ON carrier_execution_receipts BEGIN
  SELECT RAISE(ABORT,'carrier execution receipt is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_delivery_u
BEFORE UPDATE ON carrier_delivery_receipts BEGIN
  SELECT RAISE(ABORT,'carrier delivery receipt is immutable');
END;
CREATE TRIGGER IF NOT EXISTS immutable_carrier_delivery_d
BEFORE DELETE ON carrier_delivery_receipts BEGIN
  SELECT RAISE(ABORT,'carrier delivery receipt is immutable');
END;
