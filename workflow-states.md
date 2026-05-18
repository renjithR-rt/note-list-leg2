# Workflow Server — Complete State Machine

## Happy Path (normal pipeline run)
PENDING → DISCOVERY_RUNNING → DISCOVERY_HITL → DISCOVERY_APPROVED
→ COMPREHENSION_RUNNING → COMPREHENSION_HITL → COMPREHENSION_APPROVED
→ BR_DOC_PENDING → BR_DOC_GENERATING → BR_DOC_REVIEW_WAITING → BR_DOC_APPROVED
→ PLANNING_RUNNING → PLANNING_HITL → PLANNING_APPROVED
→ CONTEXT_ASSEMBLY → GENERATING → PRE_HITL_VALIDATION → SELF_REVIEW
→ HUMAN_REVIEW → TESTING → TEST_PASSED → FULLY_VALIDATED ← SHORTCUT

## Full validation chain (if TEST_PASSED → MERGED used instead)
TEST_PASSED → MERGED → UNIT_VALIDATED → INTEGRATION_VALIDATED
→ GOLDEN_VALIDATED → DUAL_RUN_VALIDATED → FULLY_VALIDATED

## Reset targets
| Want to rerun | Reset to |
|---|---|
| Everything | PENDING |
| From comprehension | DISCOVERY_APPROVED |
| From planning | COMPREHENSION_APPROVED |
| From codegen | PLANNING_APPROVED |
| Tests only | APPROVED |

## Error states
TEST_FAILED → TESTING (retry) or PENDING (full reset)
BLOCKED → PENDING (full reset)
INTEGRATION_DEFECT → APP_INTEGRATION (retry) or REVISION (fix code)

## Actions endpoints (preferred over transition_mwu for HITL gates)
POST /actions/approve-discovery    {mwu_id, project_id}
POST /actions/approve-comprehension
POST /actions/approve-planning
POST /actions/approve-hitl         ← HUMAN_REVIEW gate
POST /actions/approve-br-doc
POST /actions/reset-to-pending     {mwu_id, project_id}
POST /actions/reset-to-approved    {mwu_id, project_id}
POST /actions/run-tests            {mwu_id, project_id}
