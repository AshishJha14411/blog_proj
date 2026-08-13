// src/app/admin/ads/[id]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchAd } from '@/services/adsService'; // same combined service
import Badge from '@/components/ui/Badge';
import PageHeader from '@/components/ui/PageHeader';
import { useAuth } from '@/hooks/useAuth';
import type { AdOut } from '@/services/adsService';
import { getErrorMessage } from '@/lib/errors';

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
      } catch (e) {
        setErr(getErrorMessage(e, 'Failed to load ad'));
      }
    })();
  }, [id, isHydrated, user, router]);

  if (!isHydrated) return null;
  if (err) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <p className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
          {err}
        </p>
      </main>
    );
  }
  if (!ad) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton mt-8 h-64 rounded-2xl" />
      </main>
    );
  }

  const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="flex flex-wrap gap-2 border-b border-border-soft py-3 last:border-b-0">
      <span className="w-32 shrink-0 text-xs font-semibold uppercase tracking-wider text-text-subtle">
        {label}
      </span>
      <span className="min-w-0 flex-1 break-words text-sm text-text-light">{children}</span>
    </div>
  );

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <PageHeader
        eyebrow="Admin"
        title="Ad Detail"
        actions={
          <Link
            href={`/admin/ads/${ad.id}/edit`}
            className="rounded-full border border-border-soft bg-surface px-5 py-2.5 text-sm font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong"
          >
            Edit
          </Link>
        }
      />

      <div className="rounded-2xl border border-border-soft bg-surface p-6 shadow-soft">
        <Row label="Advertiser">{ad.advertiser_name}</Row>
        <Row label="Active">
          {ad.active ? <Badge tone="success" dot>Live</Badge> : <Badge tone="neutral">Paused</Badge>}
        </Row>
        <Row label="Weight">{ad.weight}</Row>
        <Row label="Destination">
          <a
            href={ad.destination_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-strong hover:underline"
          >
            {ad.destination_url}
          </a>
        </Row>
        {ad.image_url && (
          <Row label="Image">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={ad.image_url}
              alt="Ad"
              className="max-h-40 rounded-xl border border-border-soft"
            />
          </Row>
        )}
        <Row label="Content">
          <span className="whitespace-pre-wrap">{ad.ad_content}</span>
        </Row>
        <Row label="Timestamps">
          Created {new Date(ad.created_at).toLocaleString()} · Updated{' '}
          {new Date(ad.updated_at).toLocaleString()}
        </Row>
      </div>
    </main>
  );
}
