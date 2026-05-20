-- PostgreSQL DDL for notes table
-- MWU-NL2-001 Backend migration
-- BR-008: Upgrade from MySQL utf8 (3-byte) to PostgreSQL UTF-8 (4-byte)

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- Not SERIAL
    content     VARCHAR(500)                NOT NULL,              -- BR-002: 500 char limit
    created_at  TIMESTAMP WITH TIME ZONE    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- BR-009: DB-generated
);

-- BR-007: all list queries order by created_at DESC; index supports this hot path
CREATE INDEX IF NOT EXISTS idx_notes_created_at_desc
    ON notes (created_at DESC);