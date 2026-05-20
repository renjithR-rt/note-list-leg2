# Planning Document — MWU-NL2-002-FE frontend
**Phase:** Planning
**MWU Tier:** LOW
**Date:** 2026-05-20
**Source stack:** PHP 5.6 (single-file, server-rendered)
**Target stack:** React 18 + TypeScript + Vite SPA
**Business Rules:** 15 rules (from comprehension BR catalog)
**Dependencies:** MWU-NL2-001 (FastAPI backend)

---

## §1 — Target Data Model (DDL)

The frontend module owns no database tables. DDL is owned exclusively by MWU-NL2-001 (backend). This section provides the canonical TypeScript type definitions that serve as the frontend's data model contract. Every component, hook, and service function must use these interfaces — no `any` types, no inline object-literal types.

```typescript
// src/types/note.ts

/** Mirrors backend NoteRead Pydantic schema (MWU-NL2-001) */
export interface Note {
  id: number;           // positive integer, PK
  content: string;      // 1–500 chars, trimmed by backend (BR-BACKEND-003)
  created_at: string;   // ISO 8601 UTC string from API (e.g. "2026-05-20T10:00:00Z")
}

/** Mirrors backend NoteCreate Pydantic schema (MWU-NL2-001) */
export interface NoteCreate {
  content: string;      // client sends raw input; backend trims + validates
}

/** FastAPI HTTPException error envelope */
export interface ApiError {
  detail: string | ValidationErrorItem[];
}

/** Pydantic 422 validation error detail item */
export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}
```

These types are derived directly from the backend's Pydantic schemas. Any change to the backend `NoteRead` or `NoteCreate` schema (MWU-NL2-001) requires a corresponding update here.

---

## §2 — Target ORM / Data Access Models

The frontend has no ORM. This section defines the React component tree, application state shape, and the data access architecture that parallels the ORM layer on the backend.

### 2.1 Component Tree

```
App                         ← state owner, orchestrates all API calls
├── <nav> brand             (BR-FRONTEND-010)
├── AlertBanner             (BR-FRONTEND-006) — rendered conditionally
├── NoteForm                (BR-FRONTEND-001, 004, 014)
│   ├── <textarea maxLength=500>
│   └── <button disabled={submitting}>
├── NoteList                (BR-FRONTEND-005, 009, 012)
│   └── NoteCard[]          (BR-FRONTEND-002, 003, 008)
│       ├── <p>{content}</p>          ← JSX escaping (BR-FRONTEND-008)
│       ├── <time>{formatDate(...)}</time>  ← en-GB (BR-FRONTEND-003)
│       └── <button>Delete</button>   ← triggers confirm (BR-FRONTEND-002)
└── <footer> copyright      (BR-FRONTEND-011)
```

### 2.2 Application State Shape

```typescript
// src/types/state.ts

export type AlertType = 'error' | 'success' | null;

export interface AppState {
  notes: Note[];               // API-returned order, newest first (BR-FRONTEND-009)
  loading: boolean;            // true while initial GET /notes is in flight
  submitting: boolean;         // true while POST /notes is in flight (BR-FRONTEND-014)
  alertType: AlertType;        // mutually exclusive with other alert (BR-FRONTEND-006)
  alertMessage: string | null; // null when no alert shown
  formContent: string;         // textarea value — preserved on error (BR-FRONTEND-004)
}
```

### 2.3 State Transition Table

| Trigger | State mutation |
|---------|---------------|
| App mount | `loading=true` → `fetchNotes()` → `notes=data, loading=false` |
| User types in textarea | `formContent=value` |
| Submit pressed | `submitting=true` (button disables — BR-FRONTEND-014) |
| POST success | `submitting=false`, `alertType='success'`, `alertMessage='Note added.'`, `formContent=''`, refetch notes |
| POST failure | `submitting=false`, `alertType='error'`, `alertMessage=extracted`, `formContent` **unchanged** (BR-FRONTEND-004) |
| Delete pressed | `window.confirm` → cancelled: no-op; confirmed: `fetch DELETE` → refetch notes |
| DELETE failure | `alertType='error'`, `alertMessage=extracted` |
| New alert triggered | Replaces previous alert state (mutual exclusion — BR-FRONTEND-006) |

### 2.4 File Structure

```
src/
├── main.tsx                      # Vite entry point — renders <App /> into #root
├── App.tsx                       # Root component, owns all state
├── types/
│   ├── note.ts                   # Note, NoteCreate, ApiError, ValidationErrorItem
│   └── state.ts                  # AppState, AlertType
├── services/
│   └── noteService.ts            # fetchNotes, createNote, deleteNote, extractErrorMessage, validateNoteCreate
├── utils/
│   └── formatDate.ts             # formatDate(iso: string): string — BR-FRONTEND-003
├── components/
│   ├── AlertBanner.tsx           # BR-FRONTEND-006
│   ├── NoteForm.tsx              # BR-FRONTEND-001, 004, 014
│   ├── NoteList.tsx              # BR-FRONTEND-005, 009, 012
│   └── NoteCard.tsx              # BR-FRONTEND-002, 003, 008
├── test/
│   ├── setup.ts                  # Vitest globals + MSW server setup
│   ├── fixtures/
│   │   └── notes.ts              # sampleNotes, xssNote, edgeDateNote
│   ├── mocks/
│   │   ├── handlers.ts           # MSW request handlers
│   │   └── server.ts             # MSW Node server
│   ├── unit/
│   │   ├── formatDate.test.ts
│   │   └── extractErrorMessage.test.ts
│   └── components/
│       ├── AlertBanner.test.tsx
│       ├── NoteForm.test.tsx
│       ├── NoteList.test.tsx
│       ├── NoteCard.test.tsx
│       └── App.integration.test.tsx
├── index.css                     # Bootstrap 5 import + minimal overrides
└── vite-env.d.ts
```

