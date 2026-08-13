// app/admin/ads/new/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';
import Input from '@/components/ui/Input';
import PageHeader from '@/components/ui/PageHeader';
import Textarea from '@/components/ui/Textarea';
import { useAuth } from '@/hooks/useAuth';
import { adminCreateAd } from '@/services/adsService';
import { getErrorMessage } from '@/lib/errors';

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
    return <div className="p-6 text-sm text-text-subtle">Redirecting…</div>;
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
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create ad.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <PageHeader eyebrow="Admin" title="Create Ad" />

      {error && (
        <div className="mb-6 rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
          {error}
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8"
      >
        <div>
          <FormLabel htmlFor="ad-advertiser">Advertiser Name</FormLabel>
          <Input
            id="ad-advertiser"
            value={advertiserName}
            onChange={(e) => setAdvertiserName(e.target.value)}
          />
        </div>

        <div>
          <FormLabel htmlFor="ad-destination">Destination URL</FormLabel>
          <Input
            id="ad-destination"
            value={destinationUrl}
            onChange={(e) => setDestinationUrl(e.target.value)}
            placeholder="https://…"
          />
        </div>

        <div>
          <FormLabel htmlFor="ad-image">Image URL (optional)</FormLabel>
          <Input
            id="ad-image"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            placeholder="https://…"
          />
        </div>

        <div>
          <FormLabel htmlFor="ad-content">Ad Content</FormLabel>
          <Textarea
            id="ad-content"
            rows={5}
            value={adContent}
            onChange={(e) => setAdContent(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-end gap-6">
          <div>
            <FormLabel htmlFor="ad-weight">Weight</FormLabel>
            <Input
              id="ad-weight"
              type="number"
              min={1}
              className="w-28"
              value={weight}
              onChange={(e) => setWeight(parseInt(e.target.value || '1', 10))}
            />
          </div>
          <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-border-soft bg-surface-muted/60 px-4 py-2.5">
            <input
              type="checkbox"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              className="h-4 w-4 accent-[var(--accent-primary)]"
            />
            <span className="text-sm text-text-light">Active</span>
          </label>
        </div>

        <div className="border-t border-border-soft pt-5">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Create Ad'}
          </Button>
        </div>
      </form>
    </main>
  );
}
