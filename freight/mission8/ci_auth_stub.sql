-- Minimal synthetic CI identity shape; not exported or production credentials.
CREATE TABLE users(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,email text NOT NULL,display_name text NOT NULL,role text NOT NULL DEFAULT 'user');
