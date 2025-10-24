"use client";

import { useEffect, useState } from "react";
import DOMPurify from "isomorphic-dompurify";
import { recordClick, recordImpression, serveAd, ServedAd } from "@/services/adsService";

interface Props {
  slot: string;          // e.g., "HOMEPAGE_SIDEBAR", "POST_INLINE"
  postId?: number;
  className?: string;
  minHeight?: number;    // to avoid layout shift
}

export default function AdSlot({ slot, postId, className, minHeight = 80 }: Props) {
  const [ad, setAd] = useState<ServedAd | null>(null);

  useEffect(() => {
    let mounted = true;
    serveAd(slot, postId).then(async (a) => {
      if (!mounted || !a) return;
      setAd(a);
      recordImpression(a.id, slot, postId);
    });
    return () => { mounted = false; };
  }, [slot, postId]);

  if (!ad) return <div style={{ minHeight }} className={className} />;

  return (
    <div className={`border rounded p-3 bg-white ${className || ""}`} style={{ minHeight }}>
      <div className="text-xs text-gray-500 mb-1">Sponsored · {ad.advertiser_name}</div>
      <div
        className="prose"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(ad.ad_content) }}
      />
      <div className="mt-2">
        <a
          href={ad.destination_url}
          onClick={() => recordClick(ad.id, slot, postId)}
          className="text-sm underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn more
        </a>
      </div>
    </div>
  );
}
