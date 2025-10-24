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
      className="block rounded-xl border w-[100%] h-[8rem]  p-3 hover:shadow-md transition"
    >
      {ad.image_url ? (
        <img src={ad.image_url} alt={ad.advertiser_name} className="w-full w-[90%] max-h-[5rem]  rounded-md mb-2 object-contain" />
      ) : null}
      <div className="text-sm font-semibold">{ad.advertiser_name}</div>
      <div className="text-xs text-gray-600 mt-1">{ad.ad_content}</div>
    </a>
  );
}
