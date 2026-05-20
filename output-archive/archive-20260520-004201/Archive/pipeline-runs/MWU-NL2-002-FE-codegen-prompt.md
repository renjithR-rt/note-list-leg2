## ⛔ HARD GATES — CHECK BEFORE GENERATING ANY CODE

Before writing a single line of code, verify ALL of the following.
If ANY check fails → STOP IMMEDIATELY and output ONLY the abort message.
Do NOT attempt to work around missing inputs.

### Gate 1 — Planning Document
Check if "PRIMARY ARTIFACT" section contains actual content.
If it says "Planning document not found" or is empty:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: planning_doc_missing
    Reason: Planning document not found for module {module}.
    Required: output/mkb/{module}/track-a/planning-001.md
    Action: Run planning agent first, then retry codegen.
  STOP. Do not generate any files.

### Gate 2 — Business Rules
Check if BUSINESS RULES section contains real BR IDs (BR-XXX-NNN format).
If all IDs are identical (e.g. all "BR-PL-001") or count is 0:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: business_rules_missing
    Reason: Business rules not properly loaded for module {module}.
    Required: Distinct BR IDs from comprehension phase.
    Action: Re-run comprehension with MKB tools active, then retry.
  STOP. Do not generate any files.

### Gate 3 — MKB Query Results
After calling mkb_get_business_rules:
If it returns 0 results:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: mkb_empty
    Reason: MKB returned 0 business rules for module {module}.
    Required: Validated BRs in MKB from comprehension phase.
    Action: Check MKB connection and re-run comprehension.
  STOP. Do not generate any files.

### Gate 4 — Critical BR Coverage
After loading BRs, verify these critical rules are present:
  - A rule covering the tax calculation formula
  - A rule covering pay frequency handling
  - A rule covering monetary precision (Decimal)
If any are missing:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: critical_br_missing
    Reason: Critical business rules missing for {module}.
    Missing: {list which critical rules not found}
    Action: Review comprehension output and re-run.
  STOP. Do not generate any files.

## IMPORTANT
A CODEGEN_ABORT response is the CORRECT response when inputs are incomplete.
It is NOT a failure — it prevents generating wrong code that will fail
self-review and waste compute budget on retries.
The orchestrator handles CODEGEN_ABORT by escalating to HITL, not retrying.

## STEP 0.5 — Query Pipeline Lessons

  mkb_query_semantic(
    query="codegen implementation errors PHP FastAPI",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )
  mkb_query_semantic(
    query="pay frequency decimal precision tax calculation",
    project_id="PIPELINE-LESSONS",
    top_k=3,
    min_similarity=0.3
  )

Key lessons to look for and apply:
  - "PENDING_MKB_WRITE causes codegen hallucination"
  - "pay frequency divisor must not be hardcoded"
  - "Decimal not float for monetary values"
  - "bracket formula: base_tax + excess only, no loop accumulation"

---

# Code Generation Agent — Pipeline Mode

You are an expert Python/FastAPI code generation agent operating in
pipeline mode. You receive a complete specification and must return
ALL generated code as structured text output in your response.

## CRITICAL: Output Format
- Return ALL generated files inline in your response
- Use this format for each file:

### FILE: path/to/filename.py
```python
<complete file contents>
```

## File Path Convention — CRITICAL

All generated files MUST use this exact path structure:

  ### FILE: app/modules/{module_name}/models.py        ✅ CORRECT
  ### FILE: app/modules/{module_name}/router.py        ✅ CORRECT
  ### FILE: app/modules/{module_name}/service.py       ✅ CORRECT
  ### FILE: app/modules/{module_name}/schemas.py       ✅ CORRECT
  ### FILE: app/modules/{module_name}/constants.py     ✅ CORRECT
  ### FILE: app/modules/{module_name}/stubs.py         ✅ CORRECT
  ### FILE: tests/modules/{module_name}/conftest.py    ✅ CORRECT
  ### FILE: migrations/versions/001_initial.py         ✅ CORRECT

NEVER repeat the module name as a subfolder inside itself:

  ### FILE: app/modules/admin_fiscal_years/admin_fiscal_years/models.py  ❌ WRONG
  ### FILE: app/modules/gl/gl/models.py                                   ❌ WRONG
  ### FILE: app/modules/taxes/taxes/service.py                            ❌ WRONG

Rule: the module folder IS the module namespace.
      Do not create any subfolder with the same name as the module folder.

Shared infrastructure files use these paths:
  ### FILE: app/db/base.py                             ✅ CORRECT
  ### FILE: app/auth/dependencies.py                   ✅ CORRECT
  ### FILE: app/main.py                                ✅ CORRECT

- Do NOT write files to disk
- Do NOT ask for permissions
- Do NOT ask clarifying questions
- Return COMPLETE file contents — no placeholders, no truncation
- If a file is long, include every line — do not summarise

## CRITICAL: ### FILE: MARKER RULES

The ### FILE: marker MUST follow these rules without exception:

1. ### FILE: markers appear ONLY as top-level lines in your response.
   They must NEVER appear inside:
   - Python docstrings (triple-quoted strings)
   - Comments (# lines or block comments)
   - String literals of any kind
   - Test file headers or module-level strings
   - Any quoted or code-fenced content

2. Each file appears EXACTLY ONCE in your response.
   Never repeat a ### FILE: block for the same path.
   If you need to correct a previously written file,
   DO NOT emit it again — the extractor uses last-wins
   but multiple copies cause line count explosion and
   syntax errors.

3. If you reference a filename in documentation or a docstring,
   use plain prose — never the ### FILE: marker syntax:
   CORRECT:   "See app/modules/taxes/service.py for full implementation"
   INCORRECT: "### FILE: app/modules/taxes/service.py" inside a string

This has caused production defects in two consecutive MWU runs:
  MWU-FA-001-PIPE: test_dimensions.py emitted 3× (2141 → 1133 lines)
  MWU-FA-002-PIPE: service.py emitted 3× (two copies truncated)

10. You MUST emit integration-hints.json as the final FILE: block.
    The integration pipeline reads this to register your module in
    the application. Missing or wrong router paths will break app startup.

---
## Available MKB Tools — USE THESE BEFORE GENERATING CODE

You have access to the Migration Knowledge Base via MCP tools.
These tools contain 174 structured artifacts from this migration
project — validated business rules, approved patterns, schema
mappings, and source code findings.

---
## RETRY RUN DETECTION — READ FIRST

Before doing anything else, check if this is a retry run:
- Look for a section called "REVISION NOTES" or "SELF-REVIEW ISSUES"
  in this prompt
- If found → this is a RETRY RUN. Skip STEP 1 entirely. The business
  rules are already embedded in the PLANNING DOCUMENT section (400+
  references). Jump directly to generating ### FILE: blocks.
- If not found → this is a FIRST RUN. Execute STEP 1 normally.

RETRY RUNS MUST BEGIN GENERATING FILES WITHIN 60 SECONDS.
Do not query MKB. Do not re-read context. Start with ### FILE: immediately.
---

STEP 1 — MANDATORY before writing any code:

  Call mkb_get_business_rules with the module name:
    mkb_get_business_rules(module="dimensions")
    mkb_get_business_rules(module="taxes")
    etc.

  This returns the authoritative validated business rule list.
  Cross-check against the BRs in your prompt context.
  If they differ, the MKB version is authoritative.
  You MUST implement every rule returned.

STEP 2 — RECOMMENDED while planning your implementation:

  Call mkb_query_semantic to find approved patterns:
    mkb_query_semantic(
        query="round2 decimal monetary precision SQLAlchemy",
        top_k=5
    )
    → finds canonical money-handling patterns from approved modules

    mkb_query_semantic(
        query="FastAPI async session dependency injection",
        top_k=3
    )
    → finds architecture patterns from prior approved modules

    mkb_query_semantic(
        query="SQLAlchemy ORM model PostgreSQL column mapping",
        top_k=3
    )
    → finds approved ORM patterns

STEP 3 — AFTER generating code (mark BRs as implemented):

  For each business rule you have implemented, call:
    mkb_update_artifact_status(
        artifact_id="uuid-from-step-1",
        status="IMPLEMENTED"
    )

STRICT RULES:
  - Call MKB tools ONLY during your analysis phase
  - NEVER call MKB tools after you have written your first ### FILE: block
  - If mkb_get_business_rules returns rules not in your prompt,
    add them to your implementation — they are validated requirements
  - If mkb_query_semantic returns an approved service.py pattern,
    follow it exactly for consistency across modules
---

## What You Will Receive
You will receive:
1. A planning specification with DDL, ORM models, endpoints, services
2. A comprehension document with business rules
3. Source PHP files for reference (if available)
4. Example code from previously approved modules

## What You Must Produce
Generate ALL of the following files completely:
- app/modules/{module}/models.py
- app/modules/{module}/schemas.py
- app/modules/{module}/service.py
- app/modules/{module}/router.py
- app/modules/{module}/__init__.py
- app/modules/{module}/stubs.py (if subsystem stubs needed)
- migrations/{NNN}_{module}.sql
- tests/modules/{module}/conftest.py
- tests/modules/{module}/test_{module}.py
- integration-hints.json

The last required file is always the integration manifest. Emit it as:

### FILE: integration-hints.json
```json
{
  "mwu_id": "{mwu_id}",
  "module": "{module}",
  "depends_on_modules": ["list every module whose models are referenced via ForeignKey in this module's models.py"],
  "files_generated": [
    "list every app/ file you generated"
  ],
  "routers": [
    {
      "import_path": "app.modules.{module}.router",
      "variable": "router",
      "alias": "{module}_router",
      "tag": "{module}"
    }
  ],
  "smoke_test_endpoints": [
    {"method": "GET", "path": "/api/{module}/", "expect_status": [200, 401]}
  ],
  "migration_sql": ["list any migrations/ files generated"],
  "utilities_added": ["list any app/utils/ files added"]
}
```

CRITICAL: This file is read by the integration pipeline.
- routers list must be accurate — wrong entries break app startup
- import_path must match actual generated file paths exactly
- If no routers generated, set routers to empty array []
- If tech stack has no router registration (e.g. Spring Boot),
  set routers to [] and add "registration_strategy": "none"
- depends_on_modules must list every module whose SQLAlchemy models
  are referenced via ForeignKey in this module's models.py
  (e.g. ["purchasing_suppliers", "gl"] if supplier_id or account_id
  FKs appear). Set to [] if this module has no FK dependencies.

## MANDATORY PATTERNS — FA Project

### 1. require_permission on every endpoint
EVERY endpoint MUST import and use require_permission:

```python
from app.auth.dependencies import require_permission, get_current_user
from app.auth.constants import SA_SUPPMASTER, SA_PURCHASEORDER

@router.get("/suppliers")
async def list_suppliers(
    user: UserContext = Depends(require_permission(SA_SUPPMASTER)),
    db: AsyncSession = Depends(get_db_session),
):
```

NEVER use bare get_current_user without require_permission.

### 2. DELETE endpoints must return Response(status_code=204)

```python
from fastapi import Response

@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(...) -> Response:
    await svc.delete_supplier(...)
    return Response(status_code=204)
```

NEVER use `-> None` on DELETE endpoints.

### 3. Migration SQL — INTEGER GENERATED ALWAYS AS IDENTITY not SERIAL

CORRECT:
```sql
  order_no    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
```

WRONG:
```sql
  order_no    SERIAL PRIMARY KEY,
  id          SERIAL PRIMARY KEY,
  id          BIGSERIAL PRIMARY KEY,
```

NEVER use SERIAL or BIGSERIAL in migration SQL.
Always use INTEGER GENERATED ALWAYS AS IDENTITY for auto-increment PKs.

### 4. Pydantic v2 — no decimal_places in Field()
NEVER use `decimal_places=` in Field() — not supported in Pydantic v2.

WRONG:
```python
amount: Decimal = Field(..., decimal_places=2)
```

CORRECT:
```python
amount: Decimal = Field(...)
```

Decimal precision is enforced at DB layer via Numeric(19,6).

---
## Quality Requirements
- Zero float() for monetary values — use Decimal throughout
- All async/await — no blocking database calls
- Every business rule from the spec must be implemented
- Type hints on every function
- Docstrings on every public method
- Tests must cover every business rule


---

﻿# Codegen Stack Layer — Python / FastAPI / PostgreSQL / pytest

## PostgreSQL DDL Rules
NEVER use SERIAL, BIGSERIAL, SMALLSERIAL pseudo-types
ALWAYS use GENERATED ALWAYS AS IDENTITY:
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY

NEVER use float or double for monetary values
ALWAYS use Decimal / NUMERIC(16,2)

## SQLAlchemy Async Rules
NEVER use sync session (Session)
ALWAYS use AsyncSession:
  from sqlalchemy.ext.asyncio import AsyncSession
  async with AsyncSession(engine) as session:
      result = await session.execute(select(Model))

NEVER use f-strings for SQL
ALWAYS use bound parameters via SQLAlchemy ORM

## Pydantic v2 Rules
ALWAYS use model_config = ConfigDict(from_attributes=True)
NEVER use class Config: orm_mode = True (v1 syntax)
ALWAYS use @model_validator(mode='before') not @validator

## pytest-asyncio Rules
NEVER use @pytest_asyncio.async_test — this decorator does not exist
ALWAYS use:
  import pytest
  import pytest_asyncio
  @pytest.mark.asyncio
  async def test_name():

NEVER use asyncio.run() inside tests
ALWAYS rely on pytest-asyncio event loop management

## FastAPI Patterns
ALWAYS use async def for endpoint functions
NEVER use def (sync) for DB-touching endpoints
ALWAYS use Depends() for dependency injection
NEVER import db session as a global

## File Structure (required — missing files cause test collection failure)
Every generated backend module MUST include:
  app/__init__.py
  app/main.py              ← FastAPI app + CORSMiddleware + include_router
  app/db/__init__.py
  app/db/session.py        ← get_db_session + engine + AsyncSessionLocal
  app/modules/{module}/__init__.py
  app/modules/{module}/models.py
  app/modules/{module}/router.py
  app/modules/{module}/schemas.py
  app/modules/{module}/service.py

## app/db/ Structure (REQUIRED — missing causes test collection failure)
ALWAYS generate these files — tests will fail to collect without them:
  app/db/__init__.py        (empty)
  app/db/session.py         (get_db_session + engine + AsyncSessionLocal)

conftest.py imports determine which file to create:
  from app.db.session import get_db_session → create app/db/session.py
  from app.db.base import get_db_session    → create app/db/base.py

## app/main.py Router Prefix Rule (REQUIRED — wrong prefix causes 404 on all endpoint tests)
NEVER add a prefix to include_router() in app/main.py:
  CORRECT:   app.include_router(notes_router)
  INCORRECT: app.include_router(notes_router, prefix="/api/v1")

The router's own prefix (e.g. prefix="/notes") already sets the path.
Adding a second prefix in main.py creates /api/v1/notes but tests call /notes — all 404.

## conftest.py TEST_DATABASE_URL Rule (REQUIRED — hardcoded credentials break CI)
ALWAYS read TEST_DATABASE_URL from environment in conftest.py:
  CORRECT:
    import os
    TEST_DATABASE_URL = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://notelist:notelist@localhost:5436/notes_test",
    )
  INCORRECT:
    TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost/notes_test"

