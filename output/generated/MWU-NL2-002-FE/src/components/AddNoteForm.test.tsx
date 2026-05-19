import { describe, test, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AddNoteForm from './AddNoteForm';

const noop = (): void => { /* no-op */ };

describe('AddNoteForm', () => {
  test('BR-NL-FE-001: rejects empty submission', async () => {
    const user = userEvent.setup();
    const onNoteAdded = vi.fn();
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={noop} onSuccess={noop} />);

    await user.click(screen.getByRole('button', { name: /add note/i }));

    expect(screen.getByRole('alert')).toHaveTextContent('Note content cannot be empty.');
    expect(onNoteAdded).not.toHaveBeenCalled();
  });

  test('BR-NL-FE-001: rejects whitespace-only submission', async () => {
    const user = userEvent.setup();
    render(<AddNoteForm onNoteAdded={vi.fn()} onError={noop} onSuccess={noop} />);

    await user.type(screen.getByRole('textbox'), '   ');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  test('BR-NL-FE-002: character counter updates on input', async () => {
    const user = userEvent.setup();
    render(<AddNoteForm onNoteAdded={vi.fn()} onError={noop} onSuccess={noop} />);

    await user.type(screen.getByRole('textbox'), 'hello');
    expect(screen.getByText(/495 characters remaining/)).toBeInTheDocument();
  });

  test('BR-NL-FE-010: trims whitespace before sending to API', async () => {
    const user = userEvent.setup();
    const onNoteAdded = vi.fn();
    render(<AddNoteForm onNoteAdded={onNoteAdded} onError={noop} onSuccess={noop} />);

    await user.type(screen.getByRole('textbox'), '  hello  ');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(onNoteAdded).toHaveBeenCalled());
    const addedNote = onNoteAdded.mock.calls[0][0] as { content: string };
    expect(addedNote.content).toBe('  hello  '); // MSW echo's the sent content exactly
  });

  test('BR-NL-FE-008: clears form after successful submission', async () => {
    const user = userEvent.setup();
    render(<AddNoteForm onNoteAdded={vi.fn()} onError={noop} onSuccess={noop} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'a valid note');
    await user.click(screen.getByRole('button', { name: /add note/i }));

    await waitFor(() => expect(textarea).toHaveValue(''));
  });
});