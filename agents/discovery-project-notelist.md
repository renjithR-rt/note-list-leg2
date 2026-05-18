## STEP 0 — Query Pipeline Lessons (MANDATORY, run before anything else)

Before analyzing any source files, query the shared lessons KB:

  mkb_query_semantic(
    query="PHP migration common errors",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )
  mkb_query_semantic(
    query="codegen self-review failures",
    project_id="PIPELINE-LESSONS",
    top_k=3,
    min_similarity=0.3
  )

For each result with similarity > 0.3:
  Read the lesson content
  Apply it to your current task
  If it flags a known failure pattern — actively check for it

---

# Discovery Project Layer — Note-List-Leg1

## Project Context
Migrating simple note taking app from PHP 5.6 to Python 3.12 + FastAPI + PostgreSQL.
Source: index.php (mixed concerns — extract business logic only)
Legacy DB: MySQL 5.7 at localhost:3310
Target DB: PostgreSQL 16 at localhost:5436/notelist_modern

## Domain Context
Simple note CRUD app, no authentication, single table design
Extract scope for this MWU: business_logic_and_data_access

## Key Business Rules — Flag as HIGH Priority BRs with NEEDS_VALIDATION
1. Empty note check: notes cannot be saved if content is empty
2. Length limit: note content limited to 500 characters  
3. Invalid ID guard: operations on non-existent note IDs return proper errors
4. No auth: all endpoints are public (CRITICAL: never add authentication)

## CRITICAL Rules
- NO authentication: flag ANY_AUTH_PATTERN (must remain public)
- ALL note operations: flag VALIDATION_RULE (empty check, length check)
- ALL ID operations: flag ID_VALIDATION (must handle invalid IDs gracefully)

## DB Table Ownership
notes table -> MWU-NL-001 (complete CRUD operations)
No user tables, no session tables, no auth tables

## Shared Files to Reference
Database connection patterns in index.php
Basic validation patterns
Error handling approaches