Default fallback must use:
  - Port 5436 (notelist-target-postgres Docker container)
  - Credentials: notelist:notelist
  - Database: notes_test (isolated from notelist_modern)


---

## ⛔ HARD GATES — CHECK BEFORE GENERATING ANY CODE

Before writing a single line of code, verify ALL of the following.
If ANY check fails → STOP IMMEDIATELY and output ONLY the abort message.
Do NOT attempt to work around missing inputs.

### Gate 1 — Planning Document
Check if "PRIMARY ARTIFACT" section contains actual content.
If it says "Planning document not found" or is empty:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: planning_doc_missing
    Reason: Planning document not found for module {module}.
    Required: output/mkb/{module}/track-a/planning-001.md
    Action: Run planning agent first, then retry codegen.
  STOP. Do not generate any files.

### Gate 2 — Business Rules
Check if BUSINESS RULES section contains real BR IDs (BR-XXX-NNN format).
If all IDs are identical (e.g. all "BR-PL-001") or count is 0:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: business_rules_missing
    Reason: Business rules not properly loaded for module {module}.
    Required: Distinct BR IDs from comprehension phase.
    Action: Re-run comprehension with MKB tools active, then retry.
  STOP. Do not generate any files.

### Gate 3 — MKB Query Results
After calling mkb_get_business_rules:
If it returns 0 results:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: mkb_empty
    Reason: MKB returned 0 business rules for module {module}.
    Required: Validated BRs in MKB from comprehension phase.
    Action: Check MKB connection and re-run comprehension.
  STOP. Do not generate any files.

### Gate 4 — Critical BR Coverage
After loading BRs, verify these critical rules are present:
  - A rule covering the tax calculation formula
  - A rule covering pay frequency handling
  - A rule covering monetary precision (Decimal)
If any are missing:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: critical_br_missing
    Reason: Critical business rules missing for {module}.
    Missing: {list which critical rules not found}
    Action: Review comprehension output and re-run.
  STOP. Do not generate any files.

## IMPORTANT
A CODEGEN_ABORT response is the CORRECT response when inputs are incomplete.
It is NOT a failure — it prevents generating wrong code that will fail
self-review and waste compute budget on retries.
The orchestrator handles CODEGEN_ABORT by escalating to HITL, not retrying.

## STEP 0.5 — Query Pipeline Lessons

  mkb_query_semantic(
    query="codegen implementation errors PHP FastAPI",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )
  mkb_query_semantic(
    query="pay frequency decimal precision tax calculation",
    project_id="PIPELINE-LESSONS",
    top_k=3,
    min_similarity=0.3
  )

Key lessons to look for and apply:
  - "PENDING_MKB_WRITE causes codegen hallucination"
  - "pay frequency divisor must not be hardcoded"
  - "Decimal not float for monetary values"
  - "bracket formula: base_tax + excess only, no loop accumulation"

---

# Code Generation Agent — Pipeline Mode

You are an expert Python/FastAPI code generation agent operating in
pipeline mode. You receive a complete specification and must return
ALL generated code as structured text output in your response.

## CRITICAL: Output Format
- Return ALL generated files inline in your response
- Use this format for each file:

### FILE: path/to/filename.py
```python
<complete file contents>
```

## File Path Convention — CRITICAL

All generated files MUST use this exact path structure:

  ### FILE: app/modules/{module_name}/models.py        ✅ CORRECT
  ### FILE: app/modules/{module_name}/router.py        ✅ CORRECT
  ### FILE: app/modules/{module_name}/service.py       ✅ CORRECT
  ### FILE: app/modules/{module_name}/schemas.py       ✅ CORRECT
  ### FILE: app/modules/{module_name}/constants.py     ✅ CORRECT
  ### FILE: app/modules/{module_name}/stubs.py         ✅ CORRECT
  ### FILE: tests/modules/{module_name}/conftest.py    ✅ CORRECT
  ### FILE: migrations/versions/001_initial.py         ✅ CORRECT

NEVER repeat the module name as a subfolder inside itself:

  ### FILE: app/modules/admin_fiscal_years/admin_fiscal_years/models.py  ❌ WRONG
  ### FILE: app/modules/gl/gl/models.py                                   ❌ WRONG
  ### FILE: app/modules/taxes/taxes/service.py                            ❌ WRONG

Rule: the module folder IS the module namespace.
      Do not create any subfolder with the same name as the module folder.

Shared infrastructure files use these paths:
  ### FILE: app/db/base.py                             ✅ CORRECT
  ### FILE: app/auth/dependencies.py                   ✅ CORRECT
  ### FILE: app/main.py                                ✅ CORRECT

- Do NOT write files to disk
- Do NOT ask for permissions
- Do NOT ask clarifying questions
- Return COMPLETE file contents — no placeholders, no truncation
- If a file is long, include every line — do not summarise

## CRITICAL: ### FILE: MARKER RULES

The ### FILE: marker MUST follow these rules without exception:

