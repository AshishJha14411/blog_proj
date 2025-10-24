import api from "@/lib/axios";

export interface DailyMetric {
  day: string; // ISO date
  new_users: number;
  logins: number;
  posts_created: number;
  flags_created: number;
  ai_flags: number;
  human_flags: number;
  dau: number;
  posts_viewed: number;
  likes: number;
  comments: number;
  ad_impressions: number;
  ad_clicks: number;
}

export async function getSeries(start: string, end: string, bucket = "day") {
  const { data } = await api.get<{ items: DailyMetric[] }>(`/analytics/series`, {
    params: { start, end, bucket },
  });
  return data.items;
}

export interface AdCtrRow {
  ad_id: string;
  slot: string | null;
  impressions: number;
  clicks: number;
  ctr: number;
}

export async function getAdsCtr(start: string, end: string) {
  const { data } = await api.get<AdCtrRow[]>(`/analytics/ads_ctr`, {
    params: { start, end },
  });
  return data;
}