---

## §3 — Validation Schemas / DTOs

The frontend validation layer uses TypeScript type guards and runtime checks aligned with the backend Pydantic schemas. No external validation library (Zod, Yup) is needed — native HTML attributes plus lightweight runtime checks are sufficient for this simple form.

### 3.1 NoteCreate Input Validation

```typescript
// src/services/noteService.ts — validateNoteCreate()

/**
 * BR-FRONTEND-001: enforces maxlength=500 as a pre-flight client check
 * (UX aid — server is authoritative via BR-BACKEND-002).
 * Also mirrors BR-BACKEND-001: empty content rejected before network call.
 *
 * Returns null if valid, or an error string if invalid.
 */
export function validateNoteCreate(content: string): string | null {
  const trimmed = content.trim();
  if (trimmed.length === 0) return 'Note cannot be empty.';       // BR-BACKEND-001 mirror
  if (trimmed.length > 500) return 'Note cannot exceed 500 characters.'; // BR-BACKEND-002 mirror
  return null;
}
```

### 3.2 API Error Response Parsing Schema

```typescript
// src/services/noteService.ts — extractErrorMessage()

/**
 * BR-FRONTEND-015: Extract user-facing string from FastAPI error responses.
 *
 * FastAPI HTTPException: { "detail": "string" }
 * Pydantic 422 error:    { "detail": [{ "loc": [...], "msg": "string", "type": "..." }] }
 *
 * Never display raw JSON to the user — always extract a readable string.
 */
export async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json() as ApiError;
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail[0].msg ?? 'Validation error';
    }
    return 'An error occurred';
  } catch {
    return 'An error occurred';
  }
}
```

### 3.3 DTO Shape Definitions

These mirror the backend Pydantic schemas (owned by MWU-NL2-001). The frontend TypeScript interfaces in `src/types/note.ts` (§1) are the authoritative frontend representation.

| Frontend DTO | Maps to backend schema | Fields |
|---|---|---|
| `NoteCreate` | `NoteCreate` (Pydantic) | `content: string` |
| `Note` | `NoteRead` (Pydantic) | `id: number`, `content: string`, `created_at: string` |
| `ApiError` | `HTTPException` detail envelope | `detail: string \| ValidationErrorItem[]` |

### 3.4 Component Props Contracts

```typescript
// AlertBanner — BR-FRONTEND-006
interface AlertBannerProps {
  type: 'error' | 'success';   // never both simultaneously
  message: string;             // never empty string when rendered
  onDismiss?: () => void;      // optional manual dismiss
}

// NoteForm — BR-FRONTEND-001, 004, 014
interface NoteFormProps {
  content: string;                            // controlled value (App.tsx owns)
  onContentChange: (value: string) => void;   // updates App state
  onSubmit: (content: string) => void;        // triggers POST flow
  submitting: boolean;                        // disables button when true
}

// NoteList — BR-FRONTEND-005, 009, 012
interface NoteListProps {
  notes: Note[];                  // API-ordered array; no client sort
  onDelete: (id: number) => void; // triggers confirm + DELETE flow
}

// NoteCard — BR-FRONTEND-002, 003, 008
interface NoteCardProps {
  note: Note;
  onDelete: (id: number) => void;
}
```

---

## §4 — API / Interface Design

The React frontend consumes three FastAPI endpoints defined in MWU-NL2-001. No additional endpoints are required for this module.

### 4.1 Endpoint Consumption Table

| Method | Path | Purpose | BRs enforced |
|--------|------|---------|--------------|
| `GET` | `/notes` | Fetch all notes on mount and after every mutation | BR-FRONTEND-009, BR-FRONTEND-012 |
| `POST` | `/notes` | Create note from NoteForm submission | BR-FRONTEND-001, BR-FRONTEND-004, BR-FRONTEND-014, BR-FRONTEND-015 |
| `DELETE` | `/notes/{id}` | Delete note after `window.confirm` | BR-FRONTEND-002, BR-FRONTEND-013, BR-FRONTEND-015 |

### 4.2 API Service Functions (Complete Implementation)

```typescript
// src/services/noteService.ts

import { Note, ApiError } from '../types/note';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * BR-FRONTEND-015: Parse FastAPI error envelope to human-readable string.
 */
export async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json() as ApiError;
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail[0].msg ?? 'Validation error';
    }
    return 'An error occurred';
  } catch {
    return 'An error occurred';
  }
}

/**
 * BR-FRONTEND-001, BR-BACKEND-001/002 mirror: client-side pre-flight check.
 * Returns null if valid, error string if invalid.
 */
export function validateNoteCreate(content: string): string | null {
  const trimmed = content.trim();
  if (trimmed.length === 0) return 'Note cannot be empty.';
  if (trimmed.length > 500) return 'Note cannot exceed 500 characters.';
  return null;
}

/**
 * GET /notes
 * BR-FRONTEND-009: returns notes in API order (newest first). No client sort.
 * BR-FRONTEND-012: no search, filter, pagination — returns all notes.
 */
export async function fetchNotes(): Promise<Note[]> {
  const res = await fetch(`${BASE_URL}/notes`);
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<Note[]>;
}

/**
 * POST /notes
 * BR-FRONTEND-014: caller must set submitting=true before calling, false after.
 * BR-FRONTEND-004: on throw, caller must NOT clear formContent.
 * BR-FRONTEND-015: error message extracted via extractErrorMessage.
 */
export async function createNote(content: string): Promise<Note> {
  const res = await fetch(`${BASE_URL}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
  return res.json() as Promise<Note>;
}

