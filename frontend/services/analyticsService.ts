import api from "@/lib/axios";

/**
 * Analytics API client.
 *
 * WHY THIS FILE WAS REWRITTEN: it previously called `/analytics/series` and
 * `/analytics/ads_ctr`, neither of which exists on the backend — the response
 * schemas (`AnalyticsSeries`, `AdsCtrRow`) were defined in
 * `app/schemas/analytics.py` but no route was ever wired to them. Both requests
 * 404'd, the page had no `.catch`, and every stat card silently rendered `0`
 * while production actually held 8 posts and 6 users for the period.
 *
 * These functions now map 1:1 onto routes that exist in `app/routes/analytics.py`.
 * All of them are gated behind `Perm.ANALYTICS_VIEW` (moderator or superadmin).
 */

/** A single point in a daily series. `running_total` is a SQL window function. */
export interface DayCount {
  day: string; // ISO date (YYYY-MM-DD)
  count: number;
  running_total: number;
}

export interface FlagsBreakdown {
  total: number;
  ai_flags: number;
  human_flags: number;
}

export interface AuditLog {
  id: string;
  actor_user_id: string;
  action: string;
  target_type?: string | null;
  target_id?: string | null;
  before_state?: Record<string, unknown> | null;
  after_state?: Record<string, unknown> | null;
  timestamp: string;
}

/** Stories created per day, zero-filled across the whole window by the backend. */
export async function getPostsDaily(days = 30): Promise<DayCount[]> {
  const { data } = await api.get<{ stats: DayCount[] }>("/analytics/posts/daily", {
    params: { days },
  });
  return data.stats;
}

/** Signups per day. */
export async function getUsersDaily(days = 30): Promise<DayCount[]> {
  const { data } = await api.get<{ stats: DayCount[] }>("/analytics/users/daily", {
    params: { days },
  });
  return data.stats;
}

/** Ad clicks per day. */
export async function getClicksDaily(days = 30): Promise<DayCount[]> {
  const { data } = await api.get<{ stats: DayCount[] }>("/analytics/clicks", {
    params: { days },
  });
  return data.stats;
}

/** Totals split by who raised the flag — the automated scan or a human. */
export async function getFlagsBreakdown(): Promise<FlagsBreakdown> {
  const { data } = await api.get<FlagsBreakdown>("/analytics/flags");
  return data;
}

/** Recent moderation actions from the audit log. */
export async function getModerationLogs(limit = 25, offset = 0): Promise<AuditLog[]> {
  const { data } = await api.get<{ logs: AuditLog[] }>("/analytics/moderation", {
    params: { limit, offset },
  });
  return data.logs;
}