1. ### FILE: markers appear ONLY as top-level lines in your response.
   They must NEVER appear inside:
   - Python docstrings (triple-quoted strings)
   - Comments (# lines or block comments)
   - String literals of any kind
   - Test file headers or module-level strings
   - Any quoted or code-fenced content

2. Each file appears EXACTLY ONCE in your response.
   Never repeat a ### FILE: block for the same path.
   If you need to correct a previously written file,
   DO NOT emit it again — the extractor uses last-wins
   but multiple copies cause line count explosion and
   syntax errors.

3. If you reference a filename in documentation or a docstring,
   use plain prose — never the ### FILE: marker syntax:
   CORRECT:   "See app/modules/taxes/service.py for full implementation"
   INCORRECT: "### FILE: app/modules/taxes/service.py" inside a string

This has caused production defects in two consecutive MWU runs:
  MWU-FA-001-PIPE: test_dimensions.py emitted 3× (2141 → 1133 lines)
  MWU-FA-002-PIPE: service.py emitted 3× (two copies truncated)

10. You MUST emit integration-hints.json as the final FILE: block.
    The integration pipeline reads this to register your module in
    the application. Missing or wrong router paths will break app startup.

---
## Available MKB Tools — USE THESE BEFORE GENERATING CODE

You have access to the Migration Knowledge Base via MCP tools.
These tools contain 174 structured artifacts from this migration
project — validated business rules, approved patterns, schema
mappings, and source code findings.

---
## RETRY RUN DETECTION — READ FIRST

Before doing anything else, check if this is a retry run:
- Look for a section called "REVISION NOTES" or "SELF-REVIEW ISSUES"
  in this prompt
- If found → this is a RETRY RUN. Skip STEP 1 entirely. The business
  rules are already embedded in the PLANNING DOCUMENT section (400+
  references). Jump directly to generating ### FILE: blocks.
- If not found → this is a FIRST RUN. Execute STEP 1 normally.

RETRY RUNS MUST BEGIN GENERATING FILES WITHIN 60 SECONDS.
Do not query MKB. Do not re-read context. Start with ### FILE: immediately.
---

STEP 1 — MANDATORY before writing any code:

  Call mkb_get_business_rules with the module name:
    mkb_get_business_rules(module="dimensions")
    mkb_get_business_rules(module="taxes")
    etc.

  This returns the authoritative validated business rule list.
  Cross-check against the BRs in your prompt context.
  If they differ, the MKB version is authoritative.
  You MUST implement every rule returned.

STEP 2 — RECOMMENDED while planning your implementation:

  Call mkb_query_semantic to find approved patterns:
    mkb_query_semantic(
        query="round2 decimal monetary precision SQLAlchemy",
        top_k=5
    )
    → finds canonical money-handling patterns from approved modules

    mkb_query_semantic(
        query="FastAPI async session dependency injection",
        top_k=3
    )
    → finds architecture patterns from prior approved modules

    mkb_query_semantic(
        query="SQLAlchemy ORM model PostgreSQL column mapping",
        top_k=3
    )
    → finds approved ORM patterns

STEP 3 — AFTER generating code (mark BRs as implemented):

  For each business rule you have implemented, call:
    mkb_update_artifact_status(
        artifact_id="uuid-from-step-1",
        status="IMPLEMENTED"
    )

STRICT RULES:
  - Call MKB tools ONLY during your analysis phase
  - NEVER call MKB tools after you have written your first ### FILE: block
  - If mkb_get_business_rules returns rules not in your prompt,
    add them to your implementation — they are validated requirements
  - If mkb_query_semantic returns an approved service.py pattern,
    follow it exactly for consistency across modules
---

## What You Will Receive
You will receive:
1. A planning specification with DDL, ORM models, endpoints, services
2. A comprehension document with business rules
3. Source PHP files for reference (if available)
4. Example code from previously approved modules

## What You Must Produce
Generate ALL of the following files completely:
- app/modules/{module}/models.py
- app/modules/{module}/schemas.py
- app/modules/{module}/service.py
- app/modules/{module}/router.py
- app/modules/{module}/__init__.py
- app/modules/{module}/stubs.py (if subsystem stubs needed)
- migrations/{NNN}_{module}.sql
- tests/modules/{module}/conftest.py
- tests/modules/{module}/test_{module}.py
- integration-hints.json

The last required file is always the integration manifest. Emit it as:

### FILE: integration-hints.json
```json
{
  "mwu_id": "{mwu_id}",
  "module": "{module}",
  "depends_on_modules": ["list every module whose models are referenced via ForeignKey in this module's models.py"],
  "files_generated": [
    "list every app/ file you generated"
  ],
  "routers": [
    {
      "import_path": "app.modules.{module}.router",
      "variable": "router",
      "alias": "{module}_router",
      "tag": "{module}"
    }
  ],
  "smoke_test_endpoints": [
    {"method": "GET", "path": "/api/{module}/", "expect_status": [200, 401]}
  ],
  "migration_sql": ["list any migrations/ files generated"],
  "utilities_added": ["list any app/utils/ files added"]
}
```

CRITICAL: This file is read by the integration pipeline.
- routers list must be accurate — wrong entries break app startup
- import_path must match actual generated file paths exactly
- If no routers generated, set routers to empty array []
- If tech stack has no router registration (e.g. Spring Boot),
  set routers to [] and add "registration_strategy": "none"
- depends_on_modules must list every module whose SQLAlchemy models
  are referenced via ForeignKey in this module's models.py
  (e.g. ["purchasing_suppliers", "gl"] if supplier_id or account_id
  FKs appear). Set to [] if this module has no FK dependencies.

## MANDATORY PATTERNS — FA Project

### 1. require_permission on every endpoint
EVERY endpoint MUST import and use require_permission:

```python
from app.auth.dependencies import require_permission, get_current_user
from app.auth.constants import SA_SUPPMASTER, SA_PURCHASEORDER

@router.get("/suppliers")
async def list_suppliers(
    user: UserContext = Depends(require_permission(SA_SUPPMASTER)),
    db: AsyncSession = Depends(get_db_session),
):
```

NEVER use bare get_current_user without require_permission.

### 2. DELETE endpoints must return Response(status_code=204)

```python
from fastapi import Response

@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(...) -> Response:
    await svc.delete_supplier(...)
    return Response(status_code=204)
```

NEVER use `-> None` on DELETE endpoints.

### 3. Migration SQL — INTEGER GENERATED ALWAYS AS IDENTITY not SERIAL

CORRECT:
```sql
  order_no    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
```

WRONG:
```sql
  order_no    SERIAL PRIMARY KEY,
  id          SERIAL PRIMARY KEY,
  id          BIGSERIAL PRIMARY KEY,
```

NEVER use SERIAL or BIGSERIAL in migration SQL.
Always use INTEGER GENERATED ALWAYS AS IDENTITY for auto-increment PKs.

### 4. Pydantic v2 — no decimal_places in Field()
NEVER use `decimal_places=` in Field() — not supported in Pydantic v2.

WRONG:
```python
amount: Decimal = Field(..., decimal_places=2)
```

CORRECT:
```python
amount: Decimal = Field(...)
```

Decimal precision is enforced at DB layer via Numeric(19,6).

---
## Quality Requirements
- Zero float() for monetary values — use Decimal throughout
- All async/await — no blocking database calls
- Every business rule from the spec must be implemented
- Type hints on every function
- Docstrings on every public method
- Tests must cover every business rule



======================================================================
## BUSINESS RULES
======================================================================

No business rules assigned to this MWU.



======================================================================
## PRIMARY ARTIFACT
======================================================================

# Planning Document — MWU-NL2-002-FE frontend
**Phase:** Planning
**MWU Tier:** LOW
**Date:** 2026-05-19
**Source stack:** PHP 5.6 (single-file, procedural, MySQL)
**Target stack:** React 18 + TypeScript + Vite
**Business Rules:** 11 rules (from comprehension BR catalog)
**Dependencies:** MWU-NL-001 (backend FastAPI — provides REST API contract)

---

## §1 — Target Data Model (TypeScript Type Definitions)

This MWU owns no database tables. §1 defines the TypeScript type definitions that model the data exchanged with the backend API and managed in React component state. These types are the frontend's canonical data contract with MWU-NL-001.

```typescript
// src/types/note.ts

/** A single note returned by the API */
export interface Note {
  id: number;
  content: string;      // plain text, 1–500 chars
  created_at: string;   // ISO 8601 — e.g. "2026-05-18T14:32:00.000Z"
}

/** GET /notes returns an ordered array — newest first (BR-NL-FE-004) */
export type NoteListResponse = Note[];

/** POST /notes request body — trimmed content only (BR-NL-FE-010) */
export interface CreateNoteRequest {
  content: string; // trimmed, 1–500 chars — no pre-escaping (RISK-002)
}

/** Generic message response from successful POST/DELETE */
export interface ApiSuccessResponse {
  message: string;
}

/** FastAPI 422 Unprocessable Entity response shape */
export interface ApiValidationError {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}

/** FastAPI 404 Not Found response */
export interface ApiNotFoundError {
  detail: string;
}

/** Feedback state shape used in App component */
export interface FeedbackState {
  message: string;
  type: 'success' | 'error';
}
```

### Column/Field Type Decisions

| Field | API Type | Frontend TS Type | Rationale |
|-------|----------|-----------------|-----------|
| `id` | integer | `number` | Safe for PostgreSQL SERIAL (≤ 2^31) |
| `content` | string | `string` | Plain text — no escaping by frontend (RISK-002) |
| `created_at` | ISO 8601 string | `string` → `Date` via `new Date()` | Formatted with `Intl.DateTimeFormat` per BR-NL-FE-005 |

---

## §2 — Target ORM / Data Access Models (API Client Layer)

The API client is a standalone module encapsulating all HTTP calls. It classifies errors into a typed `ApiError` class so callers can branch on status codes (BR-NL-FE-011).

```typescript
// src/api/notesApi.ts

import type { Note, NoteListResponse } from '../types/note';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

/**
 * Typed API error — always has an HTTP status code and human-readable detail.
 * Thrown for any non-2xx response. Callers check err.status for 404 vs 5xx branching.
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

/** Parse response body and throw ApiError for non-2xx. */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return {} as T;
    return response.json() as Promise<T>;
  }

  let detail = `HTTP ${response.status} error`;
  try {
    const body = await response.json() as { detail?: string | Array<{ msg: string }> };
    if (typeof body?.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      detail = body.detail[0].msg;
    }
  } catch {
    // Body is not JSON — keep the generic message
  }

  throw new ApiError(response.status, detail);
}

/**
 * BR-NL-FE-004: API guarantees newest-first order — frontend does not re-sort.
 * BR-NL-FE-011: Network and HTTP errors surfaced as ApiError.
 */
export async function getNotes(): Promise<NoteListResponse> {
  const response = await fetch(`${BASE_URL}/notes`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<NoteListResponse>(response);
}

/**
 * BR-NL-FE-010: content must already be trimmed by the caller.
 * RISK-002: send raw trimmed content — never pre-escape HTML or SQL characters.
 * BR-NL-FE-011: 422 validation errors surfaced with detail message.
 */
export async function createNote(content: string): Promise<Note> {
  const response = await fetch(`${BASE_URL}/notes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ content }),
  });
  return handleResponse<Note>(response);
}

/**
 * BR-NL-FE-007: uses HTTP DELETE — never GET.
 * BR-NL-FE-011: 404 propagated as ApiError with status 404.
 */