/**
 * DELETE /notes/{id}
 * BR-FRONTEND-013: uses HTTP DELETE method, never GET.
 * BR-FRONTEND-002: caller must call window.confirm before invoking this function.
 * BR-FRONTEND-015: error message extracted via extractErrorMessage.
 */
export async function deleteNote(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/notes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
}
```

### 4.3 Environment Configuration

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000

# .env.production
VITE_API_BASE_URL=https://api.example.com
```

### 4.4 HTTP Error Handling Matrix

| HTTP Status | FastAPI cause | Frontend action |
|-------------|--------------|-----------------|
| 200 OK | GET success | `notes=data`, render list |
| 201 Created | POST success | `alertType='success'`, `alertMessage='Note added.'`, clear form, refetch |
| 204 No Content | DELETE success | refetch notes, clear any alert |
| 400 Bad Request | Business rule violation | `alertType='error'`, `alertMessage=body.detail` |
| 404 Not Found | Note not found on DELETE | `alertType='error'`, `alertMessage=body.detail` |
| 422 Unprocessable Entity | Pydantic validation | `alertType='error'`, `alertMessage=detail[0].msg` |
| 5xx Server Error | Unexpected backend error | `alertType='error'`, `alertMessage='An error occurred'` |

---

## §5 — Service Layer Design

### 5.1 App.tsx — Root Component and State Owner

```typescript
// src/App.tsx
// BR-FRONTEND-007: NO auth — no AuthProvider, no ProtectedRoute, no useAuth,
//   no Authorization header, no token storage. All views unconditionally public.

import { useState, useEffect, useCallback } from 'react';
import { Note } from './types/note';
import {
  fetchNotes,
  createNote,
  deleteNote,
  validateNoteCreate,
} from './services/noteService';
import AlertBanner from './components/AlertBanner';
import NoteForm from './components/NoteForm';
import NoteList from './components/NoteList';
import 'bootstrap/dist/css/bootstrap.min.css';

export default function App() {
  const [notes, setNotes]             = useState<Note[]>([]);
  const [loading, setLoading]         = useState(true);
  const [submitting, setSubmitting]   = useState(false);          // BR-FRONTEND-014
  const [alertType, setAlertType]     = useState<'error' | 'success' | null>(null);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);
  const [formContent, setFormContent] = useState('');             // BR-FRONTEND-004

  const loadNotes = useCallback(async () => {
    try {
      const data = await fetchNotes();
      setNotes(data);                                              // BR-FRONTEND-009: API order
    } catch (err) {
      showAlert('error', (err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadNotes(); }, [loadNotes]);

  // BR-FRONTEND-006: always replaces previous alert — mutually exclusive
  const showAlert = (type: 'error' | 'success', message: string) => {
    setAlertType(type);
    setAlertMessage(message);
  };
  const clearAlert = () => { setAlertType(null); setAlertMessage(null); };

  const handleSubmit = async (content: string) => {
    clearAlert();
    const validationError = validateNoteCreate(content);
    if (validationError) { showAlert('error', validationError); return; }

    setSubmitting(true);                                           // BR-FRONTEND-014: disable button
    try {
      await createNote(content);
      setFormContent('');                                          // BR-FRONTEND-004: clear on success only
      showAlert('success', 'Note added.');                        // BR-FRONTEND-006: success copy
      await loadNotes();
    } catch (err) {
      // BR-FRONTEND-004: formContent NOT reset — error path preserves textarea
      showAlert('error', (err as Error).message);
    } finally {
      setSubmitting(false);                                        // BR-FRONTEND-014: re-enable button
    }
  };

  const handleDelete = async (id: number) => {
    // BR-FRONTEND-002: confirm before ANY delete request — cancel aborts entirely
    if (!window.confirm('Delete this note?')) return;
    clearAlert();
    try {
      await deleteNote(id);                                        // BR-FRONTEND-013: HTTP DELETE
      await loadNotes();
    } catch (err) {
      showAlert('error', (err as Error).message);                 // BR-FRONTEND-015
    }
  };

  return (
    <div className="container py-4">
      {/* BR-FRONTEND-010: "📝 Note List" brand — NO "Legacy v1.0" tag */}
      <nav className="navbar navbar-light bg-light mb-4 px-3 rounded">
        <span className="navbar-brand mb-0 h1">📝 Note List</span>
      </nav>

      {/* BR-FRONTEND-006: render only when alertType set; never both error+success */}
      {alertType && alertMessage && (
        <AlertBanner type={alertType} message={alertMessage} onDismiss={clearAlert} />
      )}

      <NoteForm
        content={formContent}
        onContentChange={setFormContent}
        onSubmit={handleSubmit}
        submitting={submitting}
      />

      {loading
        ? <p className="text-muted">Loading...</p>
        : <NoteList notes={notes} onDelete={handleDelete} />
      }

      {/* BR-FRONTEND-011: copyright line — "Legacy PHP Application" qualifier removed */}
      <footer className="text-center text-muted mt-5 small">
        Note List &copy; 2026
      </footer>
    </div>
  );
}
```

