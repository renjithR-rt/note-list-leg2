import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import AddNoteForm from '../components/AddNoteForm';
import * as notesApi from '../api/notesApi';

vi.mock('../api/notesApi');

describe('AddNoteForm', () => {
  const onNoteAdded = vi.fn();
  const onError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // BR-NL-FE-001: reject empty
  it('shows inline error and does not call API for empty submission', async () => {
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));
    expect(screen.getByText(/cannot be empty/i)).toBeInTheDocument();
    expect(notesApi.createNote).not.toHaveBeenCalled();
  });

  // BR-NL-FE-001: reject whitespace-only
  it('shows inline error for whitespace-only content', async () => {
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    await userEvent.type(screen.getByRole('textbox'), '   ');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));
    expect(screen.getByText(/cannot be empty/i)).toBeInTheDocument();
    expect(notesApi.createNote).not.toHaveBeenCalled();
  });

  // BR-NL-FE-002: char counter visible and updates
  it('shows character counter that updates as user types', async () => {
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    expect(screen.getByText(/500/)).toBeInTheDocument(); // initial
    await userEvent.type(screen.getByRole('textbox'), 'hello');
    expect(screen.getByText(/495/)).toBeInTheDocument(); // after 5 chars
  });

  // BR-NL-FE-002: reject over-500 chars
  it('shows inline error for content over 500 chars', async () => {
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    const longContent = 'a'.repeat(501);
    await userEvent.type(screen.getByRole('textbox'), longContent);
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));
    expect(screen.getByText(/500 characters/i)).toBeInTheDocument();
    expect(notesApi.createNote).not.toHaveBeenCalled();
  });

  // BR-NL-FE-010: trim before submit
  it('trims whitespace from content before calling createNote', async () => {
    const newNote = { id: 1, content: 'hello', created_at: '2026-05-18T10:00:00Z' };
    vi.mocked(notesApi.createNote).mockResolvedValueOnce({ ok: true, data: newNote });

    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    await userEvent.type(screen.getByRole('textbox'), '  hello  ');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(notesApi.createNote).toHaveBeenCalledWith('hello'));
  });

  // BR-NL-FE-008: success path calls onNoteAdded
  it('calls onNoteAdded with new note on successful creation', async () => {
    const newNote = { id: 1, content: 'test note', created_at: '2026-05-18T10:00:00Z' };
    vi.mocked(notesApi.createNote).mockResolvedValueOnce({ ok: true, data: newNote });

    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    await userEvent.type(screen.getByRole('textbox'), 'test note');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(onNoteAdded).toHaveBeenCalledWith(newNote));
  });

  // BR-NL-FE-008: form clears after successful submission
  it('clears textarea after successful note creation', async () => {
    const newNote = { id: 1, content: 'test', created_at: '2026-05-18T10:00:00Z' };
    vi.mocked(notesApi.createNote).mockResolvedValueOnce({ ok: true, data: newNote });

    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    const textarea = screen.getByRole('textbox');
    await userEvent.type(textarea, 'test');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(textarea).toHaveValue(''));
  });

  // BR-NL-FE-011: API error handling
  it('calls onError when API returns 5xx', async () => {
    vi.mocked(notesApi.createNote).mockResolvedValueOnce({
      ok: false, status: 500, message: 'Server error. Please try again later.',
    });

    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    await userEvent.type(screen.getByRole('textbox'), 'test');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(onError).toHaveBeenCalledWith('Server error. Please try again later.'));
  });

  // Submit button disabled while submitting
  it('disables submit button while request is in-flight', async () => {
    vi.mocked(notesApi.createNote).mockImplementationOnce(
      () => new Promise(resolve =>
        setTimeout(() => resolve({ ok: true, data: { id: 1, content: 'x', created_at: '' } }), 100)
      )
    );

    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={onError} />);
    await userEvent.type(screen.getByRole('textbox'), 'test');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));

    expect(screen.getByRole('button', { name: /adding/i })).toBeDisabled();
  });
});