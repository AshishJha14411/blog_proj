// src/app/admin/ads/page.tsx
"use client";
import { useEffect, useState } from "react";
import { AdOut, fetchAds, adminDeleteAd } from "@/services/adsService";
import Link from "next/link";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";

export default function AdminAdsPage() {
  const [rows, setRows] = useState<AdOut[]>([]);
  const [loading, setLoading] = useState(true);
 const { user, isHydrated } = useAuth();
 const router = useRouter();
  useEffect(() => {
    fetchAds(100, 0).then(({ items }) => setRows(items)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
      // 1) Don’t do anything until hydration is complete
      if (!isHydrated) return;

      // 2) If we don’t know the user yet, wait (don’t redirect)
      if (!user) return;

      // 3) Now we can decide based on the actual role
      const isModerator = user.role?.name === 'superadmin';

      if (!isModerator) {
        // Use replace to avoid back button bouncing
        router.replace('/');
        return;
      }

    }, [isHydrated, user, router]);
  const remove = async (id: string) => {
    await adminDeleteAd(id);
    setRows((r) => r.filter((x) => x.id !== id));
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-14">
      <PageHeader
        eyebrow="Admin"
        title="Ads"
        description="Sponsored slots shown between stories."
        actions={
          <Link
            href="/admin/ads/new"
            className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-all hover:-translate-y-0.5 hover:bg-primary-light"
          >
            New Ad
          </Link>
        }
      />

      {loading ? (
        <div className="skeleton h-56 rounded-2xl" />
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-border-soft bg-surface shadow-soft">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-surface-muted text-left text-xs uppercase tracking-wider text-text-subtle">
              <tr>
                <th className="p-3 font-semibold">Advertiser</th>
                <th className="p-3 font-semibold">Active</th>
                <th className="p-3 font-semibold">Weight</th>
                <th className="p-3 font-semibold">Created</th>
                <th className="p-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((ad) => (
                <tr key={ad.id} className="border-t border-border-soft transition-colors hover:bg-primary/5">
                  <td className="p-3 font-medium text-text">{ad.advertiser_name}</td>
                  <td className="p-3">
                    {ad.active ? (
                      <Badge tone="success" dot>Live</Badge>
                    ) : (
                      <Badge tone="neutral">Paused</Badge>
                    )}
                  </td>
                  <td className="p-3 text-text-light">{ad.weight}</td>
                  <td className="p-3 whitespace-nowrap text-text-subtle">
                    {new Date(ad.created_at).toLocaleString()}
                  </td>
                  <td className="space-x-3 p-3 text-right">
                    <Link
                      href={`/admin/ads/${ad.id}`}
                      className="font-medium text-primary-strong hover:underline"
                    >
                      Edit
                    </Link>
                    <button onClick={() => remove(ad.id)} className="font-medium text-red-500 hover:underline">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td className="p-6 text-center text-text-subtle" colSpan={5}>
                    No ads yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
