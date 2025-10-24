// src/components/ads/AdSlot.tsx
"use client";

import { useEffect, useState } from "react";
import { AdOut, fetchAds, pickWeightedAd } from "@/services/adsService";
import AdCard from "./AdCard";

export default function AdSlot({ limit = 20, className = "" }: { limit?: number; className?: string }) {
  const [ad, setAd] = useState<AdOut | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { items } = await fetchAds(limit, 0);
        if (cancelled) return;
        const chosen = pickWeightedAd(items);
        setAd(chosen);
        // TODO: when you add /ads/impression on the backend:
        // if (chosen) recordImpression(chosen.id, 'slot_name');
      } catch (e) {
        setAd(null);
      }
    })();
    return () => { cancelled = true; };
  }, [limit]);

  if (!ad) return null;
  return (
    <div className={className}>
      <AdCard ad={ad} />
    </div>
  );
}