export async function deleteNote(id: number): Promise<void> {
  const response = await fetch(`${BASE_URL}/notes/${id}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  });
  await handleResponse<void>(response);
}
```

### Error Classification Matrix

| Condition | Thrown As | `err.status` | Caller Action |
|-----------|-----------|-------------|---------------|
| Network failure (fetch rejects) | `TypeError` | — | Show "Network error — please check your connection." |
| 404 Not Found | `ApiError` | 404 | Show "Note not found", refresh list |
| 422 Unprocessable | `ApiError` | 422 | Show `err.detail` as inline field error |
| 5xx Server Error | `ApiError` | 500+ | Show "Server error, please try again." |
| 2xx Success | — (no throw) | — | Update state |

---

## §3 — Validation Schemas / DTOs (Client-Side Validation)

Frontend validation runs before any API call. Validators are pure functions returning typed results — no side effects, fully unit-testable.

```typescript
// src/validation/noteValidation.ts

/** Maximum note length — mirrors BR-NL-002 server-side MAX_NOTE_LENGTH=500 */
export const MAX_NOTE_LENGTH = 500;

export interface ValidationResult {
  valid: boolean;
  error: string | null;
}

/**
 * BR-NL-FE-001: reject empty or whitespace-only content.
 * BR-NL-FE-002: reject content exceeding 500 characters.
 * BR-NL-FE-010: length check applied AFTER trim (trim is implicit here).
 *
 * Called before every POST /notes submission.
 */
export function validateNoteContent(raw: string): ValidationResult {
  const trimmed = raw.trim();

  // BR-NL-FE-001: empty check (post-trim)
  if (trimmed.length === 0) {
    return { valid: false, error: 'Note content cannot be empty.' };
  }

  // BR-NL-FE-002: length check (post-trim, to match server-side behaviour)
  if (trimmed.length > MAX_NOTE_LENGTH) {
    return {
      valid: false,
      error: `Note content exceeds the maximum length of ${MAX_NOTE_LENGTH} characters.`,
    };
  }

  return { valid: true, error: null };
}

/**
 * BR-NL-FE-010: return trimmed value ready to send to API.
 * RISK-002: do NOT escape HTML, SQL, or any special characters here —
 * that corrupts stored data. The API/ORM handles query safety.
 */
export function prepareContent(raw: string): string {
  return raw.trim();
}

/**
 * BR-NL-FE-002: remaining characters for the visible counter UI.
 * Measured on raw (un-trimmed) value for the counter, since the textarea
 * applies maxLength on the raw value. Negative when over limit.
 */
export function getRemainingChars(raw: string): number {
  return MAX_NOTE_LENGTH - raw.length;
}
```

### Validation Rule Summary

| BR | Input Condition | Validation Response |
|----|----------------|-------------------|
| BR-NL-FE-001 | `"".trim() === ""` | Error: "Note content cannot be empty." |
| BR-NL-FE-001 | `"   ".trim() === ""` | Error: "Note content cannot be empty." |
| BR-NL-FE-002 | `trimmed.length > 500` | Error: "Note content exceeds the maximum length of 500 characters." |
| BR-NL-FE-010 | Any content | `content.trim()` applied before API call |
| RISK-002 | Content with `'`, `<`, `>`, `&` | Sent raw — no pre-escaping |

---

## §4 — API / Interface Design (Component Props and API Contract)

### 4.1 Component Props Interfaces

```typescript
// src/types/props.ts

import type { Note } from './note';

/** BR-NL-FE-008: inline success/error feedback bar */
export interface FeedbackMessageProps {
  message: string | null;
  type: 'success' | 'error' | null;
}

/** BR-NL-FE-001, BR-NL-FE-002, BR-NL-FE-010: add note form */
export interface AddNoteFormProps {
  onNoteAdded: (note: Note) => void;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

/** BR-NL-FE-004: note list preserving API order */
export interface NoteListProps {
  notes: Note[];
  onNoteDeleted: (id: number) => void;
  onDeleteError: (message: string) => void;
  onDeleteSuccess: (message: string) => void;
}

/** BR-NL-FE-003, BR-NL-FE-005, BR-NL-FE-007 */
export interface NoteItemProps {
  note: Note;
  onDelete: (id: number) => void;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}
```

### 4.2 Backend API Endpoints Consumed

These endpoints are owned by MWU-NL-001. The frontend treats them as an external contract.

| Method | Path | Request Body | Success Response | BRs Consumed |
|--------|------|-------------|-----------------|--------------|
| GET | `/notes` | — | `Note[]` (newest first) | BR-NL-FE-004, BR-NL-FE-011 |
| POST | `/notes` | `{ content: string }` | `Note` (201) | BR-NL-FE-001, BR-NL-FE-002, BR-NL-FE-010, BR-NL-FE-011 |
| DELETE | `/notes/{id}` | — | 200/204 or 404 | BR-NL-FE-007, BR-NL-FE-011 |

### 4.3 Error Response Handling Table

| HTTP Status | Trigger | Frontend UX Action |
|-------------|---------|-------------------|
| 200 / 201 | Successful GET/POST | Update state; show success feedback (BR-NL-FE-008) |
| 204 | Successful DELETE | Remove note from list; show "Note deleted." |
| 404 | Delete of non-existent note | Show "Note not found — refreshing list."; re-fetch list (BR-NL-FE-011, RISK-007) |
| 422 | Validation error from API | Display `detail[0].msg` as inline field error (BR-NL-FE-001/002) |
| 500 | Internal server error | Show "Server error, please try again." |
| Network failure | `fetch()` throws `TypeError` | Show "Network error — please check your connection." |

### 4.4 No Authentication (BR-NL-FE-006 — CRITICAL)

The frontend exposes **zero authentication UI**. There are no login forms, no token storage, no protected route wrappers, no `useAuth` hooks, no session checks. This mirrors the legacy source which has no auth. Any authentication concern belongs to infrastructure (reverse proxy, network policy) — not this application layer.

---

## §5 — Service Layer Design (Component Architecture)

### 5.1 Component Tree

```
App
├── Header                  (static — app title)
├── FeedbackMessage         (BR-NL-FE-008: inline success/error)
├── AddNoteForm             (BR-NL-FE-001, 002, 010: validation + trim + counter)
│   ├── <textarea>          (maxLength=500, char counter)
│   └── <button type="submit">
├── NoteList                (BR-NL-FE-004: render in API order, no re-sort)
│   └── NoteItem[]
│       ├── <p>{note.content}</p>        (BR-NL-FE-003: text node, never innerHTML)
│       ├── <time>{formatDate(...)}</time> (BR-NL-FE-005: Intl formatting)
│       └── <button type="button">Delete</button>  (BR-NL-FE-007: HTTP DELETE)
└── Footer                  (static)
```

No React Router. No external state management. `useState` is sufficient.

### 5.2 App Component — Full Implementation

```typescript
// src/App.tsx
// BR-NL-FE-009: single-page layout — all functionality here, no routing.
// BR-NL-FE-006: no auth state, no login, no protected routes.

import React, { useState, useEffect, useCallback } from 'react';
import { getNotes, ApiError } from './api/notesApi';
import Header from './components/Header';
import FeedbackMessage from './components/FeedbackMessage';
import AddNoteForm from './components/AddNoteForm';
import NoteList from './components/NoteList';
import Footer from './components/Footer';
import type { Note, FeedbackState } from './types/note';

const FEEDBACK_TIMEOUT_MS = 4000;

export default function App(): React.JSX.Element {
  const [notes, setNotes] = useState<Note[]>([]);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [loading, setLoading] = useState(true);

  const showFeedback = useCallback((message: string, type: 'success' | 'error'): void => {
    setFeedback({ message, type });
    setTimeout(() => setFeedback(null), FEEDBACK_TIMEOUT_MS);
  }, []);

  const loadNotes = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      const data = await getNotes();
      setNotes(data); // BR-NL-FE-004: preserve API order — no re-sort
    } catch (err) {
      showFeedback(resolveErrorMessage(err), 'error');
    } finally {
      setLoading(false);
    }
  }, [showFeedback]);

  useEffect(() => {
    void loadNotes();
  }, [loadNotes]);

  function handleNoteAdded(note: Note): void {
    // Prepend to mirror the newest-first API sort order
    setNotes(prev => [note, ...prev]);
  }

  function handleNoteDeleted(id: number): void {
    setNotes(prev => prev.filter(n => n.id !== id));
  }

  async function handleDeleteError(message: string): Promise<void> {
    showFeedback(message, 'error');
    // BR-NL-FE-011 / RISK-007: on 404, re-fetch list to sync state
    if (message.toLowerCase().includes('not found')) {
      await loadNotes();
    }
  }

  return (
    <div className="app-container">
      <Header />
      <main className="app-main">
        <FeedbackMessage
          message={feedback?.message ?? null}
          type={feedback?.type ?? null}
        />
        <AddNoteForm
          onNoteAdded={handleNoteAdded}
          onError={msg => showFeedback(msg, 'error')}
          onSuccess={msg => showFeedback(msg, 'success')}
        />
        {loading ? (
          <p className="loading-state">Loading notes…</p>
        ) : (
          <NoteList
            notes={notes}
            onNoteDeleted={handleNoteDeleted}
            onDeleteError={handleDeleteError}
            onDeleteSuccess={msg => showFeedback(msg, 'success')}
          />
        )}
      </main>
      <Footer />
    </div>
  );
}

function resolveErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.detail;
  if (err instanceof TypeError) return 'Network error — please check your connection.';
  return 'An unexpected error occurred.';
}
```

**BR coverage in App:**

| Method | BRs Implemented |
|--------|----------------|
| `loadNotes()` | BR-NL-FE-004 (no re-sort), BR-NL-FE-011 (error display) |
| `handleNoteAdded()` | BR-NL-FE-008 (success feedback via caller) |
| `handleNoteDeleted()` | BR-NL-FE-008 (success feedback via caller) |
| `handleDeleteError()` | BR-NL-FE-011 (404 triggers list refresh) |
| `showFeedback()` | BR-NL-FE-008 (auto-clear after 4s) |

### 5.3 AddNoteForm Component — Full Implementation

```typescript
// src/components/AddNoteForm.tsx
// Implements: BR-NL-FE-001 (empty reject), BR-NL-FE-002 (length limit + counter),
//             BR-NL-FE-010 (trim before send), BR-NL-FE-008 (inline error),
//             BR-NL-FE-011 (API error handling)

import React, { useState } from 'react';
import { createNote, ApiError } from '../api/notesApi';
import {
  validateNoteContent,
  prepareContent,
  getRemainingChars,
  MAX_NOTE_LENGTH,
} from '../validation/noteValidation';
import type { AddNoteFormProps } from '../types/props';

export default function AddNoteForm({
  onNoteAdded,
  onError,
  onSuccess,
}: AddNoteFormProps): React.JSX.Element {
  const [content, setContent] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    setContent(e.target.value);
    if (validationError) setValidationError(null); // clear on edit
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();

    // BR-NL-FE-001 + BR-NL-FE-002: client-side validation before API call
    const result = validateNoteContent(content);
    if (!result.valid) {
      setValidationError(result.error);
      return;
    }

    // BR-NL-FE-010: trim before send; RISK-002: do NOT escape special chars
    const trimmed = prepareContent(content);

    try {
      setSubmitting(true);
      const note = await createNote(trimmed);
      setContent('');
      setValidationError(null);
      onNoteAdded(note);
      onSuccess('Note added successfully.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        // Server validation error — show inline (mirrors client-side error UX)
        setValidationError(err.detail);
      } else {
        onError(resolveError(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  const remaining = getRemainingChars(content);
  const overLimit = remaining < 0;

  return (
    <form className="add-note-form" onSubmit={handleSubmit} noValidate>
      <div className="form-field">
        <label htmlFor="note-content">New Note</label>
        <textarea
          id="note-content"
          value={content}
          onChange={handleChange}
          maxLength={MAX_NOTE_LENGTH}
          rows={4}
          placeholder="Enter your note…"
          disabled={submitting}
          aria-describedby={validationError ? 'note-error' : 'char-counter'}
          aria-invalid={validationError !== null}
        />
        {/* BR-NL-FE-002: visible character counter */}
        <span
          id="char-counter"
          className={`char-counter${overLimit ? ' over-limit' : ''}`}
          aria-live="polite"
        >
          {remaining >= 0
            ? `${remaining} characters remaining`
            : `${Math.abs(remaining)} characters over limit`}
        </span>
        {/* BR-NL-FE-001: inline validation error message */}
        {validationError && (
          <span id="note-error" className="field-error" role="alert">
            {validationError}
          </span>
        )}
      </div>
      <button type="submit" disabled={submitting || overLimit} className="btn-primary">
        {submitting ? 'Adding…' : 'Add Note'}
      </button>
    </form>
  );
}

function resolveError(err: unknown): string {
  if (err instanceof ApiError) return err.detail;
  if (err instanceof TypeError) return 'Network error — please check your connection.';
  return 'Failed to add note.';
}
```

### 5.4 NoteList Component — Full Implementation

```typescript
// src/components/NoteList.tsx
// Implements: BR-NL-FE-004 (render in API order — no re-sort)

import React from 'react';
import NoteItem from './NoteItem';
import type { NoteListProps } from '../types/props';

export default function NoteList({
  notes,
  onNoteDeleted,
  onDeleteError,
  onDeleteSuccess,
}: NoteListProps): React.JSX.Element {
  if (notes.length === 0) {
    return <p className="empty-state">No notes yet. Add one above.</p>;
  }

  return (
    <ul className="note-list" aria-label="Notes">
      {/* BR-NL-FE-004: render in received order — never sort client-side */}
      {notes.map(note => (
        <NoteItem
          key={note.id}
          note={note}
          onDelete={onNoteDeleted}
          onError={onDeleteError}
          onSuccess={onDeleteSuccess}
        />
      ))}
    </ul>
  );
}
```

### 5.5 NoteItem Component — Full Implementation

```typescript
// src/components/NoteItem.tsx
// Implements: BR-NL-FE-003 (text-only rendering — no innerHTML),
//             BR-NL-FE-005 (ISO 8601 → "18 May 2026"),
//             BR-NL-FE-007 (HTTP DELETE — never GET, never anchor),
//             BR-NL-FE-011 (404 error path)

import React, { useState } from 'react';
import { deleteNote, ApiError } from '../api/notesApi';
import { formatDate } from '../utils/dateUtils';
import type { NoteItemProps } from '../types/props';

export default function NoteItem({
  note,
  onDelete,
  onError,
  onSuccess,
}: NoteItemProps): React.JSX.Element {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(): Promise<void> {
    try {
      setDeleting(true);
      // BR-NL-FE-007: HTTP DELETE via fetch — never GET, never anchor link
      await deleteNote(note.id);
      onDelete(note.id);
      onSuccess('Note deleted.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // RISK-007 / BR-NL-FE-011: note already gone — sync the list
        onError('Note not found — refreshing list.');
        onDelete(note.id); // remove optimistically; App re-fetches
      } else if (err instanceof TypeError) {
        onError('Network error — please check your connection.');
      } else if (err instanceof ApiError) {
        onError(err.detail);
      } else {
        onError('Failed to delete note.');
      }
    } finally {
      setDeleting(false);
    }
  }

  return (
    <li className="note-item">
      {/*
        BR-NL-FE-003: JSX text interpolation renders as a text node.
        dangerouslySetInnerHTML is NEVER used here — XSS risk (RISK-008).
      */}
      <p className="note-content">{note.content}</p>

      {/* BR-NL-FE-005: ISO 8601 → "18 May 2026" via Intl.DateTimeFormat */}
      <time className="note-date" dateTime={note.created_at}>
        {formatDate(note.created_at)}
      </time>

      {/*
        BR-NL-FE-007: <button type="button"> — never <a href="?delete=...">
        RISK-003: anchor tags for delete are a CSRF anti-pattern and forbidden.
      */}
      <button
        type="button"
        className="btn-delete"
        onClick={handleDelete}
        disabled={deleting}
        aria-label={`Delete note from ${formatDate(note.created_at)}`}
      >
        {deleting ? 'Deleting…' : 'Delete'}
      </button>
    </li>
  );
}
```

### 5.6 FeedbackMessage Component

```typescript
// src/components/FeedbackMessage.tsx
// Implements: BR-NL-FE-008 (inline success/error feedback)

import React from 'react';
import type { FeedbackMessageProps } from '../types/props';

export default function FeedbackMessage({
  message,
  type,
}: FeedbackMessageProps): React.JSX.Element | null {
  if (!message || !type) return null;

  return (
    <div
      className={`feedback-message feedback-${type}`}
      role={type === 'error' ? 'alert' : 'status'}
      aria-live={type === 'error' ? 'assertive' : 'polite'}
    >
      {message}
    </div>
  );
}
```

### 5.7 Header and Footer

```typescript
// src/components/Header.tsx
import React from 'react';

export default function Header(): React.JSX.Element {
  return (
    <header className="app-header">
      <h1>Note List</h1>
    </header>
  );
}

// src/components/Footer.tsx
import React from 'react';

export default function Footer(): React.JSX.Element {
  return (
    <footer className="app-footer">
      <p>Note List App</p>
    </footer>
  );
}
```

### 5.8 Date Utility

```typescript
// src/utils/dateUtils.ts
// BR-NL-FE-005: format ISO 8601 → "18 May 2026"
// RISK-006: use Intl.DateTimeFormat with explicit locale — never toLocaleDateString()
//           without locale (browser inconsistency), never moment.js (bundle weight).

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

/** BR-NL-FE-005: "2026-05-18T10:00:00Z" → "18 May 2026" */
export function formatDate(iso: string): string {
  return DATE_FORMATTER.format(new Date(iso));
}
```

### 5.9 Project Structure

```
src/
├── App.tsx                          # Root — state orchestration
├── main.tsx                         # React DOM root mount
├── api/
│   └── notesApi.ts                  # HTTP client (§2)
├── components/
│   ├── AddNoteForm.tsx              # BR-NL-FE-001/002/010/008
│   ├── FeedbackMessage.tsx          # BR-NL-FE-008
│   ├── Footer.tsx
│   ├── Header.tsx
│   ├── NoteItem.tsx                 # BR-NL-FE-003/005/007/011
│   └── NoteList.tsx                 # BR-NL-FE-004
├── types/
│   ├── note.ts                      # Data model types (§1)
│   └── props.ts                     # Component props interfaces (§4)
├── utils/
│   └── dateUtils.ts                 # BR-NL-FE-005 date formatting
├── validation/
│   └── noteValidation.ts            # BR-NL-FE-001/002/010 validators (§3)
└── test/
    ├── fixtures.ts
    ├── handlers.ts                   # MSW handlers
    └── setup.ts
```

### 5.10 Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/notes': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### 5.11 Entry Point

```typescript
// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

```html
<!-- index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Note List</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### 5.12 Package.json (key dependencies)

```json
{
  "name": "note-list-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^15.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^24.0.0",
    "msw": "^2.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0"
  }
}
```

**Dependency rationale:**
- `react` + `react-dom`: target framework
- `msw`: API mocking for integration tests (no real server required in CI)
- `@testing-library/react`: component testing per React best practices
- No `react-router-dom` — BR-NL-FE-009 (single page, no routing)
- No `axios`, `date-fns`, `moment`, `lodash` — all functionality covered by browser APIs

---

## §6 — Risk Register and Mitigations

### RISK-002: Raw SQL Concatenation — Frontend Data Purity Constraint
**Source behaviour:** Legacy PHP concatenated `$_POST['content']` directly into SQL strings. The PHP layer also applied `htmlspecialchars()` to output. The combination meant content might be stored with HTML-escaped characters if the PHP escaping was applied before storage.

**Target implementation:** The React frontend must send raw trimmed user input to the FastAPI API. The API uses SQLAlchemy ORM with parameterized queries — it handles SQL safety. Pre-escaping on the frontend would cause double-escaping or corrupt stored data.

```typescript
// CORRECT — send raw trimmed content:
const trimmed = content.trim();
const note = await createNote(trimmed);
// API receives: { content: "O'Brien's & <script>" }
// SQLAlchemy binds it as a parameter — no injection possible

// WRONG — pre-escaping corrupts stored data:
const escaped = content
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;');
// User later sees "&amp;" in their note — data corrupted
```

**Validation approach:** Store a note with content `O'Brien's note & <script>alert(1)</script>`. Via the API, verify the stored content is the exact input string. Via the React UI, verify it renders as a text node (see RISK-008).

---

### RISK-003: CSRF — DELETE via GET Anti-pattern
**Source behaviour:** Legacy PHP delete link: `<a href="?delete=1">Delete</a>`. This is a GET request that mutates server state. Any page (attacker-controlled) can embed `<img src="http://app/?delete=1">` to trigger deletion without user consent.

**Target implementation:** All delete operations use `fetch()` with `method: 'DELETE'`. The delete trigger is always `<button type="button">` with an `onClick` handler. Anchor tags are never used for state-changing operations.

```typescript
// CORRECT:
async function handleDelete(): Promise<void> {
  await deleteNote(note.id); // fetch(..., { method: 'DELETE' })
}
// Trigger: <button type="button" onClick={handleDelete}>Delete</button>

// WRONG:
// <a href={`/?delete=${note.id}`}>Delete</a>         ← GET, CSRF-vulnerable
// <a href={`/notes/${note.id}`} method="delete">      ← HTML4 compat fiction
// window.location.href = `/delete?id=${note.id}`;    ← GET, CSRF-vulnerable
```

**Validation approach:** In NoteItem tests, assert that `fetch` is called with `{ method: 'DELETE' }` on delete button click. Assert no `<a>` elements exist in the NoteItem render tree. Grep codebase for `href.*delete` — must return zero results.

---

### RISK-005: Unbounded Note List — No Client-Side Pagination
**Source behaviour:** Legacy PHP: `SELECT * FROM notes ORDER BY created_at DESC` with no LIMIT clause. All notes returned in one response.

**Target implementation:** The React frontend renders all notes returned by the API using `Array.map()`. No client-side LIMIT, slice, or virtual scrolling is added. If the API adds pagination later, the component structure handles it transparently — the `notes` prop remains `Note[]` regardless of source.

```typescript
// CORRECT — works for any array length, accommodates future API pagination:
{notes.map(note => (
  <NoteItem key={note.id} note={note} {...handlers} />
))}

// WRONG — client-side artificial limit is out of scope:
{notes.slice(0, 20).map(...)} // hidden notes — users can't find their data
```

**Validation approach:** Load test with 1000 mock notes. Assert all 1000 `<li>` elements render. Assert no `.slice()` or `.splice()` calls in NoteList source.

---

### RISK-006: Date Formatting — Browser Consistency
**Source behaviour:** Legacy PHP formatted dates server-side: `date('d M Y', strtotime($row['created_at']))` → "18 May 2026". The API now returns ISO 8601 strings — the frontend is responsible for formatting.

**Target implementation:** `Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })` with an explicit locale. This matches the legacy output format and is consistent across all major browsers. `toLocaleDateString()` without locale is avoided — its output depends on the browser's detected OS locale and produces inconsistent results across environments.

```typescript
// CORRECT — explicit locale, consistent output:
const fmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric'
});
fmt.format(new Date('2026-05-18T10:00:00Z')); // "18 May 2026"

// WRONG — locale-dependent, inconsistent:
new Date('2026-05-18').toLocaleDateString();   // "5/18/2026" on en-US OS
import { format } from 'date-fns';             // 21 kB bundle for one format
```

**Validation approach:** Unit test `formatDate()` with five known ISO 8601 strings. Assert output exactly matches "D Mon YYYY" pattern. Test with UTC midnight timestamps to verify no off-by-one date from timezone conversion.

---

### RISK-007: Silent Delete vs 404 — Frontend Dual-Path Handling
**Source behaviour:** Legacy PHP `DELETE FROM notes WHERE id = ?` succeeded silently whether or not the row existed. The backend BR-NL-007 has a NEEDS_VALIDATION annotation on whether the FastAPI endpoint returns 200 or 404 for a non-existent ID.

**Target implementation:** The frontend handles both API behaviours:
- **200/204 success:** Remove note from state, show "Note deleted."
- **404 Not Found:** Show "Note not found — refreshing list.", trigger `loadNotes()` re-fetch to sync the list.

```typescript
try {
  await deleteNote(note.id);
  onDelete(note.id);         // 200/204 path — remove from local state
  onSuccess('Note deleted.');
} catch (err) {
  if (err instanceof ApiError && err.status === 404) {
    onError('Note not found — refreshing list.');
    onDelete(note.id);       // optimistic remove; App.handleDeleteError re-fetches
  } else {
    onError(resolveError(err));
  }
}
```

**Validation approach:** MSW handler for `DELETE /notes/999` returns 404. Assert error message "Note not found" appears. Assert `getNotes()` is called again (list re-fetch). Assert note ID 999 is removed from the displayed list.

---

### RISK-008: XSS — Note Content Rendering
**Source behaviour:** Legacy PHP used `echo htmlspecialchars($row['content'])` to prevent stored XSS. Without escaping, stored `<script>` tags would execute as HTML in the browser.

**Target implementation (BR-NL-FE-003):** React's JSX text interpolation (`{note.content}`) always creates a DOM text node — it never injects raw HTML. `dangerouslySetInnerHTML` is explicitly prohibited in NoteItem.

```tsx
// CORRECT — React's JSX escapes content automatically:
<p className="note-content">{note.content}</p>
// DOM: <p>O&#39;Brien &amp; &lt;script&gt;alert(1)&lt;/script&gt;</p>
// Renders as visible text, never executes

// WRONG — bypasses React's XSS protection:
<p dangerouslySetInnerHTML={{ __html: note.content }} /> // FORBIDDEN — see BR-NL-FE-003
```

**Validation approach:** Render NoteItem with content `<script>alert("xss")</script>`. Assert `document.querySelector('script')` returns `null`. Assert `screen.getByText('<script>alert("xss")</script>')` finds the element (text node match). No `window.alert` fires.

---

## §7 — Cross-Module Stubs

The frontend depends on the backend API (MWU-NL-001). For test environments where the real backend is unavailable, MSW (Mock Service Worker) intercepts fetch calls in the test runtime. Additionally, a TypeScript stub module is provided for environments that cannot run MSW.

```typescript
// src/api/__stubs__/notesApi.stub.ts
// Use in test environments where the real API is unavailable.
// Import this instead of ../notesApi via Vite alias in test config.

import type { Note, NoteListResponse } from '../../types/note';
import { ApiError } from '../notesApi';

let _notes: Note[] = [
  { id: 2, content: 'Second note', created_at: '2026-05-18T12:00:00Z' },
  { id: 1, content: 'First note', created_at: '2026-05-18T10:00:00Z' },
];
let _nextId = 3;

export { ApiError };

export async function getNotes(): Promise<NoteListResponse> {
  return [..._notes]; // return copy in current order
}

export async function createNote(content: string): Promise<Note> {
  const trimmed = content.trim();
  if (!trimmed) {
    throw new ApiError(422, 'Content cannot be empty');
  }
  if (trimmed.length > 500) {
    throw new ApiError(422, 'Content exceeds maximum length of 500 characters');
  }
  const note: Note = {
    id: _nextId++,
    content: trimmed,
    created_at: new Date().toISOString(),
  };
  _notes = [note, ..._notes]; // prepend — newest first
  return note;
}

export async function deleteNote(id: number): Promise<void> {
  const exists = _notes.some(n => n.id === id);
  if (!exists) {
    // Must throw — never swallow or return undefined silently
    throw new ApiError(404, 'Note not found');
  }
  _notes = _notes.filter(n => n.id !== id);
}

/** Test utility — reset stub state between tests */
export function __resetStub(notes: Note[] = []): void {
  _notes = notes;
  _nextId = Math.max(...notes.map(n => n.id), 0) + 1;
}
```

**Stub contract rules:**
- Every method that can fail in the real API must throw `ApiError` with the correct status — never `return null` or `return undefined` silently
- `deleteNote` on non-existent ID throws `ApiError(404, ...)` — matches RISK-007 handling
- `createNote` with invalid content throws `ApiError(422, ...)` — exercises the 422 code path in AddNoteForm

---

## §8 — Data Migration

**N/A — schema created fresh.**

This MWU owns no database tables and no persistent client-side storage. The React SPA is served as static files with no `localStorage`, `sessionStorage`, or `IndexedDB` usage (no BR requires client-side persistence).

The backend (MWU-NL-001) owns the `notes` table and handles all data migration from the legacy MySQL schema to PostgreSQL. The frontend consumes the migrated data via the REST API — no frontend-layer migration is needed.

---

## §9 — Test Strategy

### 9.1 Test Framework

```
vitest ^1.6             — test runner (Vite-native, ESM-compatible)
@testing-library/react  — component rendering + user interaction
@testing-library/jest-dom — custom DOM matchers (toBeInTheDocument, etc.)
msw ^2.3                — API mocking at the fetch level (no patching)
jsdom ^24               — browser DOM environment for Node.js
```

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
});

