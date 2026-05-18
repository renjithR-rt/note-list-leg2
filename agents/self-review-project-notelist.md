## STEP 0 — Query Pipeline Lessons (MANDATORY, run before anything else)

Before reviewing generated code, query the shared lessons KB:

  mkb_query_semantic(
    query="codegen self-review failures",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )
  mkb_query_semantic(
    query="PHP FastAPI migration validation errors",
    project_id="PIPELINE-LESSONS",
    top_k=3,
    min_similarity=0.3
  )

For each result with similarity > 0.3:
  Read the lesson content
  Apply it to your current task
  If it flags a known failure pattern — actively check for it

---

# Self-Review Project Layer — Note-List-Leg1

## CRITICAL — Fail immediately
- require_permission() found in code -> FORBIDDEN (source has no auth)
- get_current_user() found in code -> FORBIDDEN (source has no auth)
- JWT tokens in code -> FORBIDDEN (source has no auth)
- Any authentication middleware -> FORBIDDEN (source has no auth)
- Empty note content saved -> must validate non-empty
- Content over 500 chars saved -> must enforce limit
- mysql_* functions used -> must be SQLAlchemy async

## HIGH — Conditional pass
- All endpoints are public (no auth decorators)
- Content validation on create and update
- Invalid ID returns 404, not 500
- All DB queries parameterised (no SQL injection)
- Proper error responses with meaningful messages

## Target Options
Backend: FastAPI + PostgreSQL
Frontend: React+Vite (If MWU is FRONTEND: check for .py files — must be ZERO)

## Traceability Header Required
# MWU: {mwu_id} | Module: notes | Rules: {br_ids} | Legacy: index.php

## Verdict
PASS: all CRITICAL pass
CONDITIONAL: 1-2 HIGH with remediation documented  
FAIL: any CRITICAL failure (especially auth hallucinations)

## Auth Constraint Enforcement
The source application has NO authentication system.
Any generated authentication code is a hallucination and must be rejected.
All endpoints must remain public and accessible without tokens.