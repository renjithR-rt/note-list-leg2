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