import { describe, test, expect } from 'vitest';
import {
  validateNoteContent,
  prepareContent,
  getRemainingChars,
  MAX_NOTE_LENGTH,
} from './noteValidation';

describe('validateNoteContent', () => {
  test('BR-NL-FE-001: empty string rejected', () => {
    expect(validateNoteContent('')).toMatchObject({ valid: false });
  });

  test('BR-NL-FE-001: whitespace-only rejected', () => {
    expect(validateNoteContent('   ')).toMatchObject({ valid: false });
  });

  test('BR-NL-FE-002: exactly 500 chars accepted', () => {
    expect(validateNoteContent('a'.repeat(MAX_NOTE_LENGTH))).toEqual({ valid: true, error: null });
  });

  test('BR-NL-FE-002: 501 chars rejected', () => {
    const result = validateNoteContent('a'.repeat(MAX_NOTE_LENGTH + 1));
    expect(result.valid).toBe(false);
    expect(result.error).toContain('500');
  });

  test('BR-NL-FE-001 + BR-NL-FE-010: whitespace around valid content accepted', () => {
    expect(validateNoteContent('  hello  ')).toEqual({ valid: true, error: null });
  });
});

describe('prepareContent', () => {
  test('BR-NL-FE-010: trims leading and trailing whitespace', () => {
    expect(prepareContent('  hello world  ')).toBe('hello world');
  });

  test('BR-NL-FE-010 / RISK-002: does not escape special characters', () => {
    expect(prepareContent("O'Brien's & <script>")).toBe("O'Brien's & <script>");
  });
});

describe('getRemainingChars', () => {
  test('BR-NL-FE-002: 5 chars typed → 495 remaining', () => {
    expect(getRemainingChars('hello')).toBe(495);
  });

  test('BR-NL-FE-002: 501 chars typed → -1 remaining', () => {
    expect(getRemainingChars('a'.repeat(501))).toBe(-1);
  });
});