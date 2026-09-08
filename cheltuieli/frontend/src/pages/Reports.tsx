import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { apiUrl } from "../lib/base";
import { money, monthLabel } from "../lib/format";
import type { ReportSummary } from "../lib/types";

export default function Reports() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState<number | "all">(now.getMonth() + 1);
  const [data, setData] = useState<ReportSummary | null>(null);

  useEffect(() => {
    const qs = month === "all" ? `year=${year}` : `year=${year}&month=${month}`;
    api<ReportSummary>(`/reports/summary?${qs}`).then(setData);
  }, [year, month]);

  const exportCsv = () => {
    const qs = month === "all" ? `year=${year}` : `year=${year}&month=${month}`;
    window.location.href = apiUrl(`/reports/export.csv?${qs}`);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-ink/55">Rapoarte</p>
          <h1 className="font-display text-3xl">
            {month === "all" ? `Anul ${year}` : monthLabel(year, month)}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <select className="rounded-xl border border-black/10 bg-white px-3 py-3" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {Array.from({ length: 5 }, (_, i) => now.getFullYear() - i).map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <select
            className="rounded-xl border border-black/10 bg-white px-3 py-3"
            value={month}
            onChange={(e) => setMonth(e.target.value === "all" ? "all" : Number(e.target.value))}
          >
            <option value="all">Tot anul</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>
                {new Intl.DateTimeFormat("ro-RO", { month: "long" }).format(new Date(2000, m - 1, 1))}
              </option>
            ))}
          </select>
          <button type="button" onClick={exportCsv} className="rounded-xl bg-forest px-4 py-3 font-semibold text-sand">
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card label="Total" value={money(data?.total ?? 0)} />
        <Card label="Cheltuieli" value={String(data?.count ?? 0)} />
        <Card label="Comune" value={money(data?.shared ?? 0)} />
      </div>

      <section className="rounded-3xl bg-paper p-5 shadow-card">
        <h2 className="font-display text-xl">Categorii</h2>
        <div className="mt-4 h-64">
          <ResponsiveContainer>
            <BarChart data={data?.by_category || []} layout="vertical" margin={{ left: 16, right: 8 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => money(v)} />
              <Bar dataKey="total" radius={[0, 8, 8, 0]} fill="#1F4D3A" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="grid gap-3 md:grid-cols-2">
        <section className="rounded-3xl bg-paper p-5 shadow-card">
          <h2 className="font-display text-xl">Pe persoană</h2>
          <ul className="mt-3 space-y-2">
            {(data?.by_person || []).map((p) => (
              <li key={p.name} className="flex justify-between text-sm">
                <span>{p.name}</span>
                <span className="font-medium">{money(p.total)}</span>
              </li>
            ))}
            {!data?.by_person?.length ? <li className="text-sm text-ink/50">Nu sunt date.</li> : null}
          </ul>
        </section>
        <section className="rounded-3xl bg-paper p-5 shadow-card">
          <h2 className="font-display text-xl">Comercianți</h2>
          <ul className="mt-3 space-y-2">
            {(data?.by_merchant || []).map((p) => (
              <li key={p.name} className="flex justify-between gap-3 text-sm">
                <span className="truncate">{p.name}</span>
                <span className="shrink-0 font-medium">{money(p.total)}</span>
              </li>
            ))}
            {!data?.by_merchant?.length ? <li className="text-sm text-ink/50">Nu sunt date.</li> : null}
          </ul>
        </section>
      </div>
    </div>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl bg-paper p-4 shadow-card">
      <p className="text-sm text-ink/55">{label}</p>
      <p className="mt-1 font-display text-2xl">{value}</p>
    </div>
  );
}
