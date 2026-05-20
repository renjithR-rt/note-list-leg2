/**
 * BR-NL-FE-005: format ISO 8601 → "18 May 2026"
 * RISK-006: use Intl.DateTimeFormat with explicit locale — never toLocaleDateString()
 *           without locale (browser inconsistency), never moment.js (bundle weight).
 */
const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

/** BR-NL-FE-005: "2026-05-18T10:00:00Z" → "18 May 2026" */
export function formatDate(iso: string): string {
  return DATE_FORMATTER.format(new Date(iso));
}