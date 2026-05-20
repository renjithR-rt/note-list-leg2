import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  test('BR-NL-FE-009: renders single-page layout', async () => {
    render(<App />);
    
    // All components should be present on one page
    expect(screen.getByRole('banner')).toBeInTheDocument(); // header
    expect(screen.getByRole('main')).toBeInTheDocument();   // main content
    expect(screen.getByRole('contentinfo')).toBeInTheDocument(); // footer
    expect(screen.getByRole('textbox')).toBeInTheDocument(); // add form
  });

  test('BR-NL-FE-006: no auth UI elements present', () => {
    render(<App />);
    
    // Should not contain any auth-related elements
    expect(screen.queryByText(/login/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/logout/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sign in/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/authentication/i)).not.toBeInTheDocument();
  });

  test('BR-NL-FE-004: displays notes in API order', async () => {
    render(<App />);
    
    // Wait for notes to load and check they appear in correct order
    const notes = await screen.findAllByRole('listitem');
    expect(notes).toHaveLength(2);
    
    // First note should be id:2 (newer), second should be id:1 (older)
    expect(notes[0]).toHaveTextContent('Second note');
    expect(notes[1]).toHaveTextContent('First note');
  });
});