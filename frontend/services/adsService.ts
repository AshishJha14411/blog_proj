import api from "@/lib/axios";

export interface ServedAd {
  id: number;
  advertiser_name: string;
  ad_content: string;        // HTML or text
  destination_url: string;
}

export async function serveAd(slot: string, postId?: number) {
  const { data } = await api.get<{ ad: ServedAd | null }>("/ads/serve", {
    params: { slot, post_id: postId },
  });
  return data.ad;
}

export async function recordImpression(adId: number, slot: string, postId?: number) {
  try {
    await api.post("/ads/impression", { ad_id: adId, slot, post_id: postId });
  } catch { /* best effort */ }
}

export async function recordClick(adId: number, slot?: string, postId?: number) {
  try {
    await api.post("/ads/click", { ad_id: adId, slot, post_id: postId });
  } catch { /* best effort */ }
}
