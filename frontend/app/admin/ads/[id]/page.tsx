// src/app/admin/ads/[id]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchAd } from '@/services/adsService'; // same combined service
import { useAuth } from '@/hooks/useAuth';
import type { AdOut } from '@/services/adsService';

export default function AdminAdDetailPage() {
  const { id } = useParams() as { id: string };
  const { user, isHydrated } = useAuth();
  const router = useRouter();
  const [ad, setAd] = useState<AdOut | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!isHydrated) return;
    if (user?.role?.name !== 'superadmin') {
      router.replace('/');
      return;
    }
    (async () => {
      try {
        const data = await fetchAd(id);
        setAd(data);
      } catch (e: any) {
        setErr(e?.response?.data?.detail || 'Failed to load ad');
      }
    })();
  }, [id, isHydrated, user, router]);

  if (!isHydrated) return null;
  if (err) return <div className="p-6 text-red-600">{err}</div>;
  if (!ad) return <div className="p-6">Loading…</div>;

  return (
    <main className="mx-auto max-w-3xl p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Ad Detail</h1>
        <Link href={`/admin/ads/${ad.id}/edit`} className="text-blue-600 underline">Edit</Link>
      </div>

      <div className="rounded border p-4 space-y-2">
        <div><span className="font-medium">Advertiser:</span> {ad.advertiser_name}</div>
        <div><span className="font-medium">Active:</span> {ad.active ? 'Yes' : 'No'}</div>
        <div><span className="font-medium">Weight:</span> {ad.weight}</div>
        <div><span className="font-medium">Destination:</span> {ad.destination_url}</div>
        {ad.image_url && (
          <div className="mt-2">
            <img src={ad.image_url} alt="Ad" className="max-h-40 rounded border" />
          </div>
        )}
        <div className="mt-2">
          <div className="font-medium mb-1">Content</div>
          <div className="rounded border p-2 whitespace-pre-wrap">{ad.ad_content}</div>
        </div>
        <div className="text-sm text-gray-500">
          Created: {new Date(ad.created_at).toLocaleString()} • Updated: {new Date(ad.updated_at).toLocaleString()}
        </div>
      </div>
    </main>
  );
}
