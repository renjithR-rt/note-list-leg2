-- ============================================================
-- notes table
-- Owns: all note records for the application.
-- BR-009: created_at is DB-managed; the application never
--         supplies this value on INSERT.
-- BR-008: PostgreSQL's native UTF-8 is 4-byte; emoji and
--         supplementary Unicode are supported automatically.
-- BR-002: content is VARCHAR(500); DB enforces the cap as a
--         second layer after the app-layer Pydantic check.
-- ============================================================

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content     VARCHAR(500)    NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- BR-001 + BR-003: content cannot be empty after trimming
    CONSTRAINT notes_content_not_empty CHECK (LENGTH(TRIM(content)) > 0)
);

-- Index: supports BR-007 (always return notes newest-first).
-- Without this index every GET /api/notes performs a full sequential
-- scan + sort; the index makes ORDER BY created_at DESC a pure index
-- scan on any Postgres query planner version.
CREATE INDEX IF NOT EXISTS idx_notes_created_at_desc
    ON notes (created_at DESC);