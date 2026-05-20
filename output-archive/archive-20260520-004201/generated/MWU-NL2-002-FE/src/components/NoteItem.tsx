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