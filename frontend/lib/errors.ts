import axios from 'axios';

/**
 * Extract a user-facing message from a caught error. Backend errors arrive
 * as axios responses with a `detail` field (FastAPI's HTTPException shape);
 * anything else falls back to a generic Error message or the caller-supplied
 * default. Centralized so callers don't need `catch (e: any)`.
 */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
