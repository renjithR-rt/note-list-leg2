## STEP 0 — Query Pipeline Lessons (MANDATORY, run before anything else)

Before extracting business rules, query the shared lessons KB:

  mkb_query_semantic(
    query="BR extraction comprehension gaps",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )

For each result with similarity > 0.3:
  Read the lesson content
  Apply it to your current task
  If it flags a known failure pattern — actively check for it

---

# Comprehension Project Layer — Note-List-Leg1

## BR ID Convention
BR-NL-001-XXX (note CRUD operations)

## Domain Context
Simple note CRUD, no auth, no categories, no status, no users
Single table: notes (id, content, created_at, updated_at)

## Priority BRs

### Note Management (MWU-NL-001)
- Creation: content required (non-empty), max 500 chars
- Read: simple ID-based retrieval, list all notes
- Update: content validation same as creation
- Delete: simple ID-based deletion
- Validation: empty content rejected, 500 char limit enforced
- Error handling: invalid ID returns 404, not server error

## PHP Pattern Translation
- mysql_query() -> SQLAlchemy async session.execute()
- mysql_insert_id() -> result.inserted_primary_key[0]
- mysql_fetch_array() -> result.fetchall()
- mysql_escape_string() -> parameterized queries

## CRITICAL CONSTRAINT
Rule: never add auth that isn't in the source (HARD CONSTRAINT)
No require_permission(), no get_current_user(), no JWT, no sessions

## Business Rule Categories
- VALIDATION: content empty check, length limit
- ID_VALIDATION: invalid ID handling
- CRUD: basic create/read/update/delete operations

## MKB Storage
project_id: NOTE-LIST-LEG1, namespace: business-rules