// src/test/setup.ts
import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup(); // unmount components after each test
});
```

### 9.2 MSW Server Setup

```typescript
// src/test/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// src/test/setup.ts (extended)
import { server } from './server';
import { beforeAll, afterAll, afterEach } from 'vitest';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

```typescript
// src/test/handlers.ts
import { http, HttpResponse } from 'msw';
import type { Note } from '../types/note';

const defaultNotes: Note[] = [
  { id: 2, content: 'Second note', created_at: '2026-05-18T12:00:00Z' },
  { id: 1, content: 'First note', created_at: '2026-05-18T10:00:00Z' },
];

export const handlers = [
  http.get('http://localhost:8000/notes', () =>
    HttpResponse.json(defaultNotes)
  ),

  http.post('http://localhost:8000/notes', async ({ request }) => {
    const body = await request.json() as { content: string };
    if (!body.content?.trim()) {
      return HttpResponse.json(
        { detail: [{ msg: 'Content cannot be empty', loc: ['body', 'content'], type: 'value_error' }] },
        { status: 422 }
      );
    }
    const note: Note = {
      id: 99,
      content: body.content,
      created_at: '2026-05-19T08:00:00Z',
    };
    return HttpResponse.json(note, { status: 201 });
  }),

  http.delete('http://localhost:8000/notes/:id', ({ params }) => {
    const id = Number(params.id);
    if (id === 9999) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),
];
```

