## ⚡ EXECUTION ENVIRONMENT — READ BEFORE RUNNING ANYTHING

Shell: PowerShell ONLY — never bash, never sh, never zsh
Path separator: backslash (E:\Claude\...) — never forward slash in Set-Location
Chain commands with ; not &&
Never use /usr/bin/bash or unix-style paths on Windows

Script directory for all Python tools:
  E:\Claude\task-man-leg1\engine\pipeline-controller\   (task-man session)
  E:\Claude\note-list-leg1\engine\pipeline-controller\  (note-list session)

Activate venv before any python command:
  .venv\Scripts\activate

## ⚡ LOOKUP PROTOCOL — RUN BEFORE READING ANY FILE

Step 1 — Check known fixes:
  cd E:\Claude\<engagement>\engine\pipeline-controller
  .venv\Scripts\activate
  python lesson.py --query "describe the problem"

Step 2 — Find exact file and line:
  python index_pipeline_code.py --query "describe the problem"
  Read ONLY the returned line range — never the full file

Step 3 — Exact pattern search:
  Select-String "pattern" (Get-ChildItem . -Recurse -Filter "*.py").FullName

Step 4 — Fix → re-index → store lesson:
  python index_pipeline_code.py --file controller/nodes.py --force
  python index_pipeline_code.py --export-md
  python lesson.py

NEVER: Read entire nodes.py, orchestrator.py, or preflight.py
ALWAYS: index query first → line number → read 30-40 lines only

---

## ⚡ RE-INDEX RULE — AFTER EVERY ENGINE FILE CHANGE

After fixing ANY engine file, re-index it before next pipeline run:

  python index_pipeline_code.py --file <changed_file> --force
  python index_pipeline_code.py --export-md

Examples:
  python index_pipeline_code.py --file preflight.py --force
  python index_pipeline_code.py --file orchestrator.py --force
  python index_pipeline_code.py --file controller/nodes.py --force
  python index_pipeline_code.py --file controller/github_pr.py --force

Stale index = wrong line numbers = agents read wrong code = wasted tokens.

## ⚡ INDEX COVERAGE — FILES THAT MUST BE INDEXED

These files are queried most often — verify they appear in index results:
  preflight.py          ← PROJECT_ID loading, MWU check, strategy checks
  orchestrator.py       ← project_id flag, preflight call, worker loop
  controller/nodes.py   ← all agent nodes, agent layer paths
  controller/config.py  ← all config variables and defaults
  controller/github_pr.py ← PR creation, branch management
  controller/graph.py   ← state machine routing

Check coverage:
  python index_pipeline_code.py --query "load_config preflight PROJECT_ID"
  # Must return preflight.py — if not, run --file preflight.py --force

## ⚡ DEBUGGING RULE — NEVER GREP BLINDLY

When debugging an engine error:

  1. python lesson.py --query "error description"
     → similarity > 0.5: known fix exists, follow it

  2. python index_pipeline_code.py --query "error description"
     → get exact file + line number
     → read ONLY those 20-30 lines

  3. For dynamic error messages (f-strings), search for the
     STATIC FRAGMENT not the full assembled string:
     Bad:  Select-String "MWU MWU-NL2-001 not found" file.py
     Good: Select-String "not found" file.py | Select-String "FAIL\|Status"

  4. When line number is known — read directly:
     Get-Content "file.py" | Select-Object -Skip ($linenum-1) -First 25

  5. Fix → re-index → add lesson → commit

---

# Note List Migration
project_id: NOTE-LIST-1
Legacy: PHP 5.6 single-file app -> FastAPI + React + PostgreSQL

source/   <- submodule: note-list (READ-ONLY)
engine/   <- submodule: migration-pipeline
agents/   <- NOTE-LIST-1-context.md
output/   <- all generated code

Run:
  cd E:\Claude\note-list-leg1\engine\pipeline-controller
  .venv\Scripts\activate
  python preflight.py
  python orchestrator.py --mwu-id MWU-NL-001 --poll-interval 30
  python orchestrator.py --mwu-id MWU-NL-002-FE --poll-interval 30

Legacy:     http://localhost:8094
Dashboard:  http://localhost:8766/dashboard/index.html

MWUs:
  MWU-NL-001      .  LOW  BACKEND   -> FastAPI (extract logic from index.php)
  MWU-NL-002-FE   .  LOW  FRONTEND  -> React   (extract UI from index.php)