### 5.2 AlertBanner Component

```typescript
// src/components/AlertBanner.tsx
// BR-FRONTEND-006: inline alert banners, mutually exclusive, error=red / success=green
// BR-FRONTEND-008: message rendered as text via JSX — dangerouslySetInnerHTML FORBIDDEN

interface AlertBannerProps {
  type: 'error' | 'success';
  message: string;
  onDismiss?: () => void;
}

export default function AlertBanner({ type, message, onDismiss }: AlertBannerProps) {
  // BR-FRONTEND-006: red for error, green for success
  const className = type === 'error' ? 'alert alert-danger' : 'alert alert-success';

  return (
    <div className={`${className} d-flex justify-content-between align-items-center`} role="alert">
      {/* BR-FRONTEND-008: JSX text node — auto-escaped, no dangerouslySetInnerHTML */}
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          className="btn-close"
          onClick={onDismiss}
          aria-label="Close"
        />
      )}
    </div>
  );
}
```

### 5.3 NoteForm Component

```typescript
// src/components/NoteForm.tsx
// BR-FRONTEND-001: maxLength={500} HTML attribute (UX aid; server is authoritative)
// BR-FRONTEND-004: content is controlled prop from App.tsx — App only clears on success
// BR-FRONTEND-014: button disabled while submitting=true

interface NoteFormProps {
  content: string;
  onContentChange: (value: string) => void;
  onSubmit: (content: string) => void;
  submitting: boolean;
}

export default function NoteForm({ content, onContentChange, onSubmit, submitting }: NoteFormProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(content);
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="mb-3">
        <textarea
          className="form-control"
          rows={4}
          maxLength={500}                               // BR-FRONTEND-001
          value={content}                               // BR-FRONTEND-004: controlled
          onChange={(e) => onContentChange(e.target.value)}
          placeholder="Write a note..."
          aria-label="Note content"
        />
      </div>
      <button
        type="submit"
        className="btn btn-primary"
        disabled={submitting}                           // BR-FRONTEND-014
        aria-busy={submitting}
      >
        {submitting ? 'Adding…' : 'Add Note'}
      </button>
    </form>
  );
}
```

### 5.4 NoteList Component

```typescript
// src/components/NoteList.tsx
// BR-FRONTEND-005: exact empty-state copy from legacy
// BR-FRONTEND-009: map in API order — no sort
// BR-FRONTEND-012: flat list, no search/filter/sort toggle/pagination

import { Note } from '../types/note';
import NoteCard from './NoteCard';

interface NoteListProps {
  notes: Note[];
  onDelete: (id: number) => void;
}

export default function NoteList({ notes, onDelete }: NoteListProps) {
  if (notes.length === 0) {
    // BR-FRONTEND-005: exact string from legacy — do not alter
    return <p className="text-muted">No notes yet. Add one above.</p>;
  }

  return (
    <ul className="list-group">
      {/* BR-FRONTEND-009: API order preserved; no .sort() call */}
      {notes.map((note) => (
        <NoteCard key={note.id} note={note} onDelete={onDelete} />
      ))}
    </ul>
  );
}
```

### 5.5 NoteCard Component

```typescript
// src/components/NoteCard.tsx
// BR-FRONTEND-002: onDelete triggers window.confirm in App.tsx before fetch
// BR-FRONTEND-003: formatDate() with en-GB locale, zero-padded day
// BR-FRONTEND-008: JSX auto-escaping — dangerouslySetInnerHTML FORBIDDEN

import { Note } from '../types/note';
import { formatDate } from '../utils/formatDate';

interface NoteCardProps {
  note: Note;
  onDelete: (id: number) => void;
}

export default function NoteCard({ note, onDelete }: NoteCardProps) {
  return (
    <li className="list-group-item d-flex justify-content-between align-items-start gap-3">
      <div>
        {/* BR-FRONTEND-008: text node, auto-escaped by JSX — XSS impossible here */}
        <p className="mb-1">{note.content}</p>
        {/* BR-FRONTEND-003: "dd MMM yyyy", locale en-GB, zero-padded day */}
        <small className="text-muted">
          <time dateTime={note.created_at}>{formatDate(note.created_at)}</time>
        </small>
      </div>
      {/* BR-FRONTEND-002: confirm is handled in App.tsx handleDelete */}
      <button
        className="btn btn-sm btn-outline-danger flex-shrink-0"
        onClick={() => onDelete(note.id)}
        aria-label={`Delete note ${note.id}`}
      >
        Delete
      </button>
    </li>
  );
}
```

### 5.6 formatDate Utility

```typescript
// src/utils/formatDate.ts
// BR-FRONTEND-003: "dd MMM yyyy" format, locale pinned to en-GB, day zero-padded
// RISK-FE-001: explicit locale required — toLocaleDateString() without locale is forbidden

/**
 * BR-FRONTEND-003: Format ISO 8601 UTC string as "dd MMM yyyy".
 * day: '2-digit' ensures zero-padding ("05 Jan" not "5 Jan").
 * Locale 'en-GB' ensures English month abbreviations on all runtimes.
 *
 * RISK-FE-001: Do NOT use toLocaleDateString() without an explicit locale argument.
 */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso));
}
```