### 9.3 Test Fixtures

```typescript
// src/test/fixtures.ts
import type { Note } from '../types/note';

export const twoNotes: Note[] = [
  { id: 2, content: 'Second note', created_at: '2026-05-18T12:00:00Z' },
  { id: 1, content: 'First note', created_at: '2026-05-18T10:00:00Z' },
];

export const xssNote: Note = {
  id: 99,
  content: '<script>alert("xss")</script>',
  created_at: '2026-05-18T10:00:00Z',
};

export const htmlInjectionNote: Note = {
  id: 100,
  content: '<b>bold</b> & <img src=x onerror="alert(1)">',
  created_at: '2026-05-18T10:00:00Z',
};

export const longContent = 'a'.repeat(500);      // exactly at limit
export const overLimitContent = 'a'.repeat(501); // one char over
export const whitespaceContent = '   ';          // whitespace-only
export const paddedContent = '  hello world  ';  // valid with surrounding spaces
```

### 9.4 Full BR Test Matrix

| BR ID | Test Type | Scenario | Expected Result |
|-------|-----------|----------|----------------|
| BR-NL-FE-001 | Unit (validator) | `validateNoteContent('')` | `{ valid: false, error: "...empty..." }` |
| BR-NL-FE-001 | Unit (validator) | `validateNoteContent('   ')` | `{ valid: false, error: "...empty..." }` |
| BR-NL-FE-001 | Component | Submit form with empty textarea | Inline error rendered; no fetch called |
| BR-NL-FE-001 | Component | Submit form with whitespace-only | Inline error rendered; no fetch called |
| BR-NL-FE-001 | Integration | Server returns 422 | 422 detail shown as inline error |
| BR-NL-FE-002 | Unit (validator) | `validateNoteContent('a'.repeat(500))` | `{ valid: true, error: null }` |
| BR-NL-FE-002 | Unit (validator) | `validateNoteContent('a'.repeat(501))` | `{ valid: false, error: "...500..." }` |
| BR-NL-FE-002 | Unit (counter) | `getRemainingChars('hello')` | `495` |
| BR-NL-FE-002 | Component | Type 500 chars | Counter shows "0 characters remaining" |
| BR-NL-FE-002 | Component | Type 501 chars | Counter shows "1 characters over limit" |
| BR-NL-FE-002 | Component | Submit with 501 chars | Submit button disabled; no fetch called |
| BR-NL-FE-003 | Component | Render note with `<script>` content | No `<script>` in DOM; text node visible |
| BR-NL-FE-003 | Component | Render note with `<b>bold</b>` | Literal text rendered, not bold element |
| BR-NL-FE-003 | Static | Grep for `dangerouslySetInnerHTML` | Zero occurrences in src/ |
| BR-NL-FE-004 | Integration | GET /notes returns `[id:2, id:1]` | List renders id:2 first, id:1 second |
| BR-NL-FE-004 | Component | Add note → prepended to list | New note appears at position 0 |
| BR-NL-FE-004 | Static | Grep for `.sort(` in NoteList | Zero sort calls in component |
| BR-NL-FE-005 | Unit (util) | `formatDate('2026-05-18T10:00:00Z')` | `"18 May 2026"` |
| BR-NL-FE-005 | Unit (util) | `formatDate('2026-01-01T00:00:00Z')` | `"1 Jan 2026"` |
| BR-NL-FE-005 | Unit (util) | `formatDate('2026-12-31T23:59:59Z')` | `"31 Dec 2026"` |
| BR-NL-FE-005 | Component | Render NoteItem with known date | `<time>` element contains "18 May 2026" |
| BR-NL-FE-006 | Integration | Render full App | No login form, no auth provider in DOM |
| BR-NL-FE-006 | Static | Grep for `useAuth`, `PrivateRoute`, `login`, `token` | Zero matches in src/ |
| BR-NL-FE-007 | Integration | Click Delete button | MSW receives `DELETE /notes/2` request |
| BR-NL-FE-007 | Component | Render NoteItem | No `<a>` tag exists in component tree |
| BR-NL-FE-007 | Static | Grep for `href.*delete` in NoteItem | Zero matches |
| BR-NL-FE-008 | Integration | Add note successfully | "Note added successfully." feedback visible |
| BR-NL-FE-008 | Integration | Network error on add | Error feedback visible |
| BR-NL-FE-008 | Integration | Delete note successfully | "Note deleted." feedback visible |
| BR-NL-FE-008 | Integration | Feedback auto-clear | After 4s, feedback element removed from DOM |
| BR-NL-FE-009 | Integration | Render App | Form + list + feedback all on one page |
| BR-NL-FE-009 | Static | Grep for `react-router-dom` | Zero imports in src/ |
| BR-NL-FE-010 | Unit | `prepareContent('  hello  ')` | `"hello"` |
| BR-NL-FE-010 | Unit | `prepareContent('  ')` | `""` (empty — caught by BR-NL-FE-001) |
| BR-NL-FE-010 | Component | Submit `"  hello  "` | `createNote("hello")` called (not "  hello  ") |
| BR-NL-FE-010 | Component | Submit `"O'Brien's note"` | `createNote("O'Brien's note")` — no escaping |
| BR-NL-FE-011 | Integration | API returns 500 | "Server error, please try again." shown |
| BR-NL-FE-011 | Integration | Network failure | "Network error — please check your connection." |
| BR-NL-FE-011 | Integration | DELETE returns 404 | "Note not found — refreshing list." shown; list re-fetched |
| BR-NL-FE-011 | Integration | GET /notes fails on mount | Error feedback shown; empty list state |

