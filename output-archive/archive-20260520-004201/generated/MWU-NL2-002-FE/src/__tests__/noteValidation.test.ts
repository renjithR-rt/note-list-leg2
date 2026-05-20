import { describe, it, expect } from 'vitest';
import {
  validateNoteContent,
  getRemainingChars,
  getCounterClass,
  extractApiErrorMessage,
  formatNoteDate,
} from '../validation/noteValidation';

describe('validateNoteContent', () => {
  // BR-NL-FE-001: empty string rejected
  it('rejects empty string', () => {
    const result = validateNoteContent('');
    expect(result.valid).toBe(false);
    expect(result.error).toContain('empty');
  });

  // BR-NL-FE-001: whitespace-only rejected
  it('rejects whitespace-only content', () => {
    expect(validateNoteContent('   ').valid).toBe(false);
    expect(validateNoteContent('\t\n  ').valid).toBe(false);
    expect(validateNoteContent(' ').valid).toBe(false);
  });

  // BR-NL-FE-002: over-limit rejected
  it('rejects content over 500 chars', () => {
    const result = validateNoteContent('a'.repeat(501));
    expect(result.valid).toBe(false);
    expect(result.error).toContain('500');
  });

  // BR-NL-FE-002: exactly 500 chars accepted
  it('accepts content exactly 500 chars', () => {
    expect(validateNoteContent('a'.repeat(500)).valid).toBe(true);
  });

  // BR-NL-FE-010: trim applied before length check
  it('trims whitespace before validating length (500 chars of content + spaces = valid)', () => {
    const contentWithSpaces = '  ' + 'a'.repeat(500) + '  '; // 504 total, 500 trimmed
    expect(validateNoteContent(contentWithSpaces).valid).toBe(true);
  });

  // BR-NL-FE-010: trim applied before empty check
  it('trims before empty check (spaces-only is still empty)', () => {
    expect(validateNoteContent('     ').valid).toBe(false);
  });

  it('accepts valid content', () => {
    const result = validateNoteContent('Valid note content');
    expect(result.valid).toBe(true);
    expect(result.error).toBeNull();
  });
});

describe('getRemainingChars', () => {
  it('returns 500 for empty string', () => {
    expect(getRemainingChars('')).toBe(500);
  });

  it('returns 0 for 500-char string', () => {
    expect(getRemainingChars('a'.repeat(500))).toBe(0);
  });

  it('returns negative for over-limit input', () => {
    expect(getRemainingChars('a'.repeat(501))).toBe(-1);
    expect(getRemainingChars('a'.repeat(510))).toBe(-10);
  });
});

describe('getCounterClass', () => {
  it('returns counter--normal for plenty of space', () => {
    expect(getCounterClass(500)).toBe('counter--normal');
    expect(getCounterClass(21)).toBe('counter--normal');
  });

  it('returns counter--warning when 20 chars or fewer remain', () => {
    expect(getCounterClass(20)).toBe('counter--warning');
    expect(getCounterClass(1)).toBe('counter--warning');
    expect(getCounterClass(0)).toBe('counter--warning');
  });

  it('returns counter--over when negative', () => {
    expect(getCounterClass(-1)).toBe('counter--over');
    expect(getCounterClass(-100)).toBe('counter--over');
  });
});

describe('extractApiErrorMessage', () => {
  it('extracts first msg from 422 detail array', () => {
    const body = {
      detail: [
        { loc: ['body', 'content'], msg: 'content cannot be empty', type: 'value_error' },
      ],
    };
    expect(extractApiErrorMessage(422, body)).toBe('content cannot be empty');
  });

  it('returns fallback for malformed 422', () => {
    expect(extractApiErrorMessage(422, {})).toBe('Validation error. Please check your input.');
    expect(extractApiErrorMessage(422, { detail: [] })).toBe('Validation error. Please check your input.');
  });

  it('returns note not found for 404', () => {
    expect(extractApiErrorMessage(404, {})).toBe('Note not found.');
  });

  it('returns server error for 500+', () => {
    expect(extractApiErrorMessage(500, {})).toBe('Server error. Please try again later.');
    expect(extractApiErrorMessage(503, {})).toBe('Server error. Please try again later.');
  });

  it('extracts detail string for other errors', () => {
    expect(extractApiErrorMessage(400, { detail: 'Bad request' })).toBe('Bad request');
  });

  it('returns generic message when no detail', () => {
    expect(extractApiErrorMessage(400, {})).toBe('An unexpected error occurred.');
  });
});

describe('formatNoteDate', () => {
  // BR-NL-FE-005: ISO 8601 → "18 May 2026"
  it('formats ISO 8601 UTC timestamp as "18 May 2026"', () => {
    expect(formatNoteDate('2026-05-18T10:30:00Z')).toBe('18 May 2026');
  });

  it('formats date with single-digit day', () => {
    expect(formatNoteDate('2026-05-01T00:00:00Z')).toBe('1 May 2026');
  });

  it('formats date with different month', () => {
    expect(formatNoteDate('2026-12-25T12:00:00Z')).toBe('25 Dec 2026');
  });
});