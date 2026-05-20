I'll write the complete planning document for MWU-NL2-002-FE (LOW tier — no MKB queries). Let me first verify the output directory exists, then write the document.Directory exists. Writing the complete planning document now.Now storing to MKB (Step 4).Planning document written to disk and stored to MKB (UUID `6f71ecac-0726-4585-9b2e-628417f74141`).

---

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
 * Negative when over limit.
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

| Method | Path | Request Body | Success Response | BRs Consumed |
|--------|------|-------------|-----------------|--------------|
| GET | `/notes` | — | `Note[]` (newest first) | BR-NL-FE-004, BR-NL-FE-011 |
| POST | `/notes` | `{ content: string }` | `Note` (201) | BR-NL-FE-001, BR-NL-FE-002, BR-NL-FE-010, BR-NL-FE-011 |
| DELETE | `/notes/{id}` | — | 200/204 or 404 | BR-NL-FE-007, BR-NL-FE-011 |

### 4.3 Error Response Handling

| HTTP Status | Trigger | Frontend UX Action |
|-------------|---------|-------------------|
| 200 / 201 | Successful GET/POST | Update state; show success feedback (BR-NL-FE-008) |
| 204 | Successful DELETE | Remove note from list; show "Note deleted." |
| 404 | Delete of non-existent note | Show "Note not found — refreshing list."; re-fetch (BR-NL-FE-011, RISK-007) |
| 422 | Validation error from API | Display `detail[0].msg` as inline field error |
| 500 | Internal server error | Show "Server error, please try again." |
| Network failure | `fetch()` throws `TypeError` | Show "Network error — please check your connection." |

### 4.4 No Authentication (BR-NL-FE-006 — CRITICAL)

