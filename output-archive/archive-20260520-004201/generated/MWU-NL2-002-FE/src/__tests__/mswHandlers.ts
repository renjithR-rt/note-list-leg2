import { http, HttpResponse } from 'msw';
import type { Note } from '../types/note';

// Shared mutable state across handlers
const notes: Note[] = [
  { id: 1, content: 'Test note one', created_at: '2026-05-18T10:00:00Z' },
  { id: 2, content: 'Test note two', created_at: '2026-05-17T08:00:00Z' },
];

export const handlers = [
  // GET /notes — returns notes array newest-first
  http.get('http://localhost:8000/notes', () => {
    return HttpResponse.json([...notes]);
  }),

  // POST /notes — validates content, creates note
  http.post('http://localhost:8000/notes', async ({ request }) => {
    const body = await request.json() as { content?: string };

    if (!body.content?.trim()) {
      return HttpResponse.json(
        {
          detail: [{
            loc: ['body', 'content'],
            msg: 'content cannot be empty',
            type: 'value_error',
          }],
        },
        { status: 422 }
      );
    }

    if (body.content.length > 500) {
      return HttpResponse.json(
        {
          detail: [{
            loc: ['body', 'content'],
            msg: 'content must be 500 characters or fewer',
            type: 'value_error',
          }],
        },
        { status: 422 }
      );
    }

    const newNote: Note = {
      id: notes.length + 1,
      content: body.content,
      created_at: new Date().toISOString(),
    };
    notes.unshift(newNote); // newest first
    return HttpResponse.json(newNote, { status: 201 });
  }),

  // DELETE /notes/:id — removes note or returns 404
  http.delete('http://localhost:8000/notes/:id', ({ params }) => {
    const id = Number(params.id);
    const idx = notes.findIndex(n => n.id === id);
    if (idx === -1) {
      return HttpResponse.json({ detail: 'Note not found' }, { status: 404 });
    }
    notes.splice(idx, 1);
    return HttpResponse.json({ message: 'Note deleted successfully', id });
  }),
];