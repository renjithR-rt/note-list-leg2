/** A single note returned by the API */
export interface Note {
  id: number;
  content: string;      // plain text, 1–500 chars
  created_at: string;   // ISO 8601 — e.g. "2026-05-18T14:32:00.000Z"
}

/** GET /notes returns an ordered array — newest first (BR-NL-FE-004) */
export type NoteListResponse = Note[];

/** POST /notes request body — trimmed content only (BR-NL-FE-010) */
export interface CreateNoteRequest {
  content: string; // trimmed, 1–500 chars — no pre-escaping (RISK-002)
}

/** Generic message response from successful POST/DELETE */
export interface ApiSuccessResponse {
  message: string;
}

/** FastAPI 422 Unprocessable Entity response shape */
export interface ApiValidationError {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}

/** FastAPI 404 Not Found response */
export interface ApiNotFoundError {
  detail: string;
}

/** Feedback state shape used in App component */
export interface FeedbackState {
  message: string;
  type: 'success' | 'error';
}