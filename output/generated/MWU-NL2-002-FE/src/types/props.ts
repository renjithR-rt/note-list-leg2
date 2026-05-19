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