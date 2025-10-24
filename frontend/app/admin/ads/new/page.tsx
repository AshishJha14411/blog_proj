// app/admin/ads/new/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { adminCreateAd } from '@/services/adsService';

export default function AdminCreateAdPage() {
  // 1) HOOKS: always called, in the same order, no conditions
  const router = useRouter();
  const { isHydrated, user } = useAuth();

  // form state (always created; not inside conditions)
  const [advertiserName, setAdvertiserName] = useState('');
  const [adContent, setAdContent] = useState('');
  const [destinationUrl, setDestinationUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [weight, setWeight] = useState(1);
  const [active, setActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 2) Compute auth flag in a memo (no side effects during render)
  const isAuthorized = useMemo(
    () => !!user && user.role?.name === 'superadmin',
    [user]
  );

  // 3) Redirect only after we are hydrated & confirmed not authorized
  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthorized) {
      router.replace('/'); // safe: executed after render
    }
  }, [isHydrated, isAuthorized, router]);

  // 4) Avoid hydration mismatches:
  //    Before hydration we render nothing.
  //    If not authorized after hydration, show a stable placeholder.
  if (!isHydrated) return null;
  if (!isAuthorized) {
    return <div className="p-6 text-sm text-gray-600">Redirecting…</div>;
  }

  // 5) Normal render (now safe)
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await adminCreateAd({
        advertiser_name: advertiserName,
        ad_content: adContent,
        destination_url: destinationUrl,
        image_url: imageUrl || undefined,
        weight,
        active,
      });
      router.replace('/admin/ads'); // navigate after success
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create ad.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Create Ad</h1>

      {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Advertiser Name</label>
          <input className="mt-1 w-full rounded border p-2"
                 value={advertiserName} onChange={(e) => setAdvertiserName(e.target.value)} />
        </div>

        <div>
          <label className="block text-sm font-medium">Destination URL</label>
          <input className="mt-1 w-full rounded border p-2"
                 value={destinationUrl} onChange={(e) => setDestinationUrl(e.target.value)} placeholder="https://…" />
        </div>

        <div>
          <label className="block text-sm font-medium">Image URL (optional)</label>
          <input className="mt-1 w-full rounded border p-2"
                 value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://…" />
        </div>

        <div>
          <label className="block text-sm font-medium">Ad Content</label>
          <textarea className="mt-1 w-full rounded border p-2 h-32"
                    value={adContent} onChange={(e) => setAdContent(e.target.value)} />
        </div>

        <div className="flex gap-4 items-center">
          <div>
            <label className="block text-sm font-medium">Weight</label>
            <input type="number" min={1} className="mt-1 w-24 rounded border p-2"
                   value={weight} onChange={(e) => setWeight(parseInt(e.target.value || '1', 10))} />
          </div>
          <label className="inline-flex gap-2 items-center mt-6">
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            Active
          </label>
        </div>

        <button disabled={saving}
                className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">
          {saving ? 'Saving…' : 'Create Ad'}
        </button>
      </form>
    </main>
  );
}
