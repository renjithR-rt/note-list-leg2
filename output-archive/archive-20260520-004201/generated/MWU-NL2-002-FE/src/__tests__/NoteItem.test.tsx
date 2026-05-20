import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect } from 'vitest';
import NoteItem from '../components/NoteItem';
import type { Note } from '../types/note';

const mockNote: Note = {
  id: 1,
  content: 'Test note content',
  created_at: '2026-05-18T10:30:00Z',
};

describe('NoteItem', () => {
  // BR-NL-FE-003: text-only render — no HTML injection
  it('renders content as text, not as HTML', () => {
    const xssNote: Note = { ...mockNote, content: '<script>alert("xss")</script>' };
    render(<NoteItem note={xssNote} onDelete={vi.fn()} onError={vi.fn()} />);
    // Text visible as a string
    expect(screen.getByText('<script>alert("xss")</script>')).toBeInTheDocument();
    // No script element injected into DOM
    expect(document.querySelector('script')).toBeNull();
  });

  // BR-NL-FE-003: no dangerouslySetInnerHTML used
  it('does not use dangerouslySetInnerHTML', () => {
    const { container } = render(
      <NoteItem note={mockNote} onDelete={vi.fn()} onError={vi.fn()} />
    );
    // React sets innerHTML directly when dangerouslySetInnerHTML is used
    // This checks the content element specifically
    const contentEl = container.querySelector('.note-item__text');
    expect(contentEl?.innerHTML).toBe('Test note content'); // exact text, no HTML encoding artifacts
  });

  // BR-NL-FE-005: date formatted as "18 May 2026"
  it('formats created_at as "18 May 2026"', () => {
    render(<NoteItem note={mockNote} onDelete={vi.fn()} onError={vi.fn()} />);
    expect(screen.getByText('18 May 2026')).toBeInTheDocument();
  });

  // BR-NL-FE-007: delete uses button element, not anchor
  it('uses a button element for delete (not an anchor tag)', () => {
    render(<NoteItem note={mockNote} onDelete={vi.fn()} onError={vi.fn()} />);
    const deleteBtn = screen.getByRole('button', { name: /delete/i });
    expect(deleteBtn.tagName).toBe('BUTTON');
  });

  // BR-NL-FE-007: no anchor tags with delete-related href
  it('has no anchor tags with delete-related href attributes', () => {
    render(<NoteItem note={mockNote} onDelete={vi.fn()} onError={vi.fn()} />);
    const anchors = screen.queryAllByRole('link');
    anchors.forEach(anchor => {
      expect(anchor.getAttribute('href') ?? '').not.toMatch(/delete|remove/i);
    });
  });

  // BR-NL-FE-007: onDelete called with correct id on button click
  it('calls onDelete with note.id when delete button is clicked', async () => {
    const onDelete = vi.fn();
    render(<NoteItem note={mockNote} onDelete={onDelete} onError={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(onDelete).toHaveBeenCalledWith(1);
  });

  // BR-NL-FE-007: button disabled while deleting
  it('disables delete button while deletion is in-flight', async () => {
    const onDelete = vi.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );
    render(<NoteItem note={mockNote} onDelete={onDelete} onError={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /delete/i }));
    const btn = screen.getByRole('button', { name: /deleting/i });
    expect(btn).toBeDisabled();
  });
});