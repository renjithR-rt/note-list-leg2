## STEP 0 — Query Pipeline Lessons (MANDATORY, run before anything else)

Before generating frontend code, query the shared lessons KB:

  mkb_query_semantic(
    query="React codegen common errors",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )
  mkb_query_semantic(
    query="frontend self-review failures",
    project_id="PIPELINE-LESSONS",
    top_k=3,
    min_similarity=0.3
  )

For each result with similarity > 0.3:
  Read the lesson content
  Apply it to your current task
  If it flags a known failure pattern — actively check for it

---

# Frontend Codegen Agent — Note-List-Leg1

## CRITICAL OUTPUT CONSTRAINT
Output: .jsx files ONLY — ZERO .py files allowed
Source is index.php HTML structure — translate to React components

## HARD RULE: Frontend File Check
If about to write .py files → STOP → re-read this file
This is FRONTEND-ONLY generation, not backend

## Components Required
- AddNote: textarea + submit button for new notes
- NoteList: display all notes in list format
- NoteCard: individual note display with delete button

## API Integration
- GET /notes: fetch all notes
- POST /notes: create new note
- DELETE /notes/{id}: delete note
- Base URL via Vite proxy to http://localhost:8000

## Form Structure
- Single textarea for note content
- Character counter (500 max)
- Submit button (disabled if empty or over limit)
- Simple validation feedback

## Note List Pattern
- Simple ul/li structure or card layout
- Note content display (truncated if long)
- Delete button/link for each note
- Created/updated timestamps if available

## Error/Success Patterns
- Success: green alert/toast after create/delete
- Error: red alert for validation or API errors
- Loading states: simple spinners or disabled buttons

## No Authentication UI
- No login forms
- No user menus
- No permission checks
- All functionality public and accessible