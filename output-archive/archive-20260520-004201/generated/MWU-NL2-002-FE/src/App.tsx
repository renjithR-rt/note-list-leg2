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