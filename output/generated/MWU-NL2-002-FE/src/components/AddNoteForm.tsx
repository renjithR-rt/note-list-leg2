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