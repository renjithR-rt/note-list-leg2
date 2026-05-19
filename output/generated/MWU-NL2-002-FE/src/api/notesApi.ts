import type { Note, NoteListResponse } from '../types/note';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

/**
 * Typed API error — always has an HTTP status code and human-readable detail.
 * Thrown for any non-2xx response. Callers check err.status for 404 vs 5xx branching.
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

/** Parse response body and throw ApiError for non-2xx. */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return {} as T;
    return response.json() as Promise<T>;
  }

  let detail = `HTTP ${response.status} error`;
  try {
    const body = await response.json() as { detail?: string | Array<{ msg: string }> };
    if (typeof body?.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      detail = body.detail[0].msg;
    }
  } catch {
    // Body is not JSON — keep the generic message
  }

  throw new ApiError(response.status, detail);
}

/**
 * BR-NL-FE-004: API guarantees newest-first order — frontend does not re-sort.
 * BR-NL-FE-011: Network and HTTP errors surfaced as ApiError.
 */
export async function getNotes(): Promise<NoteListResponse> {
  const response = await fetch(`${BASE_URL}/notes`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<NoteListResponse>(response);
}

/**
 * BR-NL-FE-010: content must already be trimmed by the caller.
 * RISK-002: send raw trimmed content — never pre-escape HTML or SQL characters.
 * BR-NL-FE-011: 422 validation errors surfaced with detail message.
 */
export async function createNote(content: string): Promise<Note> {
  const response = await fetch(`${BASE_URL}/notes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ content }),
  });
  return handleResponse<Note>(response);
}

/**
 * BR-NL-FE-007: uses HTTP DELETE — never GET.
 * BR-NL-FE-011: 404 propagated as ApiError with status 404.
 */
export async function deleteNote(id: number): Promise<void> {
  const response = await fetch(`${BASE_URL}/notes/${id}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  });
  await handleResponse<void>(response);
}