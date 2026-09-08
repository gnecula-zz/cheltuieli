import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "../lib/api";
import { money, monthLabel } from "../lib/format";
import type { ReportSummary } from "../lib/types";

export default function Dashboard() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [data, setData] = useState<ReportSummary | null>(null);

  useEffect(() => {
    api<ReportSummary>(`/reports/summary?year=${year}&month=${month}`).then(setData);
  }, [year, month]);

  const shift = (delta: number) => {
    const d = new Date(year, month - 1 + delta, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth() + 1);
  };

  const chart = useMemo(
    () =>
      (data?.by_category || []).map((c) => ({
        name: c.name,
        value: c.total,
        color: c.color,
      })),
    [data],
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-ink/55">Panou</p>
          <h1 className="font-display text-3xl capitalize">{monthLabel(year, month)}</h1>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" className="rounded-full p-2 hover:bg-white" onClick={() => shift(-1)} aria-label="Luna anterioară">
            <ChevronLeft />
          </button>
          <button type="button" className="rounded-full p-2 hover:bg-white" onClick={() => shift(1)} aria-label="Luna următoare">
            <ChevronRight />
          </button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Total lună" value={money(data?.total ?? 0)} />
        <Stat label="Personale" value={money(data?.personal ?? 0)} />
        <Stat label="Comune" value={money(data?.shared ?? 0)} />
      </div>

      <section className="rounded-3xl bg-paper p-5 shadow-card">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl">Pe categorii</h2>
          <Link to="/rapoarte" className="text-sm text-forest underline">
            Rapoarte
          </Link>
        </div>
        {chart.length === 0 ? (
          <EmptyMonth />
        ) : (
          <div className="mt-4 grid items-center gap-4 md:grid-cols-2">
            <div className="h-52">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={chart} dataKey="value" nameKey="name" innerRadius={48} outerRadius={80} paddingAngle={2}>
                    {chart.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="space-y-2">
              {(data?.by_category || []).slice(0, 6).map((c) => (
                <li key={c.name} className="flex items-center justify-between gap-3 text-sm">
                  <span className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full" style={{ background: c.color }} />
                    {c.icon} {c.name}
                  </span>
                  <span className="font-medium">{money(c.total)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {data?.budgets?.length ? (
        <section className="rounded-3xl bg-paper p-5 shadow-card">
          <h2 className="font-display text-xl">Bugete</h2>
          <ul className="mt-3 space-y-3">
            {data.budgets.map((b) => {
              const pct = b.amount > 0 ? Math.min(100, Math.round((b.spent / b.amount) * 100)) : 0;
              const over = b.spent > b.amount && b.amount > 0;
              return (
                <li key={b.category_id}>
                  <div className="flex justify-between text-sm">
                    <span>{b.category_name}</span>
                    <span className={over ? "text-clay" : ""}>
                      {money(b.spent)} / {money(b.amount)}
                    </span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-sand">
                    <div className={`h-full ${over ? "bg-clay" : "bg-forest"}`} style={{ width: `${pct}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <Link to="/cheltuieli" className="rounded-2xl bg-forest px-5 py-4 text-center font-semibold text-sand">
          Adaugă cheltuială
        </Link>
        <Link to="/import" className="rounded-2xl bg-white px-5 py-4 text-center font-semibold text-forest shadow-card">
          Importă bon / PDF
        </Link>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl bg-paper p-4 shadow-card">
      <p className="text-sm text-ink/55">{label}</p>
      <p className="mt-1 font-display text-2xl">{value}</p>
    </div>
  );
}

function EmptyMonth() {
  return (
    <p className="mt-6 text-sm text-ink/55">
      Nicio cheltuială luna asta. Adaugă una manual sau importă un bon / extras.
    </p>
  );
}
