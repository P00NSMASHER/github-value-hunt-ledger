-- Private opt-in pilot. Install alongside the accepted-inquiry schema.
-- Only successful new rows append; submission replays and rejected traffic do not.
CREATE TABLE IF NOT EXISTS retally_inquiry_feed (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  reference TEXT NOT NULL UNIQUE REFERENCES inquiries(reference) ON DELETE CASCADE
);
CREATE TRIGGER IF NOT EXISTS retally_feed_after_accept
AFTER INSERT ON inquiries
BEGIN
  INSERT INTO retally_inquiry_feed(reference) VALUES (NEW.reference);
END;
