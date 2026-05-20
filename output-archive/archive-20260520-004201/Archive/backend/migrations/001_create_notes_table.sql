-- ============================================================
-- Migration 001: Create notes table
-- MWU-NL-001 Backend — Note List Application
-- Schema matches planning document §1 exactly
-- ============================================================

BEGIN;

-- Create notes table with PostgreSQL best practices
CREATE TABLE IF NOT EXISTS notes (
    -- Use GENERATED ALWAYS AS IDENTITY instead of SERIAL (project standard)
    id          INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- BR-BACKEND-002: VARCHAR(500) with NOT NULL enforcement
    -- PHP only enforced NOT NULL at app layer; adding DB-level constraint
    content     VARCHAR(500) NOT NULL,
    
    -- Timezone-aware timestamp. MySQL TIMESTAMP → TIMESTAMPTZ conversion
    -- NOW() provides server-time default (was CURRENT_TIMESTAMP in MySQL)
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- BR-BACKEND-001 + BR-BACKEND-002: DB-level content validation
-- Belt-and-suspenders guard against empty content after trim
ALTER TABLE notes
    ADD CONSTRAINT chk_notes_content_not_empty
    CHECK (length(trim(content)) > 0);

-- BR-BACKEND-004: Index for efficient newest-first ordering
-- ORDER BY created_at DESC becomes a pure index scan with this
CREATE INDEX IF NOT EXISTS idx_notes_created_at_desc
    ON notes (created_at DESC);

COMMIT;

-- Post-migration verification queries (run manually):
-- SELECT COUNT(*) FROM notes;  -- should be 0 for fresh install
-- \d notes;                    -- verify column types and constraints
-- \di notes*;                  -- verify indexes created