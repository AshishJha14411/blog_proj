"use client";

import { useEffect, useMemo, useState } from "react";
import { getAdsCtr, getSeries, DailyMetric } from "@/services/analyticsService";
import { useModGuard } from "@/hooks/useModGuard";

function iso(d: Date) { return d.toISOString().slice(0,10); }

export default function AdminAnalyticsPage() {
  const { isMod } = useModGuard();
  const [start, setStart] = useState(iso(new Date(Date.now() - 30*864e5)));
  const [end, setEnd] = useState(iso(new Date()));
  const [series, setSeries] = useState<DailyMetric[]>([]);
  const [ctrRows, setCtrRows] = useState<any[]>([]);

  useEffect(() => {
    if (!isMod) return;
    getSeries(start, end, "day").then(setSeries);
    getAdsCtr(start, end).then(setCtrRows);
  }, [start, end, isMod]);

  const totals = useMemo(() => {
    return series.reduce((a, r) => ({
      users: a.users + r.new_users,
      posts: a.posts + r.posts_created,
      flags: a.flags + r.flags_created,
      ai_flags: a.ai_flags + r.ai_flags,
      human_flags: a.human_flags + r.human_flags,
    }), { users:0, posts:0, flags:0, ai_flags:0, human_flags:0 });
  }, [series]);

  if (!isMod) return null;

  return (
    <main className="mx-auto max-w-6xl p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Analytics</h1>

      <div className="flex gap-2">
        <input type="date" value={start} onChange={(e)=>setStart(e.target.value)} className="border rounded p-2"/>
        <input type="date" value={end} onChange={(e)=>setEnd(e.target.value)} className="border rounded p-2"/>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="New Users" value={totals.users}/>
        <StatCard label="Posts" value={totals.posts}/>
        <StatCard label="Flags" value={totals.flags}/>
        <StatCard label="AI Flags" value={totals.ai_flags}/>
        <StatCard label="Human Flags" value={totals.human_flags}/>
      </div>

      <section>
        <h2 className="font-medium mb-2">Posts / day</h2>
        <MiniTable rows={series.map(s => ({ day: s.day, value: s.posts_created }))}/>
      </section>

      <section>
        <h2 className="font-medium mb-2">Users / day</h2>
        <MiniTable rows={series.map(s => ({ day: s.day, value: s.new_users }))}/>
      </section>

      <section>
        <h2 className="font-medium mb-2">Ads CTR</h2>
        <table className="w-full text-sm border">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-2 text-left">Ad ID</th>
              <th className="p-2 text-left">Slot</th>
              <th className="p-2 text-right">Impressions</th>
              <th className="p-2 text-right">Clicks</th>
              <th className="p-2 text-right">CTR</th>
            </tr>
          </thead>
          <tbody>
            {ctrRows.map((r, i) => (
              <tr key={i} className="border-t">
                <td className="p-2">{r.ad_id}</td>
                <td className="p-2">{r.slot ?? "—"}</td>
                <td className="p-2 text-right">{r.impressions}</td>
                <td className="p-2 text-right">{r.clicks}</td>
                <td className="p-2 text-right">{(r.ctr * 100).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="border rounded p-3 bg-white">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}

function MiniTable({ rows }: { rows: { day: string; value: number }[] }) {
  return (
    <table className="w-full text-sm border">
      <thead className="bg-gray-50"><tr><th className="p-2 text-left">Day</th><th className="p-2 text-right">Value</th></tr></thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.day} className="border-t">
            <td className="p-2">{r.day}</td>
            <td className="p-2 text-right">{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
