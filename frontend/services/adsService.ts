import api from "@/lib/axios";

/** Shared types that match your Pydantic schema */
export interface AdOut {
  id: string;
  advertiser_name: string;
  ad_content: string;        // text or HTML snippet
  destination_url: string;   // HttpUrl
  image_url?: string | null; // HttpUrl
  weight: number;
  active: boolean;
  start_at?: string | null;
  end_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdListResponse {
  total: number;
  limit: number;
  offset: number;
  items: AdOut[];
}

export interface AdCreate {
  advertiser_name: string;
  ad_content: string;
  destination_url: string;
  image_url?: string | null;
  tag_names?: string[];      // backend ignores for now
  weight?: number;           // default 1
  active?: boolean;          // default true
  start_at?: string | null;
  end_at?: string | null;
}

export interface AdUpdate {
  advertiser_name?: string;
  ad_content?: string;
  destination_url?: string;
  image_url?: string | null;
  tag_names?: string[];
  weight?: number;
  active?: boolean;
  start_at?: string | null;
  end_at?: string | null;
}

/* ------------------------- Public APIs ------------------------- */

export async function fetchAds(limit = 20, offset = 0): Promise<AdListResponse> {
  const { data } = await api.get<AdListResponse>("/ads", { params: { limit, offset } });
  return data;
}

export async function fetchAd(id: string): Promise<AdOut> {
  const { data } = await api.get<AdOut>(`/ads/${id}`);
  return data;
}

/**
 * Client-side helper: pick a single ad using weighted random.
 * (Filters to active + within start/end window.)
 */
export function pickWeightedAd(ads: AdOut[], now = new Date()): AdOut | null {
  const eligible = ads.filter((ad) => {
    if (!ad.active) return false;
    const startsOk = !ad.start_at || new Date(ad.start_at) <= now;
    const endsOk = !ad.end_at || new Date(ad.end_at) >= now;
    return startsOk && endsOk;
  });
  if (eligible.length === 0) return null;

  const totalWeight = eligible.reduce((sum, a) => sum + Math.max(1, a.weight ?? 1), 0);
  let r = Math.random() * totalWeight;
  for (const ad of eligible) {
    r -= Math.max(1, ad.weight ?? 1);
    if (r <= 0) return ad;
  }
  return eligible[eligible.length - 1];
}

/* ------------------------- Admin APIs ------------------------- */
/** These require auth; axios instance already attaches the token. */

export async function adminCreateAd(payload: AdCreate): Promise<AdOut> {
  const { data } = await api.post<AdOut>("/admin/ads", payload);
  return data;
}

export async function adminUpdateAd(id: string, payload: AdUpdate): Promise<AdOut> {
  const { data } = await api.patch<AdOut>(`/admin/ads/${id}`, payload);
  return data;
}

export async function adminDeleteAd(id: string): Promise<void> {
  await api.delete(`/admin/ads/${id}`);
}