The frontend exposes **zero authentication UI**. No login forms, no token storage, no protected route wrappers, no `useAuth` hooks, no session checks. This mirrors the legacy source which has no auth.

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
│       ├── <p>{note.content}</p>          (BR-NL-FE-003: text node, never innerHTML)
│       ├── <time>{formatDate(...)}</time>  (BR-NL-FE-005: Intl formatting)
│       └── <button type="button">Delete   (BR-NL-FE-007: HTTP DELETE)
└── Footer                  (static)
```

No React Router. No external state management. `useState` is sufficient.

### 5.2 App Component

```typescript
// src/App.tsx
// BR-NL-FE-009: single-page layout — no routing.
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
    setNotes(prev => [note, ...prev]); // prepend — mirrors newest-first order
  }

  function handleNoteDeleted(id: number): void {
    setNotes(prev => prev.filter(n => n.id !== id));
  }

  async function handleDeleteError(message: string): Promise<void> {
    showFeedback(message, 'error');
    // BR-NL-FE-011 / RISK-007: on 404, re-fetch to sync state
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
| `handleNoteAdded()` | Prepend to maintain newest-first |
| `handleDeleteError()` | BR-NL-FE-011 (404 triggers list refresh) |
| `showFeedback()` | BR-NL-FE-008 (auto-clear after 4s) |

### 5.3 AddNoteForm Component

```typescript
// src/components/AddNoteForm.tsx
// Implements: BR-NL-FE-001, BR-NL-FE-002, BR-NL-FE-008, BR-NL-FE-010, BR-NL-FE-011

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
  onNoteAdded, onError, onSuccess,
}: AddNoteFormProps): React.JSX.Element {
  const [content, setContent] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    setContent(e.target.value);
    if (validationError) setValidationError(null);
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
        setValidationError(err.detail);
      } else {
        onError(err instanceof ApiError ? err.detail : 'Failed to add note.');
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
        {/* BR-NL-FE-001: inline validation error */}
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
```

### 5.4 NoteList Component

```typescript
// src/components/NoteList.tsx
// Implements: BR-NL-FE-004 (render in API order — no re-sort)

import React from 'react';
import NoteItem from './NoteItem';
import type { NoteListProps } from '../types/props';

export default function NoteList({
  notes, onNoteDeleted, onDeleteError, onDeleteSuccess,
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

### 5.5 NoteItem Component

```typescript
// src/components/NoteItem.tsx
// Implements: BR-NL-FE-003 (text-only — never innerHTML),
//             BR-NL-FE-005 (ISO 8601 → "18 May 2026"),
//             BR-NL-FE-007 (HTTP DELETE — never GET, never anchor),
//             BR-NL-FE-011 (404 path)

import React, { useState } from 'react';
import { deleteNote, ApiError } from '../api/notesApi';
import { formatDate } from '../utils/dateUtils';
import type { NoteItemProps } from '../types/props';

export default function NoteItem({
  note, onDelete, onError, onSuccess,
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
        onDelete(note.id);
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
// Implements: BR-NL-FE-008

import React from 'react';
import type { FeedbackMessageProps } from '../types/props';

export default function FeedbackMessage({
  message, type,
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
  return <header className="app-header"><h1>Note List</h1></header>;
}

// src/components/Footer.tsx
import React from 'react';
export default function Footer(): React.JSX.Element {
  return <footer className="app-footer"><p>Note List App</p></footer>;
}
```

### 5.8 Date Utility

```typescript
// src/utils/dateUtils.ts
// BR-NL-FE-005: format ISO 8601 → "18 May 2026"
// RISK-006: explicit locale — never toLocaleDateString() without locale.

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
├── App.tsx
├── main.tsx
├── api/
│   └── notesApi.ts
├── components/
│   ├── AddNoteForm.tsx
│   ├── FeedbackMessage.tsx
│   ├── Footer.tsx
│   ├── Header.tsx
│   ├── NoteItem.tsx
│   └── NoteList.tsx
├── types/
│   ├── note.ts
│   └── props.ts
├── utils/
│   └── dateUtils.ts
├── validation/
│   └── noteValidation.ts
└── test/
    ├── fixtures.ts
    ├── handlers.ts
    └── setup.ts
```

### 5.10 Vite + package.json

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/notes': { target: 'http://localhost:8000', changeOrigin: true } },
  },
});
```

```json
// package.json (key dependencies)
{
  "dependencies": { "react": "^18.3.1", "react-dom": "^18.3.1" },
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

No `react-router-dom` (BR-NL-FE-009). No `axios`, `date-fns`, `moment`, `lodash` — all functionality covered by browser APIs.

---

## §6 — Risk Register and Mitigations

### RISK-002: Raw SQL Concatenation — Frontend Data Purity Constraint
**Source behaviour:** Legacy PHP concatenated `$_POST['content']` directly into SQL. PHP also applied `htmlspecialchars()` on output — meaning content could be double-encoded if escaping was applied before storage.

**Target implementation:** React frontend sends raw trimmed user input. FastAPI uses SQLAlchemy ORM with parameterized queries. Pre-escaping on the frontend corrupts stored data.

```typescript
// CORRECT — send raw trimmed content:
const trimmed = content.trim();
await createNote(trimmed); // API receives: "O'Brien's & <script>"

// WRONG — corrupts stored data:
const escaped = content.replace(/&/g, '&amp;').replace(/</g, '&lt;');
// User later sees "&amp;" in their note
```

**Validation approach:** Store note with `O'Brien's & <script>alert(1)</script>`. Verify API stores exact string. Verify React renders as text node (see RISK-008).

---

### RISK-003: CSRF — DELETE via GET Anti-pattern
**Source behaviour:** `<a href="?delete=1">Delete</a>` — GET request that mutates state. Any page can embed `<img src="http://app/?delete=1">` to trigger deletion.

**Target implementation:** All deletes use `fetch()` with `method: 'DELETE'`. Trigger is always `<button type="button">`.

```typescript
// CORRECT:
await fetch(`/notes/${note.id}`, { method: 'DELETE' });
// <button type="button" onClick={handleDelete}>Delete</button>

// WRONG:
// <a href={`/?delete=${note.id}`}>Delete</a>  ← GET, CSRF-vulnerable
```

**Validation approach:** Assert `fetch` called with `{ method: 'DELETE' }`. Assert no `<a>` elements in NoteItem. Grep for `href.*delete` — zero results.

---

### RISK-005: Unbounded Note List
**Source behaviour:** `SELECT * FROM notes ORDER BY created_at DESC` — no LIMIT clause.

**Target implementation:** Frontend renders all notes via `Array.map()`. No client-side LIMIT, slice, or virtual scrolling. Component structure accommodates future API pagination transparently.

```typescript
// CORRECT:
{notes.map(note => <NoteItem key={note.id} note={note} {...handlers} />)}

// WRONG:
{notes.slice(0, 20).map(...)} // hides notes from users
```

**Validation approach:** Load test with 1000 mock notes. Assert all 1000 `<li>` elements render. Assert no `.slice()` in NoteList.

---

### RISK-006: Date Formatting — Browser Consistency
**Source behaviour:** PHP formatted dates server-side: `date('d M Y', ...)` → "18 May 2026".

**Target implementation:** `Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })` — explicit locale, consistent across all browsers.

```typescript
// CORRECT:
new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  .format(new Date('2026-05-18T10:00:00Z')); // "18 May 2026"

// WRONG:
new Date().toLocaleDateString(); // "5/18/2026" on en-US OS
import { format } from 'date-fns'; // 21 kB bundle for one format
```

**Validation approach:** Unit test `formatDate()` with five known inputs. Assert "D Mon YYYY" pattern.

---

### RISK-007: Silent Delete vs 404
**Source behaviour:** Legacy PHP `DELETE FROM notes WHERE id = ?` succeeded silently. Backend BR-NL-007 has NEEDS_VALIDATION annotation.

**Target implementation:** Frontend handles both:
- 200/204: remove from state, show "Note deleted."
- 404: show "Note not found — refreshing list.", trigger `loadNotes()`.

```typescript
try {
  await deleteNote(note.id);
  onDelete(note.id);
} catch (err) {
  if (err instanceof ApiError && err.status === 404) {
    onError('Note not found — refreshing list.');
    onDelete(note.id); // optimistic remove; App re-fetches
  }
}
```

**Validation approach:** MSW handler for `DELETE /notes/9999` returns 404. Assert error message. Assert list re-fetches. Assert note removed from display.

---

### RISK-008: XSS — Note Content Rendering
**Source behaviour:** PHP used `htmlspecialchars()` for output escaping.

**Target implementation (BR-NL-FE-003):** React JSX text interpolation (`{note.content}`) always creates a DOM text node. `dangerouslySetInnerHTML` is explicitly prohibited.

```tsx
// CORRECT — React escapes automatically:
<p className="note-content">{note.content}</p>

// WRONG — bypasses XSS protection:
<p dangerouslySetInnerHTML={{ __html: note.content }} /> // FORBIDDEN
```

**Validation approach:** Render NoteItem with `<script>alert("xss")</script>`. Assert `document.querySelector('script')` is `null`. Assert text node match found.

---

## §7 — Cross-Module Stubs

API stub for test environments where the backend is unavailable:

```typescript
// src/api/__stubs__/notesApi.stub.ts

import type { Note, NoteListResponse } from '../../types/note';
import { ApiError } from '../notesApi';

let _notes: Note[] = [
  { id: 2, content: 'Second note', created_at: '2026-05-18T12:00:00Z' },
  { id: 1, content: 'First note', created_at: '2026-05-18T10:00:00Z' },
];
let _nextId = 3;

export { ApiError };

export async function getNotes(): Promise<NoteListResponse> {
  return [..._notes];
}

export async function createNote(content: string): Promise<Note> {
  const trimmed = content.trim();
  if (!trimmed) throw new ApiError(422, 'Content cannot be empty');
  if (trimmed.length > 500) throw new ApiError(422, 'Content exceeds maximum length of 500 characters');
  const note: Note = { id: _nextId++, content: trimmed, created_at: new Date().toISOString() };
  _notes = [note, ..._notes];
  return note;
}

export async function deleteNote(id: number): Promise<void> {
  if (!_notes.some(n => n.id === id)) {
    // Must throw — never swallow silently
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

Stubs must throw `ApiError` — never return `null` or `undefined` silently on error paths.

---

## §8 — Data Migration

**N/A — schema created fresh.**

This MWU owns no database tables and no persistent client-side storage. No `localStorage`, `sessionStorage`, or `IndexedDB` usage is required by any BR. The React SPA is served as static files. The backend (MWU-NL-001) owns all data migration from legacy MySQL to PostgreSQL.

---

## §9 — Test Strategy

### 9.1 Framework

```
vitest ^1.6             — test runner (Vite-native, ESM-compatible)
@testing-library/react  — component rendering and interaction
@testing-library/jest-dom — DOM matchers
msw ^2.3                — fetch-level API mocking
jsdom ^24               — browser DOM in Node.js
```

### 9.2 MSW Setup

```typescript
// src/test/handlers.ts
import { http, HttpResponse } from 'msw';
import type { Note } from '../types/note';

const defaultNotes: Note[] = [
  { id: 2, content: 'Second note', created_at: '2026-05-18T12:00:00Z' },
  { id: 1, content: 'First note', created_at: '2026-05-18T10:00:00Z' },
];

export const handlers = [
  http.get('http://localhost:8000/notes', () => HttpResponse.json(defaultNotes)),

  http.post('http://localhost:8000/notes', async ({ request }) => {
    const body = await request.json() as { content: string };
    if (!body.content?.trim()) {
      return HttpResponse.json(
        { detail: [{ msg: 'Content cannot be empty', loc: ['body', 'content'], type: 'value_error' }] },
        { status: 422 }
      );
    }
    const note: Note = { id: 99, content: body.content, created_at: '2026-05-19T08:00:00Z' };
    return HttpResponse.json(note, { status: 201 });
  }),

  http.delete('http://localhost:8000/notes/:id', ({ params }) => {
    if (Number(params.id) === 9999) {
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
export const longContent = 'a'.repeat(500);
export const overLimitContent = 'a'.repeat(501);
export const whitespaceContent = '   ';
```

### 9.4 Full BR Test Matrix

| BR ID | Test Type | Scenario | Expected Result |
|-------|-----------|----------|----------------|
| BR-NL-FE-001 | Unit | `validateNoteContent('')` | `{ valid: false, error: "...empty..." }` |
| BR-NL-FE-001 | Unit | `validateNoteContent('   ')` | `{ valid: false, error: "...empty..." }` |
| BR-NL-FE-001 | Component | Submit form with empty textarea | Inline error; no fetch called |
| BR-NL-FE-001 | Component | Submit form with whitespace-only | Inline error; no fetch called |
| BR-NL-FE-001 | Integration | Server returns 422 | 422 detail shown as inline error |
| BR-NL-FE-002 | Unit | `validateNoteContent('a'.repeat(500))` | `{ valid: true, error: null }` |
| BR-NL-FE-002 | Unit | `validateNoteContent('a'.repeat(501))` | `{ valid: false, error: "...500..." }` |
| BR-NL-FE-002 | Component | Type 500 chars | Counter shows "0 characters remaining" |
| BR-NL-FE-002 | Component | Type 501 chars | Counter shows "1 characters over limit"; submit disabled |
| BR-NL-FE-003 | Component | Render `<script>` content | No `<script>` in DOM; text node visible |
| BR-NL-FE-003 | Component | Render `<b>bold</b>` content | Literal text; no `<b>` element in DOM |
| BR-NL-FE-003 | Static | Grep `dangerouslySetInnerHTML` in `src/` | Zero occurrences |
| BR-NL-FE-004 | Integration | GET returns `[id:2, id:1]` | id:2 renders first |
| BR-NL-FE-004 | Component | Add note → prepended | New note at position 0 |
| BR-NL-FE-004 | Static | Grep `.sort(` in NoteList | Zero sort calls |
| BR-NL-FE-005 | Unit | `formatDate('2026-05-18T10:00:00Z')` | `"18 May 2026"` |
| BR-NL-FE-005 | Unit | `formatDate('2026-01-01T00:00:00Z')` | `"1 Jan 2026"` |
| BR-NL-FE-005 | Unit | `formatDate('2026-12-31T12:00:00Z')` | `"31 Dec 2026"` |
| BR-NL-FE-005 | Component | Render NoteItem with known date | `<time>` contains "18 May 2026" |
| BR-NL-FE-006 | Integration | Render full App | No login form, no auth wrapper in DOM |
| BR-NL-FE-006 | Static | Grep `useAuth`, `PrivateRoute`, `login`, `token` in `src/` | Zero matches |
| BR-NL-FE-007 | Integration | Click Delete button | MSW receives `DELETE /notes/2` |
| BR-NL-FE-007 | Component | Render NoteItem | No `<a>` tag in component tree |
| BR-NL-FE-007 | Static | Grep `href.*delete` in NoteItem | Zero matches |
| BR-NL-FE-008 | Integration | Add note successfully | "Note added successfully." feedback visible |
| BR-NL-FE-008 | Integration | Network error on add | Error feedback visible |
| BR-NL-FE-008 | Integration | Delete note successfully | "Note deleted." feedback visible |
| BR-NL-FE-008 | Integration | Feedback auto-clear | After 4s, feedback removed from DOM |
| BR-NL-FE-009 | Integration | Render App | Form + list + feedback all on one page |
| BR-NL-FE-009 | Static | Grep `react-router-dom` in `src/` | Zero imports |
| BR-NL-FE-010 | Unit | `prepareContent('  hello  ')` | `"hello"` |
| BR-NL-FE-010 | Unit | `prepareContent("O'Brien's & <script>")` | Same string — no escaping |
| BR-NL-FE-010 | Component | Submit `"  hello  "` | `createNote("hello")` called |
| BR-NL-FE-011 | Integration | API returns 500 | "Server error, please try again." shown |
| BR-NL-FE-011 | Integration | Network failure | "Network error — please check your connection." |
| BR-NL-FE-011 | Integration | DELETE returns 404 | Error shown; list re-fetches |
| BR-NL-FE-011 | Integration | GET /notes fails on mount | Error feedback shown; empty list |

### 9.5 Coverage Requirements

- All 11 BR IDs must have at least one passing test
- BR-NL-FE-001 and BR-NL-FE-002: happy-path and minimum two rejection tests each
- RISK-003: explicit HTTP method assertion in network layer; no `<a>` element in NoteItem
- RISK-008: DOM inspection confirming no injected `<script>` or `<img onerror>` elements
- `validateNoteContent` and `prepareContent` tested as pure functions (no component rendering)
- No mocking of validators in component tests — test through real validator

---

*End of Planning Document — MWU-NL2-002-FE frontend*
*Total BRs covered: 11 / 11*
*Sections complete: §1–§9*
*Written to: `E:\Claude\note-list-leg2\output\mkb\frontend\track-a\planning-001.md`*
*MKB artifact UUID: `6f71ecac-0726-4585-9b2e-628417f74141`*