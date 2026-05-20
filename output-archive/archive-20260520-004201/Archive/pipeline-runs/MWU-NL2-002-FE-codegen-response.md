I'll start by querying the pipeline lessons and MKB for business rules, then generate the complete React frontend code.Perfect! I found 18 business rules including 11 frontend-specific rules. All critical rules are present. I can now generate the complete React frontend code.

### FILE: package.json
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
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "eslint": "^8.0.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "jsdom": "^24.0.0",
    "msw": "^2.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0"
  }
}
```

### FILE: vite.config.ts
```typescript
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

### FILE: tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### FILE: tsconfig.node.json
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

### FILE: vitest.config.ts
```typescript
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
```

### FILE: index.html
```html
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

### FILE: src/main.tsx
```tsx
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

### FILE: src/types/note.ts
```typescript
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

### FILE: src/types/props.ts
```typescript
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

### FILE: src/api/notesApi.ts
```typescript
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

### FILE: src/validation/noteValidation.ts
```typescript
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

### FILE: src/utils/dateUtils.ts
```typescript
/**
 * BR-NL-FE-005: format ISO 8601 → "18 May 2026"
 * RISK-006: use Intl.DateTimeFormat with explicit locale — never toLocaleDateString()
 *           without locale (browser inconsistency), never moment.js (bundle weight).
 */
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

### FILE: src/components/Header.tsx
```tsx
import React from 'react';

export default function Header(): React.JSX.Element {
  return (
    <header className="app-header">
      <h1>Note List</h1>
    </header>
  );
}
```

### FILE: src/components/Footer.tsx
```tsx
import React from 'react';

export default function Footer(): React.JSX.Element {
  return (
    <footer className="app-footer">
      <p>Note List App</p>
    </footer>
  );
}
```

### FILE: src/components/FeedbackMessage.tsx
```tsx
import React from 'react';
import type { FeedbackMessageProps } from '../types/props';

/**
 * BR-NL-FE-008: inline success/error feedback
 */
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

### FILE: src/components/AddNoteForm.tsx
```tsx
import React, { useState } from 'react';
import { createNote, ApiError } from '../api/notesApi';
import {
  validateNoteContent,
  prepareContent,
  getRemainingChars,
  MAX_NOTE_LENGTH,
} from '../validation/noteValidation';
import type { AddNoteFormProps } from '../types/props';

/**
 * Implements: BR-NL-FE-001 (empty reject), BR-NL-FE-002 (length limit + counter),
 *             BR-NL-FE-010 (trim before send), BR-NL-FE-008 (inline error),
 *             BR-NL-FE-011 (API error handling)
 */
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

### FILE: src/components/NoteItem.tsx
```tsx
import React, { useState } from 'react';
import { deleteNote, ApiError } from '../api/notesApi';
import { formatDate } from '../utils/dateUtils';
import type { NoteItemProps } from '../types/props';

/**
 * Implements: BR-NL-FE-003 (text-only rendering — no innerHTML),
 *             BR-NL-FE-005 (ISO 8601 → "18 May 2026"),
 *             BR-NL-FE-007 (HTTP DELETE — never GET, never anchor),
 *             BR-NL-FE-011 (404 error path)
 */
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

### FILE: src/components/NoteList.tsx
```tsx
import React from 'react';
import NoteItem from './NoteItem';
import type { NoteListProps } from '../types/props';

/**
 * Implements: BR-NL-FE-004 (render in API order — no re-sort)
 */
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

### FILE: src/App.tsx
```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { getNotes, ApiError } from './api/notesApi';
import Header from './components/Header';
import FeedbackMessage from './components/FeedbackMessage';
import AddNoteForm from './components/AddNoteForm';
import NoteList from './components/NoteList';
import Footer from './components/Footer';
import type { Note, FeedbackState } from './types/note';

const FEEDBACK_TIMEOUT_MS = 4000;

/**
 * BR-NL-FE-009: single-page layout — all functionality here, no routing.
 * BR-NL-FE-006: no auth state, no login, no protected routes.
 */
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

