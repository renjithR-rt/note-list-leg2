-- ============================================================
-- notes table — sole table owned by this module
-- ============================================================

CREATE TABLE notes (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content     VARCHAR(500)    NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_notes_content_nonempty CHECK (TRIM(content) <> '')
);

-- Supports BR-BACKEND-005: ORDER BY created_at DESC is the only list query.
-- A DESC index lets PostgreSQL satisfy that order without a sort step.
CREATE INDEX idx_notes_created_at_desc
    ON notes (created_at DESC);