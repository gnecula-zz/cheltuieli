import { useEffect, useState } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { useAuth } from "../App";
import ExpenseForm, { type ExpensePayload } from "../components/ExpenseForm";
import Modal from "../components/Modal";
import { api, ApiError } from "../lib/api";
import { money, monthEnd, monthStart, sourceLabel } from "../lib/format";
import type { Expense, User } from "../lib/types";

export default function Expenses() {
  const { user, categories } = useAuth();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [categoryId, setCategoryId] = useState("");
  const [shared, setShared] = useState("");
  const [person, setPerson] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Expense[]>([]);
  const [members, setMembers] = useState<User[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [error, setError] = useState("");

  const load = () => {
    const params = new URLSearchParams({
      from: monthStart(year, month),
      to: monthEnd(year, month),
    });
    if (categoryId) params.set("category_id", categoryId);
    if (shared === "1") params.set("shared", "true");
    if (shared === "0") params.set("shared", "false");
    if (person) params.set("user_id", person);
    if (q) params.set("q", q);
    api<Expense[]>(`/expenses?${params}`).then(setRows);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month, categoryId, shared, person]);

  useEffect(() => {
    if (user?.role === "admin") {
      api<User[]>("/users").then(setMembers).catch(() => setMembers([]));
    }
  }, [user]);

  const save = async (payload: ExpensePayload) => {
    setError("");
    try {
      if (editing) {
        await api(`/expenses/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        await api("/expenses", { method: "POST", body: JSON.stringify(payload) });
      }
      setOpen(false);
      setEditing(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Salvare eșuată");
    }
  };

  const remove = async (row: Expense) => {
    if (!confirm(`Ștergi cheltuiala ${row.merchant || money(row.amount)}?`)) return;
    await api(`/expenses/${row.id}`, { method: "DELETE" });
    load();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-ink/55">Cheltuieli</p>
          <h1 className="font-display text-3xl">Lista lunii</h1>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setError("");
            setOpen(true);
          }}
          className="flex min-h-11 items-center gap-2 rounded-2xl bg-forest px-4 font-semibold text-sand"
        >
          <Plus size={18} /> Adaugă
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        <select className="rounded-xl border border-black/10 bg-white px-3 py-3" value={`${year}-${month}`} onChange={(e) => {
          const [y, m] = e.target.value.split("-").map(Number);
          setYear(y);
          setMonth(m);
        }}>
          {monthOptions().map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select className="rounded-xl border border-black/10 bg-white px-3 py-3" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Toate categoriile</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select className="rounded-xl border border-black/10 bg-white px-3 py-3" value={shared} onChange={(e) => setShared(e.target.value)}>
          <option value="">Personal + comun</option>
          <option value="0">Doar personale</option>
          <option value="1">Doar comune</option>
        </select>
        {user?.role === "admin" ? (
          <select className="rounded-xl border border-black/10 bg-white px-3 py-3" value={person} onChange={(e) => setPerson(e.target.value)}>
            <option value="">Toți</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        ) : (
          <div className="hidden md:block" />
        )}
        <form
          className="col-span-2 flex items-center gap-2 rounded-xl border border-black/10 bg-white px-3 md:col-span-1"
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
        >
          <Search size={16} className="text-ink/40" />
          <input className="min-h-11 w-full bg-transparent outline-none" placeholder="Caută" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
      </div>

      {rows.length === 0 ? (
        <p className="rounded-3xl bg-paper p-6 text-sm text-ink/55 shadow-card">Nicio cheltuială pe filtrele alese.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li key={row.id} className="flex items-start gap-1 rounded-2xl bg-paper px-4 py-3 shadow-card">
              <button
                type="button"
                onClick={() => {
                  setEditing(row);
                  setError("");
                  setOpen(true);
                }}
                className="min-w-0 flex-1 text-left"
              >
                <p className="truncate font-medium">{row.merchant || row.description || "Fără nume"}</p>
                <p className="mt-0.5 text-xs text-ink/50">
                  {row.date} · {row.category_icon} {row.category_name || "Fără categorie"} · {sourceLabel(row.source)}
                  {row.is_shared ? " · Comună" : " · Personală"}
                  {user?.role === "admin" ? ` · ${row.user_name}` : ""}
                </p>
              </button>
              <span className="shrink-0 font-display text-lg">{money(row.amount, row.currency)}</span>
              <button
                type="button"
                onClick={() => remove(row)}
                className="rounded-full p-2 text-ink/40 hover:bg-sand hover:text-clay"
                aria-label="Șterge"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {open ? (
        <Modal
          title={editing ? "Editează cheltuiala" : "Cheltuială nouă"}
          onClose={() => {
            setOpen(false);
            setEditing(null);
          }}
        >
          <ExpenseForm
            key={editing?.id || "new"}
            categories={categories}
            initial={editing || undefined}
            submitLabel={editing ? "Salvează" : "Adaugă"}
            onSubmit={save}
            error={error}
          />
        </Modal>
      ) : null}
    </div>
  );
}

function monthOptions() {
  const now = new Date();
  const opts: { value: string; label: string }[] = [];
  for (let i = 0; i < 18; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${d.getMonth() + 1}`;
    const label = new Intl.DateTimeFormat("ro-RO", { month: "long", year: "numeric" }).format(d);
    opts.push({ value, label });
  }
  return opts;
}
