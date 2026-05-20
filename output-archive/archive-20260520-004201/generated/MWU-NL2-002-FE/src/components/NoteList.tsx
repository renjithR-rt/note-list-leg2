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