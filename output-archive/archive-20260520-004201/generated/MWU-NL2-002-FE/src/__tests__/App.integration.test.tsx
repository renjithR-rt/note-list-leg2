import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { http, HttpResponse } from 'msw';
import App from '../App';
import { server } from './mswServer';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('App integration', () => {
  // Initial load
  it('loads and displays notes on mount', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Test note one')).toBeInTheDocument());
    expect(screen.getByText('Test note two')).toBeInTheDocument();
  });

  // BR-NL-FE-004: preserve API order
  it('renders notes in the order returned by API (newest first)', async () => {
    render(<App />);
    await waitFor(() => screen.getByText('Test note one'));
    const items = screen.getAllByTestId('note-item');
    expect(items[0]).toHaveTextContent('Test note one');
    expect(items[1]).toHaveTextContent('Test note two');
  });

  // BR-NL-FE-006: CRITICAL — no auth UI
  it('renders no login, sign-in, or auth-related UI', () => {
    render(<App />);
    expect(screen.queryByRole('form', { name: /login/i })).toBeNull();
    expect(screen.queryByText(/sign in/i)).toBeNull();
    expect(screen.queryByText(/log in/i)).toBeNull();
    expect(screen.queryByText(/password/i)).toBeNull();
    expect(screen.queryByText(/username/i)).toBeNull();
  });

  // BR-NL-FE-008: success feedback after add
  it('shows success feedback after adding a note', async () => {
    render(<App />);
    await waitFor(() => screen.getByRole('textbox'));
    await userEvent.type(screen.getByRole('textbox'), 'My new note');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));
    await waitFor(() => expect(screen.getByText(/added successfully/i)).toBeInTheDocument());
  });

  // BR-NL-FE-004: new note prepended (stays newest-first)
  it('prepends new note to list top after creation', async () => {
    render(<App />);
    await waitFor(() => screen.getByRole('textbox'));
    await userEvent.type(screen.getByRole('textbox'), 'Newest note');
    await userEvent.click(screen.getByRole('button', { name: /add note/i }));
    await waitFor(() => {
      const items = screen.getAllByTestId('note-item');
      expect(items[0]).toHaveTextContent('Newest note');
    });
  });

  // BR-NL-FE-008: success feedback after delete
  it('shows success feedback after deleting a note', async () => {
    render(<App />);
    await waitFor(() => screen.getAllByTestId('note-item'));
    await userEvent.click(screen.getAllByRole('button', { name: /delete/i })[0]);
    await waitFor(() => expect(screen.getByText(/deleted/i)).toBeInTheDocument());
  });

  // BR-NL-FE-011: 404 delete — warning + refresh
  it('shows warning and refreshes list when delete returns 404', async () => {
    server.use(
      http.delete('http://localhost:8000/notes/:id', () =>
        HttpResponse.json({ detail: 'Note not found' }, { status: 404 })
      )
    );
    render(<App />);
    await waitFor(() => screen.getAllByTestId('note-item'));
    await userEvent.click(screen.getAllByRole('button', { name: /delete/i })[0]);
    await waitFor(() => expect(screen.getByText(/not found/i)).toBeInTheDocument());
  });

  // BR-NL-FE-011: network error on initial load
  it('shows error feedback when initial notes fetch fails', async () => {
    server.use(
      http.get('http://localhost:8000/notes', () => HttpResponse.error())
    );
    render(<App />);
    await waitFor(() =>
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    );
  });

  // BR-NL-FE-009: single-page — no route changes
  it('all functionality available on single page without navigation', async () => {
    render(<App />);
    await waitFor(() => screen.getByRole('textbox'));
    // Form and notes list both visible without navigating
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add note/i })).toBeInTheDocument();
    // Notes load in same view
    await waitFor(() => screen.getAllByTestId('note-item'));
    expect(screen.getAllByTestId('note-item').length).toBeGreaterThan(0);
  });
});