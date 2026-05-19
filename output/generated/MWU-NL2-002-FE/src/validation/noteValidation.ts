/** Maximum note length — mirrors BR-NL-002 server-side MAX_NOTE_LENGTH=500 */
export const MAX_NOTE_LENGTH = 500;

export interface ValidationResult {
  valid: boolean;
  error: string | null;
}

/**
 * BR-NL-FE-001: reject empty or whitespace-only content.
 * BR-NL-FE-002: reject content exceeding 500 characters.
 * BR-NL-FE-010: length check applied AFTER trim (trim is implicit here).
 *
 * Called before every POST /notes submission.
 */
export function validateNoteContent(raw: string): ValidationResult {
  const trimmed = raw.trim();

  // BR-NL-FE-001: empty check (post-trim)
  if (trimmed.length === 0) {
    return { valid: false, error: 'Note content cannot be empty.' };
  }

  // BR-NL-FE-002: length check (post-trim, to match server-side behaviour)
  if (trimmed.length > MAX_NOTE_LENGTH) {
    return {
      valid: false,
      error: `Note content exceeds the maximum length of ${MAX_NOTE_LENGTH} characters.`,
    };
  }

  return { valid: true, error: null };
}

/**
 * BR-NL-FE-010: return trimmed value ready to send to API.
 * RISK-002: do NOT escape HTML, SQL, or any special characters here —
 * that corrupts stored data. The API/ORM handles query safety.
 */
export function prepareContent(raw: string): string {
  return raw.trim();
}

/**
 * BR-NL-FE-002: remaining characters for the visible counter UI.
 * Measured on raw (un-trimmed) value for the counter, since the textarea
 * applies maxLength on the raw value. Negative when over limit.
 */
export function getRemainingChars(raw: string): number {
  return MAX_NOTE_LENGTH - raw.length;
}