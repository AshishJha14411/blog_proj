// src/app/admin/ads/[id]/edit/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchAd, adminUpdateAd, AdUpdate } from '@/services/adsService';
import { useAuth } from '@/hooks/useAuth';

export default function AdminEditAdPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const { user, isHydrated } = useAuth();

  const [form, setForm] = useState<AdUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!isHydrated) return;
    if (user?.role?.name !== 'superadmin') {
      router.replace('/');
      return;
    }
    (async () => {
      try {
        const ad = await fetchAd(id);
        setForm({
          advertiser_name: ad.advertiser_name,
          ad_content: ad.ad_content,
          destination_url: ad.destination_url,
          image_url: ad.image_url || '',
          weight: ad.weight,
          active: ad.active,
        });
      } catch (e: any) {
        setErr(e?.response?.data?.detail || 'Failed to load ad');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, isHydrated, user, router]);

  const onChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type, checked } = e.target as any;
    setForm((f) => ({
      ...f,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      await adminUpdateAd(id, {
        ...form,
        image_url: form.image_url?.trim() || undefined,
        destination_url: form.destination_url?.trim(),
      });
      router.replace('/admin/ads');
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to update ad');
    } finally {
      setSaving(false);
    }
  }

  if (!isHydrated || loading) return <div className="p-8">Loading…</div>;
  if (err) return <div className="p-8 text-red-600">{err}</div>;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold mb-6">Edit Ad</h1>

      {err && <div className="mb-4 rounded bg-red-50 p-3 text-red-700 text-sm">{err}</div>}

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">Advertiser Name</label>
          <input
            name="advertiser_name"
            value={form.advertiser_name || ''}
            onChange={onChange}
            className="w-full rounded border p-2"
            required
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Destination URL</label>
          <input
            name="destination_url"
            value={form.destination_url || ''}
            onChange={onChange}
            className="w-full rounded border p-2"
            required
            type="url"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Image URL (optional)</label>
          <input
            name="image_url"
            value={form.image_url || ''}
            onChange={onChange}
            className="w-full rounded border p-2"
            type="url"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Ad Content</label>
          <textarea
            name="ad_content"
            value={form.ad_content || ''}
            onChange={onChange}
            className="w-full rounded border p-2 min-h-[120px]"
          />
        </div>

        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm mb-1">Weight</label>
            <input
              name="weight"
              value={(form.weight as any) ?? 1}
              onChange={onChange}
              className="w-28 rounded border p-2"
              type="number"
              min={1}
            />
          </div>

          <label className="flex items-center gap-2 mt-6">
            <input
              type="checkbox"
              name="active"
              checked={!!form.active}
              onChange={onChange}
            />
            <span className="text-sm">Active</span>
          </label>
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </form>
    </main>
  );
}