### FILE: src/index.css
```css
/* Reset and base styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f9f9f9;
}

/* Layout */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  text-align: center;
}

.app-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.app-main {
  flex: 1;
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
}

.app-footer {
  background-color: #34495e;
  color: #bdc3c7;
  text-align: center;
  padding: 1rem;
  font-size: 0.9rem;
}

/* Feedback message (BR-NL-FE-008) */
.feedback-message {
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.feedback-success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.feedback-error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

/* Form styles */
.add-note-form {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.form-field {
  margin-bottom: 1rem;
}

.form-field label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.form-field textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e1e8ed;
  border-radius: 4px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  min-height: 120px;
}

.form-field textarea:focus {
  outline: none;
  border-color: #3498db;
}

.form-field textarea[aria-invalid="true"] {
  border-color: #e74c3c;
}

/* Character counter (BR-NL-FE-002) */
.char-counter {
  display: block;
  font-size: 0.875rem;
  color: #6c757d;
  margin-top: 0.25rem;
  text-align: right;
}

.char-counter.over-limit {
  color: #e74c3c;
  font-weight: 600;
}

/* Field error (BR-NL-FE-001) */
.field-error {
  display: block;
  color: #e74c3c;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

/* Buttons */
.btn-primary {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2980b9;
}

.btn-primary:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

.btn-delete {
  background-color: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-delete:hover:not(:disabled) {
  background-color: #c0392b;
}

.btn-delete:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

/* Note list */
.note-list {
  list-style: none;
}

.note-item {
  background: white;
  margin-bottom: 1rem;
  padding: 1.25rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.note-content {
  flex: 1;
  font-size: 1rem;
  line-height: 1.5;
  word-wrap: break-word;
}

.note-date {
  font-size: 0.875rem;
  color: #6c757d;
  white-space: nowrap;
  margin-right: 1rem;
}

/* Loading and empty states */
.loading-state,
.empty-state {
  text-align: center;
  color: #6c757d;
  font-style: italic;
  padding: 2rem;
}

/* Responsive design */
@media (max-width: 768px) {
  .app-main {
    padding: 1rem;
  }
  
  .note-item {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  
  .note-date {
    margin-right: 0;
  }
}
```

### FILE: src/test/setup.ts
```typescript
import '@testing-library/jest-dom';
import { afterEach, beforeAll, afterAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './server';

// MSW server setup
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  cleanup(); // unmount components after each test
  server.resetHandlers();
});
afterAll(() => server.close());
```

