// src/components/ads/AdCard.tsx
"use client";
import { AdOut } from "@/services/adsService";

export default function AdCard({ ad }: { ad: AdOut }) {
  const onClick = () => {
    // TODO: when you add /ads/click tracking, call it here
    // recordClick(ad.id, 'sidebar'); 
  };

  return (
    <a
      href={ad.destination_url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onClick}
      className="group block w-full overflow-hidden rounded-2xl border border-border-soft bg-surface-muted/60 p-4 transition-all hover:border-primary/40 hover:shadow-soft"
    >
      <div className="flex items-center gap-4">
        {ad.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={ad.image_url}
            alt={ad.advertiser_name}
            className="h-16 w-24 shrink-0 rounded-xl border border-border-soft object-contain"
          />
        ) : null}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-text">{ad.advertiser_name}</span>
            {/* Labelled, quietly: an ad that reads as editorial content is the
                one thing a reading app can't afford. */}
            <span className="rounded-full border border-border-soft px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-text-subtle">
              Ad
            </span>
          </div>
          <div className="mt-1 line-clamp-2 text-xs text-text-light">{ad.ad_content}</div>
        </div>
        <span
          aria-hidden="true"
          className="shrink-0 text-primary opacity-0 transition-opacity group-hover:opacity-100"
        >
          →
        </span>
      </div>
    </a>
  );
}