### 5.7 Project Configuration Files

```json
// package.json
{
  "name": "note-list-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "bootstrap": "^5.3.3"
  },
  "devDependencies": {
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.2",
    "vitest": "^2.0.5",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/user-event": "^14.5.2",
    "jsdom": "^25.0.0",
    "msw": "^2.3.5"
  }
}
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
```

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  },
  "include": ["src"]
}
```

---

## §6 — Risk Register and Mitigations

### RISK-FE-001: DATE-INTERPOLATION — Date Format Locale Mismatch (HIGH)

**Source behaviour:**
PHP `date('d M Y', strtotime($note['created_at']))` always produces zero-padded day and English month abbreviations (e.g., `"05 Jan 2026"`) regardless of server locale. The `'d'` format specifier zero-pads single-digit days; `'M'` produces three-letter English month names deterministically.

**Target implementation:**
Pin `Intl.DateTimeFormat` locale to `'en-GB'` with `day: '2-digit'`. Without explicit locale, `toLocaleDateString()` defaults to the user's browser/OS locale — producing `"1/5/2026"` in US-locale or `"05.01.2026"` in German-locale environments, breaking visual parity.

```typescript
// CORRECT — locale pinned, day zero-padded
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso));
  // Output: "05 Jan 2026"
}

// WRONG — locale not pinned, varies by user OS
const bad = new Date(iso).toLocaleDateString(); // could produce "1/5/2026" on en-US
```

**Validation approach:**
Unit tests in `formatDate.test.ts`:
- `formatDate('2026-01-05T00:00:00Z')` → `'05 Jan 2026'` (leading zero on day)
- `formatDate('2026-12-31T12:00:00Z')` → `'31 Dec 2026'`
- `formatDate('2026-03-01T00:00:00Z')` → `'01 Mar 2026'` (not `'1 Mar'`)
Tests must pass in CI regardless of runner system locale.

---

### RISK-FE-002: DELETE-METHOD-CHANGE — GET→DELETE Protocol Upgrade (MEDIUM)

**Source behaviour:**
Legacy PHP uses `<a href="?delete={id}">` — a GET request. This was a PHP limitation: links and form submissions were the only state-mutation mechanisms available in the simple single-file app.

**Target implementation:**
All delete operations use `fetch(url, { method: 'DELETE' })`. The note ID is a URL path parameter (`/notes/{id}`), not a query string. Never use GET for state-mutating operations.

```typescript
// CORRECT — HTTP DELETE with path parameter (BR-FRONTEND-013)
export async function deleteNote(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/notes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
}

// WRONG — GET-based delete (legacy anti-pattern, strictly forbidden)
// window.location.href = `?delete=${id}`;
// fetch(`${BASE_URL}/notes?delete=${id}`);
```

**Validation approach:**
Unit test: mock `fetch`, call `deleteNote(5)`, assert fetch called with URL `http://localhost:8000/notes/5` and `options.method === 'DELETE'`.

---

### RISK-FE-003: DIRECT-OUTPUT — SPA Replaces Full-Page Reload (MEDIUM)

**Source behaviour:**
Legacy PHP refreshes the entire page on every POST/DELETE. This implicitly cleared all form state on error as a side effect. BR-FRONTEND-004 (preserve form on error) had no explicit implementation — it was trivially satisfied by the page reload behaviour.

**Target implementation:**
React SPA must explicitly manage form state. The `formContent` state variable is NOT reset on the error path. It IS reset (to `''`) on the success path. The notes list is refreshed via `loadNotes()` (re-fetching `GET /notes`) without triggering a page reload.

```typescript
// CORRECT — explicit error path leaves formContent untouched
try {
  await createNote(content);
  setFormContent('');      // success: clear the textarea
  showAlert('success', 'Note added.');
  await loadNotes();
} catch (err) {
  showAlert('error', (err as Error).message);
  // formContent NOT modified — user can correct and retry
}

// WRONG — clearing on error violates BR-FRONTEND-004
// } catch (err) {
//   setFormContent('');  ← FORBIDDEN on error path
//   showAlert('error', ...);
// }
```

**Validation approach:**
Component test: fill textarea with `'My note content'`, mock `createNote` to throw, submit form, assert `textarea.value === 'My note content'` after render settles.

---

### RISK-FE-004: UX-GAP — No Character Counter (LOW)

**Source behaviour:**
Legacy uses only HTML `maxlength="500"`. No visible character counter, no countdown text, no progress bar.

**Target implementation:**
Replicate HTML `maxLength={500}` attribute only. Do NOT add a character counter or any visible counting UI. This is a parity migration; a character counter is a feature enhancement, not a BR.

**Validation approach:**
Code review: NoteForm.tsx must contain no `{content.length}/500` text, no `charCount` state variable, no `<progress>` element, no countdown span.

---

### RISK-FE-005: CONFIRM-DIALOG — window.confirm Limitations (LOW)

**Source behaviour:**
Legacy uses synchronous `window.confirm('Delete this note?')`. This matches BR-FRONTEND-002 exactly.

**Target implementation:**
Use `window.confirm('Delete this note?')` identically. Synchronous confirm may be suppressed in some embedded WebView environments — this is a known limitation accepted for this simple application. A custom modal would be an enhancement, not a parity requirement.

