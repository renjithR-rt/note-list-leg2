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