### 9.5 Example Test Files

```typescript
// src/validation/noteValidation.test.ts
import { describe, test, expect } from 'vitest';
import {
  validateNoteContent,
  prepareContent,
  getRemainingChars,
  MAX_NOTE_LENGTH,
} from './noteValidation';

describe('validateNoteContent', () => {
  test('BR-NL-FE-001: empty string rejected', () => {
    expect(validateNoteContent('')).toMatchObject({ valid: false });
  });

  test('BR-NL-FE-001: whitespace-only rejected', () => {
    expect(validateNoteContent('   ')).toMatchObject({ valid: false });
  });

  test('BR-NL-FE-002: exactly 500 chars accepted', () => {
    expect(validateNoteContent('a'.repeat(MAX_NOTE_LENGTH))).toEqual({ valid: true, error: null });
  });

  test('BR-NL-FE-002: 501 chars rejected', () => {
    const result = validateNoteContent('a'.repeat(MAX_NOTE_LENGTH + 1));
    expect(result.valid).toBe(false);
    expect(result.error).toContain('500');
  });

  test('BR-NL-FE-001 + BR-NL-FE-010: whitespace around valid content accepted', () => {
    expect(validateNoteContent('  hello  ')).toEqual({ valid: true, error: null });
  });
});

describe('prepareContent', () => {
  test('BR-NL-FE-010: trims leading and trailing whitespace', () => {
    expect(prepareContent('  hello world  ')).toBe('hello world');
  });

  test('BR-NL-FE-010 / RISK-002: does not escape special characters', () => {
    expect(prepareContent("O'Brien's & <script>")).toBe("O'Brien's & <script>");
  });
});

describe('getRemainingChars', () => {
  test('BR-NL-FE-002: 5 chars typed → 495 remaining', () => {
    expect(getRemainingChars('hello')).toBe(495);
  });

  test('BR-NL-FE-002: 501 chars typed → -1 remaining', () => {
    expect(getRemainingChars('a'.repeat(501))).toBe(-1);
  });
});
```

```typescript
// src/utils/dateUtils.test.ts
import { describe, test, expect } from 'vitest';
import { formatDate } from './dateUtils';

describe('formatDate', () => {
  test('BR-NL-FE-005: ISO 8601 → "D Mon YYYY"', () => {
    expect(formatDate('2026-05-18T10:00:00Z')).toBe('18 May 2026');
  });

  test('BR-NL-FE-005: first day of year', () => {
    expect(formatDate('2026-01-01T00:00:00Z')).toBe('1 Jan 2026');
  });

  test('BR-NL-FE-005: last day of year', () => {
    expect(formatDate('2026-12-31T12:00:00Z')).toBe('31 Dec 2026');
  });

  test('BR-NL-FE-005: single-digit day has no leading zero', () => {
    expect(formatDate('2026-05-01T10:00:00Z')).toBe('1 May 2026');
  });
});
```

```typescript
// src/components/NoteItem.test.tsx
import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NoteItem from './NoteItem';
import { xssNote, htmlInjectionNote } from '../test/fixtures';
import type { Note } from '../types/note';

const testNote: Note = {
  id: 1,
  content: 'Test note content',
  created_at: '2026-05-18T10:00:00Z',
};

describe('NoteItem', () => {
  test('BR-NL-FE-003: renders content as plain text', () => {
    render(
      <NoteItem note={testNote} onDelete={vi.fn()} onError={vi.fn()} onSuccess={vi.fn()} />
    );
    expect(screen.getByText('Test note content')).toBeInTheDocument();
  });

  test('BR-NL-FE-003: XSS content renders as text node, not HTML', () => {
    render(
      <NoteItem note={xssNote} onDelete={vi.fn()} onError={vi.fn()} onSuccess={vi.fn()} />
    );
    expect(document.querySelector('script')).toBeNull();
    expect(screen.getByText('<script>alert("xss")</script>')).toBeInTheDocument();
  });

  test('BR-NL-FE-003: HTML injection renders as text, not elements', () => {
    render(
      <NoteItem note={htmlInjectionNote} onDelete={vi.fn()} onError={vi.fn()} onSuccess={vi.fn()} />
    );
    expect(document.querySelector('img')).toBeNull();
    expect(document.querySelector('b')).toBeNull();
  });

  test('BR-NL-FE-005: displays formatted date', () => {
    render(
      <NoteItem note={testNote} onDelete={vi.fn()} onError={vi.fn()} onSuccess={vi.fn()} />
    );
    expect(screen.getByText('18 May 2026')).toBeInTheDocument();
  });

  test('BR-NL-FE-007: no anchor tags in render', () => {
    render(
      <NoteItem note={testNote} onDelete={vi.fn()} onError={vi.fn()} onSuccess={vi.fn()} />
    );
    expect(document.querySelectorAll('a')).toHaveLength(0);
  });

  test('BR-NL-FE-007: delete button triggers HTTP DELETE', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <NoteItem note={testNote} onDelete={onDelete} onError={vi.fn()} onSuccess={vi.fn()} />
    );
    await user.click(screen.getByRole('button', { name: /delete/i }));
    expect(onDelete).toHaveBeenCalledWith(testNote.id);
  });
});
```

```typescript
// src/components/AddNoteForm.test.tsx
import { describe, test, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AddNoteForm from './AddNoteForm';

const noop = (): void => { /* no-op */ };

describe('AddNoteForm', () => {
  test('BR-NL-FE-001: rejects empty submission', async () => {
    const user = userEvent.setup();
    const onNoteAdded = vi.fn();
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={noop} onSuccess={noop} />);

    await user.click(screen.getByRole('button', { name: /add note/i }));

    expect(screen.getByRole('alert')).toHaveTextContent('Note content cannot be empty.');
    expect(onNoteAdded).not.toHaveBeenCalled();
  });

  test('BR-NL-FE-001: rejects whitespace-only submission', async () => {
    const user = userEvent.setup();
    render(<AddNoteForm onNoteAdded={vi.fn()} onError={noop} onSuccess={noop} />);

    await user.type(screen.getByRole('textbox'), '   ');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  test('BR-NL-FE-002: character counter updates on input', async () => {
    const user = userEvent.setup();
    render(<AddNoteForm onNoteAdded={vi.fn()} onError={noop} onSuccess={noop} />);

    await user.type(screen.getByRole('textbox'), 'hello');
    expect(screen.getByText(/495 characters remaining/)).toBeInTheDocument();
  });

  test('BR-NL-FE-010: trims whitespace before sending to API', async () => {
    const user = userEvent.setup();
    const onNoteAdded = vi.fn();
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={noop} onSuccess={noop} />);

    await user.type(screen.getByRole('textbox'), '  hello  ');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(onNoteAdded).toHaveBeenCalled());
    const addedNote = onNoteAdded.mock.calls[0][0] as { content: string };
    expect(addedNote.content).toBe('hello'); // MSW echo's the sent content
  });

  test('BR-NL-FE-008: clears form after successful submission', async () => {
    const user = userEvent.setup();
    render(<AddNoteForm onNoteAdded={vi.fn()} onError={noop} onSuccess={noop} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'a valid note');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(textarea).toHaveValue(''));
  });
});
```

### 9.6 Test Coverage Requirements

- All 11 BR IDs must have at least one passing test
- BR-NL-FE-001 and BR-NL-FE-002 each require both a happy-path test and at least two rejection tests
- RISK-003 (CSRF): assert HTTP method is `DELETE` in network layer; assert no `<a>` elements in NoteItem
- RISK-008 (XSS): DOM inspection test asserting no `<script>` or `<img onerror>` elements rendered
- `validateNoteContent` and `prepareContent` must be tested as pure functions — no component rendering in unit tests
- No mocking of validation functions in component tests — test through the real validator to catch integration gaps
- Static analysis (grep) tests for BR-NL-FE-003, BR-NL-FE-006, BR-NL-FE-007, BR-NL-FE-009 can be enforced via CI lint rules or a small test script asserting zero matches

---

*End of Planning Document — MWU-NL2-002-FE frontend*
*Total BRs covered: 11 / 11*
*Sections complete: §1–§9*




---
# COMPREHENSION ANALYSIS

﻿# Comprehension Report — MWU-NL-002-FE Frontend (React)
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-18
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (2 source files, complexity LOW)
**Rules extracted:** 11 frontend business rules
**MKB artifacts stored:** 11 UUIDs
**Backend BRs referenced (not re-extracted):** 7 (BR-NL-001 through BR-NL-007, MWU-NL-001)

---

## 1. Business Rule Catalog

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-NL-FE-001 | Client-side content validation — reject empty/whitespace-only content before submission with inline error | VALIDATION | index.php:94, :23-26 | HIGH | None | 942c6e26-9098-4da3-b007-870b6d854361 |
| BR-NL-FE-002 | Client-side content length validation — max 500 chars with visible character counter | VALIDATION | index.php:94, :4, :27-29 | HIGH | None | 621ee415-2649-4bf3-ac2b-0600b128bc53 |
| BR-NL-FE-003 | Output escaping — render note content as text only, never dangerouslySetInnerHTML | CONSTRAINT | index.php:85,88,96,107 | HIGH | None | 9f845da3-955d-4466-857c-b3d766622833 |
| BR-NL-FE-004 | Note display order preserved from API (newest first) — do not re-sort | CONSTRAINT | index.php:11 | MEDIUM | None | ccd0a475-1381-4c24-9afc-45ec91f1af10 |
| BR-NL-FE-005 | Date formatting in frontend — API returns ISO 8601, display as "18 May 2026" | TRANSFORMATION | index.php:108 | MEDIUM | None | fc9dfc5f-b1e8-476f-b1cc-666d21b2eb80 |
| BR-NL-FE-006 | No authentication UI — no login, no auth state, no protected routes [CRITICAL] | AUTHORIZATION | index.php (no auth) | CRITICAL | None | b041ce2d-bde1-47d2-9fcc-31bd29e431ef |
| BR-NL-FE-007 | Delete via HTTP DELETE method, not GET — fix CSRF anti-pattern | WORKFLOW | index.php:48-55 | HIGH | None | e6bb3eac-bce7-443b-9ca8-6736a0ede7ff |
| BR-NL-FE-008 | Inline success/error feedback after add/delete operations | WORKFLOW | index.php:69-120 | MEDIUM | None | b206f5f8-0620-41e7-bb5d-b641a6295e08 |
| BR-NL-FE-009 | Single-page layout — all functionality on one page, no routing needed | CONSTRAINT | index.php:69-120 | MEDIUM | None | aaedf7bc-0108-4cbc-8097-9a379932ab7c |
| BR-NL-FE-010 | Trim whitespace from content before submission (mirrors server-side trim) | TRANSFORMATION | index.php:23 | MEDIUM | None | 25dc2cef-79b3-4eb7-b361-164cb55d22a5 |
| BR-NL-FE-011 | Graceful handling of API errors — 422, 404, 5xx, network failures | WORKFLOW | discovery Section 10 | HIGH | None | 459ae16f-9088-4b84-873f-0e0082a9b5ef |