```typescript
// CORRECT — matches legacy parity (BR-FRONTEND-002)
if (!window.confirm('Delete this note?')) return;
await deleteNote(id);

// OUT OF SCOPE — custom modal (enhancement only, not required for parity)
// const confirmed = await showCustomModal('Delete this note?');
```

**Validation approach:**
Tests mock `window.confirm`. Test 1: mock returns `false`, assert `deleteNote` never called. Test 2: mock returns `true`, assert `deleteNote` called with correct id.

---

### RISK-FE-006: API-ERROR-CONTRACT — FastAPI Error Parsing (MEDIUM)

**Source behaviour:**
Legacy PHP echoed error strings directly into HTML as unstructured text. Frontend received a complete page re-render with the error already embedded.

**Target implementation:**
FastAPI returns structured JSON. Two error shapes exist:
- `HTTPException` (400/404/500): `{ "detail": "human-readable string" }`
- Pydantic 422: `{ "detail": [{ "loc": [...], "msg": "string", "type": "..." }] }`

The `extractErrorMessage` function handles both shapes and always returns a plain string.

```typescript
// Handles HTTPException (string detail) and Pydantic 422 (array detail)
export async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json() as ApiError;
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail[0].msg ?? 'Validation error';
    }
    return 'An error occurred';
  } catch {
    return 'An error occurred';  // non-JSON body (e.g. 502 gateway HTML)
  }
}
```

**Validation approach:**
Unit tests covering all three branches: string detail, array detail, non-JSON body.

---

### RISK-FE-007: ANY_AUTH_PATTERN — Prevent Auth Scaffolding (HIGH)

**Source behaviour:**
No authentication in legacy PHP app. All pages unconditionally public with no session checks.

**Target implementation:**
CRITICAL — zero authentication scaffolding anywhere in the React codebase.

**Forbidden patterns — all must produce zero grep matches in `src/`:**
- `useAuth` — auth hook
- `AuthProvider` — context provider
- `ProtectedRoute` — route guard
- `Authorization` — HTTP header
- `Bearer` — token scheme
- `localStorage.getItem.*token` — token storage
- `login` / `logout` — auth actions

```typescript
// CORRECT — unconditional render, no auth guard
export default function App() {
  return <div className="container py-4">...</div>;
}

// WRONG — any of these patterns are strictly forbidden
const { user } = useAuth();                           // FORBIDDEN
if (!isAuthenticated) return <Navigate to="/login" />; // FORBIDDEN
headers: { 'Authorization': `Bearer ${token}` }      // FORBIDDEN
```

**Validation approach:**
Static analysis / grep check in CI: `grep -r 'useAuth\|AuthProvider\|ProtectedRoute\|Authorization\|Bearer\|token\|login\|logout' src/` must return zero matches.

---

### RISK-FE-008: BRAND-COPY — Remove Legacy Tag (LOW)

**Source behaviour:**
Legacy navbar contained `<span class="badge bg-secondary">Legacy v1.0</span>` alongside the brand text.

**Target implementation:**
Navbar renders `📝 Note List` as brand text only. No badge, no version number, no "Legacy" text of any kind.

**Validation approach:**
Render test: assert rendered navbar DOM contains no text matching `/legacy/i` and no `v1.0` version tag. Assert `"📝 Note List"` is present.

---

## §7 — Cross-Module Stubs (if applicable)

The frontend depends on the FastAPI backend (MWU-NL2-001) via HTTP. Since the frontend imports no Python modules and communicates exclusively via HTTP, traditional Python stub classes do not apply. HTTP-level stubs are provided for the test suite using Mock Service Worker (MSW).

### 7.1 MSW Request Handlers (Test Stubs)

```typescript
// src/test/mocks/handlers.ts
// HTTP-level stubs for MWU-NL2-001 backend endpoints.
// Raises NotImplementedError equivalent (onUnhandledRequest: 'error') for any
// unrecognised request — equivalent to raising NotImplementedError in a Python stub.

import { http, HttpResponse } from 'msw';

const BASE_URL = 'http://localhost:8000';

export const handlers = [
  // Stub: GET /notes — returns empty list
  http.get(`${BASE_URL}/notes`, () => {
    return HttpResponse.json([]);
  }),

  // Stub: POST /notes — echoes a created note with id=1
  http.post(`${BASE_URL}/notes`, async ({ request }) => {
    const body = await request.json() as { content: string };
    return HttpResponse.json(
      { id: 1, content: body.content, created_at: '2026-05-20T10:00:00Z' },
      { status: 201 }
    );
  }),

  // Stub: DELETE /notes/:id — returns 204 No Content
  http.delete(`${BASE_URL}/notes/:id`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
```

```typescript
// src/test/mocks/server.ts
// MSW Node server. onUnhandledRequest: 'error' ensures any unregistered
// backend call fails the test — equivalent to NotImplementedError.

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

```typescript
// src/test/setup.ts

import { beforeAll, afterAll, afterEach } from 'vitest';
import { server } from './mocks/server';
import '@testing-library/jest-dom';

