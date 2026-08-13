// src/app/admin/ads/[id]/edit/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchAd, adminUpdateAd, AdUpdate } from '@/services/adsService';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';
import Input from '@/components/ui/Input';
import PageHeader from '@/components/ui/PageHeader';
import Textarea from '@/components/ui/Textarea';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';

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
      } catch (e) {
        setErr(getErrorMessage(e, 'Failed to load ad'));
      } finally {
        setLoading(false);
      }
    })();
  }, [id, isHydrated, user, router]);

  const onChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
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
    } catch (e) {
      setErr(getErrorMessage(e, 'Failed to update ad'));
    } finally {
      setSaving(false);
    }
  }

  if (!isHydrated || loading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <div className="skeleton h-8 w-40" />
        <div className="skeleton mt-8 h-96 rounded-2xl" />
      </main>
    );
  }
  if (err) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <p className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
          {err}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <PageHeader eyebrow="Admin" title="Edit Ad" />

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8"
      >
        <div>
          <FormLabel htmlFor="edit-advertiser">Advertiser Name</FormLabel>
          <Input
            id="edit-advertiser"
            name="advertiser_name"
            value={form.advertiser_name || ''}
            onChange={onChange}
            required
          />
        </div>

        <div>
          <FormLabel htmlFor="edit-destination">Destination URL</FormLabel>
          <Input
            id="edit-destination"
            name="destination_url"
            value={form.destination_url || ''}
            onChange={onChange}
            required
            type="url"
          />
        </div>

        <div>
          <FormLabel htmlFor="edit-image">Image URL (optional)</FormLabel>
          <Input
            id="edit-image"
            name="image_url"
            value={form.image_url || ''}
            onChange={onChange}
            type="url"
          />
        </div>

        <div>
          <FormLabel htmlFor="edit-content">Ad Content</FormLabel>
          <Textarea
            id="edit-content"
            name="ad_content"
            rows={5}
            value={form.ad_content || ''}
            onChange={onChange}
          />
        </div>

        <div className="flex flex-wrap items-end gap-6">
          <div>
            <FormLabel htmlFor="edit-weight">Weight</FormLabel>
            <Input
              id="edit-weight"
              name="weight"
              value={form.weight ?? 1}
              onChange={onChange}
              className="w-28"
              type="number"
              min={1}
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-border-soft bg-surface-muted/60 px-4 py-2.5">
            <input
              type="checkbox"
              name="active"
              checked={!!form.active}
              onChange={onChange}
              className="h-4 w-4 accent-[var(--accent-primary)]"
            />
            <span className="text-sm text-text-light">Active</span>
          </label>
        </div>

        <div className="border-t border-border-soft pt-5">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </main>
  );
}
