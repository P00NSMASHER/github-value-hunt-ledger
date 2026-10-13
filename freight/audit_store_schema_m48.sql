            CREATE TABLE IF NOT EXISTS audit_events (
                buyer_id TEXT NOT NULL,
                business_unit TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                evidence_hash TEXT,
                previous_hash TEXT,
                event_hash TEXT NOT NULL,
                PRIMARY KEY (buyer_id,business_unit,sequence),
                UNIQUE (buyer_id,business_unit,event_hash)
            );

            CREATE TRIGGER IF NOT EXISTS audit_events_immutable_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(ABORT,'audit event is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_events_immutable_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(ABORT,'audit event is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_events_input_guard
            BEFORE INSERT ON audit_events
            BEGIN
                SELECT CASE WHEN
                    length(NEW.occurred_at)<>27 OR
                    NEW.occurred_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' OR
                    julianday(NEW.occurred_at) IS NULL OR
                    strftime('%Y-%m-%dT%H:%M:%S',NEW.occurred_at)<>substr(NEW.occurred_at,1,19)
                THEN RAISE(ABORT,'audit occurred_at must be canonical UTC') END;
                SELECT CASE WHEN
                    NEW.evidence_hash IS NOT NULL AND
                    (length(NEW.evidence_hash)<>64 OR NEW.evidence_hash GLOB '*[^0-9a-f]*')
                THEN RAISE(ABORT,'audit evidence_hash must be lowercase SHA-256') END;
                SELECT CASE WHEN NEW.sequence>1 AND NEW.occurred_at < (
                    SELECT occurred_at FROM audit_events
                    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
                      AND sequence=NEW.sequence-1
                ) THEN RAISE(ABORT,'audit occurred_at values must be nondecreasing') END;
            END;