// Fail any test that makes an unhandled HTTP request — enforces stub coverage
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());  // reset per-test overrides
afterAll(() => server.close());
```

### 7.2 Fallback Fetch Stub (without MSW)

If MSW is not available, use a global fetch mock that throws on unexpected calls:

```typescript
vi.stubGlobal('fetch', async (url: string, options?: RequestInit) => {
  throw new Error(
    `Backend stub (MWU-NL2-001) not configured for: ` +
    `${options?.method ?? 'GET'} ${url} — add an MSW handler`
  );
});
```

---

## §8 — Data Migration (if applicable)

**N/A — schema created fresh.**

The React frontend holds no database tables and no persistent data. All note data resides in the PostgreSQL database owned by MWU-NL2-001 (backend module). No data migration, column type conversion, or encoding change is required for the frontend module.

**Infrastructure note:** The React build output (`dist/`) is served as static files from a web server. No legacy PHP session state, PHP cookies, or server-side rendered HTML needs to be migrated into the React app. The only data shared between the legacy system and the new system is the notes table in PostgreSQL — which is the backend's migration concern.

**CORS note (infrastructure, not a BR):** The React SPA will call FastAPI from a different origin (e.g., `localhost:3000` → `localhost:8000`). FastAPI must be configured with `CORSMiddleware` permitting the React dev origin (`http://localhost:5173` for Vite default). This is a backend configuration concern (MWU-NL2-001).

---

## §9 — Test Strategy

### 9.1 BR Coverage Matrix

| BR ID | Test type | Scenario | Expected result |
|-------|-----------|----------|-----------------|
| BR-FRONTEND-001 | DOM unit | Render NoteForm, inspect textarea | `maxLength` attribute equals `500` |
| BR-FRONTEND-001 | Unit | `validateNoteCreate('')` | Returns `'Note cannot be empty.'` |
| BR-FRONTEND-001 | Unit | `validateNoteCreate('x'.repeat(501))` | Returns `'Note cannot exceed 500 characters.'` |
| BR-FRONTEND-002 | Component | Click Delete, `window.confirm` returns `false` | `deleteNote` service never called |
| BR-FRONTEND-002 | Component | Click Delete, `window.confirm` returns `true` | `deleteNote` called with correct `id` |
| BR-FRONTEND-003 | Unit | `formatDate('2026-01-05T00:00:00Z')` | Returns `'05 Jan 2026'` |
| BR-FRONTEND-003 | Unit | `formatDate('2026-12-31T12:00:00Z')` | Returns `'31 Dec 2026'` |
| BR-FRONTEND-003 | Unit | `formatDate('2026-03-01T00:00:00Z')` | Returns `'01 Mar 2026'` (zero-padded) |
| BR-FRONTEND-004 | Component | Submit form, POST mock throws error | Textarea value unchanged after error |
| BR-FRONTEND-004 | Component | Submit form, POST mock succeeds | Textarea value is `''` after success |
| BR-FRONTEND-005 | Component | Render `<NoteList notes={[]} />` | Text `"No notes yet. Add one above."` present |
| BR-FRONTEND-005 | Component | Render `<NoteList notes={[note]} />` | Empty-state text absent |
| BR-FRONTEND-006 | Component | Error state set | `.alert-danger` rendered, `.alert-success` absent |
| BR-FRONTEND-006 | Component | Success state set | `.alert-success` rendered, `.alert-danger` absent |
| BR-FRONTEND-006 | Component | Error then success in sequence | Only `.alert-success` in DOM |
| BR-FRONTEND-007 | Static analysis | Grep `src/` for auth patterns | Zero matches for `useAuth`, `AuthProvider`, `ProtectedRoute`, `Authorization`, `Bearer`, `token`, `login`, `logout` |
| BR-FRONTEND-008 | Component | Render note with `<script>alert(1)</script>` | Script tag rendered as text, no execution |
| BR-FRONTEND-008 | Code review | Search for `dangerouslySetInnerHTML` in `src/` | Zero occurrences |
| BR-FRONTEND-009 | Component | Render `<NoteList notes={[n3, n2, n1]} />` | Notes appear in input array order (n3, n2, n1) |
| BR-FRONTEND-009 | Unit | `noteService.ts` source | No `.sort()` call in `fetchNotes` or anywhere in service layer |
| BR-FRONTEND-010 | Component | Render App navbar | `"📝 Note List"` present; no text matching `/legacy/i` |
| BR-FRONTEND-011 | Component | Render App footer | `"Note List © 2026"` present; `"Legacy PHP Application"` absent |
| BR-FRONTEND-012 | Component | Render App with notes | No `<input type="search">`, no filter, no sort toggle, no pagination controls |
| BR-FRONTEND-013 | Unit | Call `deleteNote(5)` | Fetch invoked with `method: 'DELETE'` and URL ending `/notes/5` |
| BR-FRONTEND-014 | Component | Click submit | Button has `disabled` attribute during async; loses it after resolution |
| BR-FRONTEND-014 | Component | POST resolves successfully | Button no longer disabled |
| BR-FRONTEND-015 | Unit | `extractErrorMessage` with string detail | Returns detail string verbatim |
| BR-FRONTEND-015 | Unit | `extractErrorMessage` with array detail | Returns `detail[0].msg` |
| BR-FRONTEND-015 | Unit | `extractErrorMessage` with non-JSON body | Returns `'An error occurred'` |

### 9.2 Test Fixtures

