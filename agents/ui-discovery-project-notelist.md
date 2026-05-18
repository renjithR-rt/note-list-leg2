## STEP 0 — Query Pipeline Lessons (MANDATORY, run before anything else)

Before analyzing UI structure, query the shared lessons KB:

  mkb_query_semantic(
    query="UI discovery PHP extraction errors",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )

For each result with similarity > 0.3:
  Read the lesson content
  Apply it to your current task
  If it flags a known failure pattern — actively check for it

---

# UI Discovery Project Layer — Note-List-Leg1

## Source Scope
Extract UI patterns from HTML rendering section of index.php:
- Form structure (textarea + submit)
- Note list layout (ul/li or table)
- Delete link patterns
- Error/success alert structure

## Focus Areas

### Form Structure
- Textarea for note content entry
- Submit button styling and placement
- Form validation display patterns
- Character limit indicators (if present)

### Note List Layout
- How notes are displayed (table, list, cards)
- Note content formatting and truncation
- Delete action placement and styling
- Empty state handling

### Delete Link Pattern
- Button vs link styling for delete actions
- Confirmation patterns (if any)
- Delete success/error feedback

### Alert/Message Structure
- Success message styling and placement
- Error message styling and placement
- Validation feedback patterns

## Extract Targets
- Form layout -> React form component
- Note display -> React NoteCard component
- List structure -> React NoteList component
- Message patterns -> React alert components

## Ignore
- PHP business logic (backend concern)
- Database queries (backend concern)  
- Server-side validation (backend responsibility)
- Authentication UI (doesn't exist in source)