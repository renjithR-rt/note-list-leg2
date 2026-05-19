import { describe, test, expect } from 'vitest';
import { formatDate } from './dateUtils';

describe('formatDate', () => {
  test('BR-NL-FE-005: ISO 8601 → "D Mon YYYY"', () => {
    expect(formatDate('2026-05-18T10:00:00Z')).toBe('18 May 2026');
  });

  test('BR-NL-FE-005: first day of year', () => {
    expect(formatDate('2026-01-01T00:00:00Z')).toBe('1 Jan 2026');
  });

  test('BR-NL-FE-005: last day of year', () => {
    expect(formatDate('2026-12-31T12:00:00Z')).toBe('31 Dec 2026');
  });

  test('BR-NL-FE-005: single-digit day has no leading zero', () => {
    expect(formatDate('2026-05-01T10:00:00Z')).toBe('1 May 2026');
  });
});