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