```typescript
// src/test/fixtures/notes.ts

import { Note } from '../../types/note';

// Standard set — three notes in newest-first order (BR-FRONTEND-009)
export const sampleNotes: Note[] = [
  { id: 3, content: 'Newest note',  created_at: '2026-05-20T10:00:00Z' },
  { id: 2, content: 'Middle note',  created_at: '2026-05-19T08:30:00Z' },
  { id: 1, content: 'Oldest note',  created_at: '2026-05-18T07:00:00Z' },
];

// XSS attempt — verifies JSX auto-escaping (BR-FRONTEND-008)
export const xssNote: Note = {
  id: 99,
  content: '<script>alert("XSS attack")</script>',
  created_at: '2026-05-20T00:00:00Z',
};

// Edge case — single-digit day, must produce leading zero (BR-FRONTEND-003)
export const edgeDateNote: Note = {
  id: 100,
  content: 'Test edge date',
  created_at: '2026-01-05T00:00:00Z',  // must format as "05 Jan 2026"
};
```

### 9.3 Happy Path Integration Test

```typescript
// src/test/components/App.integration.test.tsx

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import App from '../../App';

describe('Happy path: create a note', () => {
  it('creates a note, shows success banner, clears form, renders new note', async () => {
    const user = userEvent.setup();

    // Override stub to return the created note on refetch
    server.use(
      http.get('http://localhost:8000/notes', () =>
        HttpResponse.json([{ id: 1, content: 'My first note', created_at: '2026-05-20T10:00:00Z' }])
      )
    );

    render(<App />);
    await screen.findByText('No notes yet. Add one above.');  // initial empty state (BR-FRONTEND-005)

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'My first note');

    await user.click(screen.getByRole('button', { name: /add note/i }));

    // Success banner shown (BR-FRONTEND-006), exact copy
    await screen.findByText('Note added.');

    // Textarea cleared (BR-FRONTEND-004 success path)
    expect(textarea).toHaveValue('');

    // Note rendered in list
    await screen.findByText('My first note');
  });
});

describe('Happy path: delete a note', () => {
  it('deletes a note after confirm and removes it from the list', async () => {
    const user = userEvent.setup();
    vi.stubGlobal('confirm', () => true);  // BR-FRONTEND-002: user confirms

    server.use(
      http.get('http://localhost:8000/notes', () =>
        HttpResponse.json([{ id: 1, content: 'Note to delete', created_at: '2026-05-20T10:00:00Z' }])
      )
    );

    render(<App />);
    await screen.findByText('Note to delete');

    // After delete, refetch returns empty
    server.use(
      http.get('http://localhost:8000/notes', () => HttpResponse.json([]))
    );

    await user.click(screen.getByRole('button', { name: /delete/i }));

    // Note removed, empty state shown
    await screen.findByText('No notes yet. Add one above.');
  });
});
```

### 9.4 BR Violation Coverage Tests

```typescript
// src/test/components/NoteForm.test.tsx (excerpt)

describe('BR-FRONTEND-004: form preserved on error', () => {
  it('does not clear textarea when POST fails', async () => {
    server.use(
      http.post('http://localhost:8000/notes', () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 })
      )
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByPlaceholderText('Write a note...');

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'This should stay');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    await screen.findByText('An error occurred');
    // BR-FRONTEND-004: content preserved after error
    expect(textarea).toHaveValue('This should stay');
  });
});

// src/test/components/NoteCard.test.tsx (excerpt)

describe('BR-FRONTEND-002: confirm prevents delete', () => {
  it('does not call fetch when user cancels confirm', async () => {
    vi.stubGlobal('confirm', () => false);
    const fetchSpy = vi.spyOn(global, 'fetch');
    const user = userEvent.setup();

    render(<NoteList notes={sampleNotes.slice(0, 1)} onDelete={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: /delete/i }));

    expect(fetchSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('/notes/'),
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});

// src/test/unit/extractErrorMessage.test.ts

describe('BR-FRONTEND-015: extractErrorMessage', () => {
  it('returns string detail verbatim', async () => {
    const res = new Response(JSON.stringify({ detail: 'Note cannot be empty' }), { status: 400 });
    expect(await extractErrorMessage(res)).toBe('Note cannot be empty');
  });

  it('returns msg from first array detail item', async () => {
    const body = { detail: [{ loc: ['body', 'content'], msg: 'field required', type: 'missing' }] };
    const res = new Response(JSON.stringify(body), { status: 422 });
    expect(await extractErrorMessage(res)).toBe('field required');
  });

  it('returns fallback for non-JSON body', async () => {
    const res = new Response('<html>Bad Gateway</html>', { status: 502 });
    expect(await extractErrorMessage(res)).toBe('An error occurred');
  });
});
```

### 9.5 Static Analysis Checks (CI)

The following grep checks must be added to CI to enforce critical BRs:

```bash
# BR-FRONTEND-007: no auth scaffolding
grep -r 'useAuth\|AuthProvider\|ProtectedRoute\|Authorization\|Bearer' src/ && exit 1 || echo "BR-007 OK"

# BR-FRONTEND-008: no dangerouslySetInnerHTML
grep -r 'dangerouslySetInnerHTML' src/ && exit 1 || echo "BR-008 OK"

# BR-FRONTEND-013: no GET-based delete
grep -r 'delete\|Delete' src/ | grep -v 'method.*DELETE\|\.delete\|deleteNote\|onDelete\|handleDelete' && echo "Review delete usages"
```

---

*Planning Agent — MWU-NL2-002-FE — 2026-05-20*