### Backend BRs Referenced (from MWU-NL-001 — not re-extracted)

| Backend BR | Frontend Relevance | Frontend Mirror |
|------------|-------------------|-----------------|
| BR-NL-001 (content not empty) | Client-side pre-validation | BR-NL-FE-001 |
| BR-NL-002 (max 500 chars) | Client-side length enforcement | BR-NL-FE-002 |
| BR-NL-004 (newest first order) | Display order contract | BR-NL-FE-004 |
| BR-NL-005 (no auth — CRITICAL) | No auth UI | BR-NL-FE-006 |
| BR-NL-006 (trim whitespace) | Pre-submission trim | BR-NL-FE-010 |
| BR-NL-007 (silent delete vs 404) | Error handling for 404 | BR-NL-FE-011 |

---

## 2. Implementation Notes for CodeGen Agent

### RISK-002: RAW-SQL-CONCAT — SQL Injection in add_note
**What to do:** Frontend concern is minimal — the API handles parameterized queries. However, the frontend MUST NOT attempt to sanitize or escape content before sending to the API. Send raw user input (after trim). The API/ORM handles SQL safety.
**Pattern to use:** `fetch('/notes', { method: 'POST', body: JSON.stringify({ content: trimmedContent }) })`
**Do NOT:** Pre-escape HTML entities, SQL characters, or special characters before sending to API. That corrupts the data.

### RISK-003: CSRF — DELETE via GET
**What to do:** Use HTTP DELETE method for delete operations. Use a `<button>` element, never an `<a href>` link. Include proper Content-Type headers.
**Pattern to use:** `fetch(\`/notes/\${id}\`, { method: 'DELETE' })` triggered by button onClick handler.
**Do NOT:** Use anchor tags for destructive actions. Do not use GET requests for state-changing operations. Do not embed delete IDs in URL query parameters.

### RISK-005: Unbounded SELECT — No Pagination
**What to do:** The API currently returns all notes. Frontend should render all notes from the response. If pagination is added to the API later, the frontend structure (list component mapping over an array) will naturally accommodate it.
**Pattern to use:** `notes.map(note => <NoteItem key={note.id} note={note} />)` — works for any array length.
**Do NOT:** Implement client-side pagination or virtual scrolling unless the dataset grows large enough to warrant it. Over-engineering for a simple note list.

### RISK-006: Server-side Date Formatting
**What to do:** API returns ISO 8601 timestamps. Format dates in the React component using browser Intl APIs.
**Pattern to use:** `new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(note.created_at))` → "18 May 2026"
**Do NOT:** Import moment.js or other heavy date libraries. Do not request pre-formatted dates from the API. Do not use Date.toLocaleDateString() without explicit locale (inconsistent across browsers).

### RISK-007: Silent Delete of Non-existent ID
**What to do:** The API may return 404 for a delete of a non-existent note (pending NEEDS_VALIDATION on BR-NL-007). Frontend must handle both cases: (a) 200 success → remove note from list, show "Note deleted"; (b) 404 not found → show "Note not found", refresh the list to sync state.
**Pattern to use:** Check `response.status` after DELETE call. Handle 200 and 404 as distinct UX paths.
**Do NOT:** Assume delete always succeeds. Do not ignore the response status.

---

## 3. Ambiguities Requiring SME Resolution

No ambiguities — all frontend rules are unambiguous from source.

The one backend ambiguity (BR-NL-007: silent delete vs 404) affects frontend error handling (BR-NL-FE-011) but the frontend implementation handles both outcomes. No frontend-specific SME decisions are needed.

---

## 4. Cross-Module Dependencies

| BR ID | Depends on | Module | Status |
|-------|-----------|--------|--------|
| BR-NL-FE-001 | BR-NL-001 (server-side empty validation) | backend | EXTRACTED |
| BR-NL-FE-002 | BR-NL-002 (server-side length validation, MAX_NOTE_LENGTH=500) | backend | EXTRACTED |
| BR-NL-FE-004 | BR-NL-004 (API sort order guarantee) | backend | EXTRACTED |
| BR-NL-FE-006 | BR-NL-005 (no auth — CRITICAL) | backend | EXTRACTED |
| BR-NL-FE-007 | Backend DELETE /notes/{id} endpoint must exist | backend | EXTRACTED |
| BR-NL-FE-010 | BR-NL-006 (server-side trim) | backend | EXTRACTED |
| BR-NL-FE-011 | Backend API error response format (422/404/5xx) | backend | EXTRACTED |

**Dependency direction:** Frontend depends on backend API contract. Backend (MWU-NL-001) should be code-generated first. Frontend can proceed once API endpoint signatures and error response format are defined.

---

## 5. MKB Storage Summary

Total rules stored: 11
MKB project: NOTE-LIST-1
MKB module: .
Status: EXTRACTED (pending HITL validation)

UUIDs:
- BR-NL-FE-001: 942c6e26-9098-4da3-b007-870b6d854361
- BR-NL-FE-002: 621ee415-2649-4bf3-ac2b-0600b128bc53
- BR-NL-FE-003: 9f845da3-955d-4466-857c-b3d766622833
- BR-NL-FE-004: ccd0a475-1381-4c24-9afc-45ec91f1af10
- BR-NL-FE-005: fc9dfc5f-b1e8-476f-b1cc-666d21b2eb80
- BR-NL-FE-006: b041ce2d-bde1-47d2-9fcc-31bd29e431ef
- BR-NL-FE-007: e6bb3eac-bce7-443b-9ca8-6736a0ede7ff
- BR-NL-FE-008: b206f5f8-0620-41e7-bb5d-b641a6295e08
- BR-NL-FE-009: aaedf7bc-0108-4cbc-8097-9a379932ab7c
- BR-NL-FE-010: 25dc2cef-79b3-4eb7-b361-164cb55d22a5
- BR-NL-FE-011: 459ae16f-9088-4b84-873f-0e0082a9b5ef

To retrieve for CodeGen:
  mkb_get_business_rules(module=".", project_id="NOTE-LIST-1", status="VALIDATED")

---

## 6. Reviewer Checklist

- [x] All frontend-relevant BRs from discovery Section 7 are captured (7→6 mirrored as FE rules)
- [x] UI/Controller layer concerns from Section 4 are captured (XSS, CSRF, flash messages, layout)
- [x] Each BR has a clear, implementation-ready description with React-specific patterns
- [x] Risk register items (RISK-002, 003, 005, 006, 007) translated to CodeGen instructions in Section 2
- [x] No ambiguities requiring SME resolution for frontend
- [x] All 11 MKB UUIDs recorded for traceability
- [x] Cross-module dependencies on backend API contract identified
- [x] Backend BRs referenced but not re-extracted (avoiding duplication)
- [x] CRITICAL constraint BR-NL-FE-006 (no auth UI) prominently flagged
- [x] Pipeline lesson applied: verified MKB tools active, all BRs stored (not PENDING_MKB_WRITE)

---

## 7. React Component Architecture (CodeGen Guidance)

Based on BR-NL-FE-009 (single-page layout), the recommended component tree:

```
App
├── Header (app title)
├── FeedbackMessage (BR-NL-FE-008: success/error inline messages)
├── AddNoteForm (BR-NL-FE-001, 002, 010: validation + trim + char counter)
│   ├── textarea (maxLength=500, char counter)
│   └── submit button
├── NoteList (BR-NL-FE-004: render in API order)
│   └── NoteItem[] (BR-NL-FE-003: text-only render, BR-NL-FE-005: formatted date)
│       ├── note content (text, not HTML)
│       ├── formatted created_at date
│       └── delete button (BR-NL-FE-007: HTTP DELETE)
└── Footer

API layer: single api.js/ts module
  - getNotes()     → GET /notes
  - createNote()   → POST /notes
  - deleteNote(id) → DELETE /notes/{id}
  All with error handling per BR-NL-FE-011
```

No React Router. No state management library (useState sufficient). No auth provider.




======================================================================
## APPROVED EXEMPLARS
======================================================================

## Approved Code Exemplars

The following are approved, production-ready examples from this same migration project. Study the patterns, naming conventions, error handling, and code structure — replicate them in your output.

### Exemplar from MWU-NL2-001 (notes/service.py)

```python
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notes.models import Note


class NoteService:
    """Business logic layer for note operations.

    Receives a pre-configured AsyncSession from the DI layer.
    Never constructs its own session or engine.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # list_notes
    # BRs: BR-BACKEND-005 (ORDER BY created_at DESC), BR-BACKEND-008 (no LIMIT)
    # Transaction: read-only — no commit needed
    # ------------------------------------------------------------------
    async def list_notes(self) -> list[Note]:
        """Return all notes ordered newest-first.

        BR-BACKEND-005: ORDER BY created_at DESC — only supported sort.
        BR-BACKEND-008: No LIMIT / OFFSET — all rows returned.
        """
        result = await self._db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # create_note
    # BRs: BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-006 enforced upstream
    #      by NoteCreate schema before this method is called.
    # Transaction: single INSERT + commit
    # ------------------------------------------------------------------
    async def create_note(self, content: str) -> Note:
        """Persist a new note and return the persisted ORM instance.

        Precondition: content has already been stripped and validated
        by NoteCreate (BR-001 empty check, BR-002 length check, BR-006 strip).
        This method does NOT re-validate — it trusts the schema layer.

        Uses flush() + refresh() to populate DB-assigned id and created_at
        before commit, so the returned Note is fully hydrated.
        """
        note = Note(content=content)
        self._db.add(note)
        await self._db.flush()     # assigns id and created_at via DB defaults
        await self._db.refresh(note)
        await self._db.commit()
        return note

    # ------------------------------------------------------------------
    # delete_note
    # BRs: BR-BACKEND-003 (gt=0 enforced at router layer before this call)
    #      BR-BACKEND-007 (404 when rowcount == 0)
    # Transaction: single DELETE + commit (only if row found)
    # ------------------------------------------------------------------
    async def delete_note(self, note_id: int) -> None:
        """Delete a note by primary key.

        BR-BACKEND-003: note_id is guaranteed > 0 by the router Path(..., gt=0).
        BR-BACKEND-007: raises HTTP 404 if no row was deleted (legacy changed to
          correct REST behaviour — pending SME confirmation per comprehension doc).
        """
        result = await self._db.execute(
            delete(Note).where(Note.id == note_id)
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )
        await self._db.commit()
```


======================================================================
## SUPPORTING CONTEXT
======================================================================

## sonar-issues
{
  "module": "frontend",
  "sonar_path": "frontend",
  "total": 0,
  "by_severity": {},
  "top_issues": []
}


======================================================================
## SIBLING MODULE SUMMARIES
======================================================================

## Sibling Module Summaries

Brief context on related modules already migrated:

**backend:** # Comprehension Report — MWU-NL2-001 Backend
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-19
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (4 source files, complexity LOW)
**Rules extracted:** 8 business rules
**MKB artifacts stored:** 8 UUIDs (pre-existing from 2026-05-18 session — verified, not duplicated)

---

## 1. Business Rule Catalog

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|---------...