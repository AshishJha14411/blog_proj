// src/app/admin/ads/page.tsx
"use client";
import { useEffect, useState } from "react";
import { AdOut, fetchAds, adminDeleteAd } from "@/services/adsService";
import Link from "next/link";
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

  if (loading) return <div className="p-6">Loading ads…</div>;

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-semibold">Ads</h1>
        <Link href="/admin/ads/new" className="px-3 py-2 rounded bg-black text-white">New Ad</Link>
      </div>
      <div className="overflow-auto border rounded">
        <table className="min-w-[800px] w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">Advertiser</th>
              <th className="text-left p-2">Active</th>
              <th className="text-left p-2">Weight</th>
              <th className="text-left p-2">Created</th>
              <th className="text-right p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((ad) => (
              <tr key={ad.id} className="border-t">
                <td className="p-2">{ad.advertiser_name}</td>
                <td className="p-2">{ad.active ? "Yes" : "No"}</td>
                <td className="p-2">{ad.weight}</td>
                <td className="p-2">{new Date(ad.created_at).toLocaleString()}</td>
                <td className="p-2 text-right space-x-2">
                  <Link href={`/admin/ads/${ad.id}`} className="underline">Edit</Link>
                  <button onClick={() => remove(ad.id)} className="text-red-600 underline">Delete</button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td className="p-3 text-gray-500" colSpan={5}>No ads yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
