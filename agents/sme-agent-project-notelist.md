# SME Agent Project Layer — Note-List-Leg1

## Domain
Minimal note list application specialist
Simple CRUD operations, no authentication, single-table design
PHP to Python migration for basic applications

## Key Validations
1. Note content validation (non-empty, length limits)
2. ID validation (invalid ID handling)
3. No authentication present (critical requirement)
4. Simple error responses
5. Basic CRUD completeness

## Known Issues to Validate
- Empty content: confirm rejection behavior
- Length limit: confirm 500 character limit
- Invalid IDs: confirm 404 vs 500 responses
- No auth: confirm no authentication exists

## Escalation Triggers (RED FLAGS)
- Any require_permission() in generated code
- Any user authentication/authorization
- Session management code
- JWT or token handling
- User-scoped data (notes belong to users)

## Output Format
STATUS: VALIDATED | NEEDS_CLARIFICATION | INCORRECT
NOTES: explanation
CORRECTION: (if INCORRECT) correct rule

## Critical Reminder
This is a PUBLIC note-taking app. Any authentication features are wrong.
Escalate immediately if auth patterns appear in generated code.