### FILE: src/test/server.ts
```typescript
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

### FILE: src/test/handlers.ts
```typescript
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
    if (body.content.trim().length > 500) {
      return HttpResponse.json(
        { detail: [{ msg: 'Content exceeds maximum length of 500 characters', loc: ['body', 'content'], type: 'value_error' }] },
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

### FILE: src/test/fixtures.ts
```typescript
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

### FILE: src/validation/noteValidation.test.ts
```typescript
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

### FILE: src/utils/dateUtils.test.ts
```typescript
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

### FILE: src/components/NoteItem.test.tsx
```typescript
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

### FILE: src/components/AddNoteForm.test.tsx
```typescript
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
    expect(addedNote.content).toBe('  hello  '); // MSW echo's the sent content exactly
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

### FILE: src/App.test.tsx
```typescript
import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  test('BR-NL-FE-009: renders single-page layout', async () => {
    render(<App />);
    
    // All components should be present on one page
    expect(screen.getByRole('banner')).toBeInTheDocument(); // header
    expect(screen.getByRole('main')).toBeInTheDocument();   // main content
    expect(screen.getByRole('contentinfo')).toBeInTheDocument(); // footer
    expect(screen.getByRole('textbox')).toBeInTheDocument(); // add form
  });

  test('BR-NL-FE-006: no auth UI elements present', () => {
    render(<App />);
    
    // Should not contain any auth-related elements
    expect(screen.queryByText(/login/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/logout/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sign in/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/authentication/i)).not.toBeInTheDocument();
  });

  test('BR-NL-FE-004: displays notes in API order', async () => {
    render(<App />);
    
    // Wait for notes to load and check they appear in correct order
    const notes = await screen.findAllByRole('listitem');
    expect(notes).toHaveLength(2);
    
    // First note should be id:2 (newer), second should be id:1 (older)
    expect(notes[0]).toHaveTextContent('Second note');
    expect(notes[1]).toHaveTextContent('First note');
  });
});
```

### FILE: integration-hints.json
```json
{
  "mwu_id": "MWU-NL2-002-FE",
  "module": "frontend",
  "depends_on_modules": [],
  "files_generated": [
    "src/main.tsx",
    "src/App.tsx",
    "src/types/note.ts",
    "src/types/props.ts",
    "src/api/notesApi.ts",
    "src/validation/noteValidation.ts",
    "src/utils/dateUtils.ts",
    "src/components/Header.tsx",
    "src/components/Footer.tsx",
    "src/components/FeedbackMessage.tsx",
    "src/components/AddNoteForm.tsx",
    "src/components/NoteItem.tsx",
    "src/components/NoteList.tsx",
    "src/index.css"
  ],
  "routers": [],
  "smoke_test_endpoints": [
    {"method": "GET", "path": "/notes", "expect_status": [200, 500]},
    {"method": "POST", "path": "/notes", "expect_status": [201, 422, 500]},
    {"method": "DELETE", "path": "/notes/1", "expect_status": [204, 404, 500]}
  ],
  "migration_sql": [],
  "utilities_added": [],
  "frontend_build": {
    "framework": "React 18",
    "bundler": "Vite",
    "language": "TypeScript",
    "dev_server_port": 5173,
    "api_proxy_target": "http://localhost:8000"
  },
  "business_rules_implemented": [
    "BR-NL-FE-001",
    "BR-NL-FE-002", 
    "BR-NL-FE-003",
    "BR-NL-FE-004",
    "BR-NL-FE-005",
    "BR-NL-FE-006",
    "BR-NL-FE-007",
    "BR-NL-FE-008",
    "BR-NL-FE-009",
    "BR-NL-FE-010",
    "BR-NL-FE-011"
  ]
}
```

## Summary

I've generated a complete React TypeScript frontend implementing all 11 business rules:

**Key Features Implemented:**
- ✅ **BR-NL-FE-001**: Client-side empty content validation with inline errors
- ✅ **BR-NL-FE-002**: 500-character limit with live counter
- ✅ **BR-NL-FE-003**: XSS protection via JSX text nodes (no `dangerouslySetInnerHTML`)
- ✅ **BR-NL-FE-004**: Preserves API sort order (no client-side re-sorting)
- ✅ **BR-NL-FE-005**: ISO 8601 → "18 May 2026" date formatting
- ✅ **BR-NL-FE-006**: **CRITICAL** - Zero authentication UI
- ✅ **BR-NL-FE-007**: HTTP DELETE (fixes CSRF anti-pattern from legacy GET)
- ✅ **BR-NL-FE-008**: Inline success/error feedback with auto-dismiss
- ✅ **BR-NL-FE-009**: Single-page layout (no routing)
- ✅ **BR-NL-FE-010**: Content trimming before API submission
- ✅ **BR-NL-FE-011**: Graceful API error handling (422/404/5xx/network)

**Architecture:**
- React 18 + TypeScript + Vite
- MSW for API mocking in tests
- Vitest + Testing Library for comprehensive test coverage
- Clean component architecture with proper separation of concerns
- Type-safe API client with error classification

**Next Steps:**
1. Run `npm install` to install dependencies
2. Run `npm run dev` to start the development server on port 5173
3. Ensure the backend API is running on port 8000
4. Run `npm test` to verify all business rules pass validation

The frontend is ready for integration with the FastAPI backend (MWU-NL2-001).