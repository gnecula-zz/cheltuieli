import { useState } from "react";
import { Field, inputClass } from "./Modal";
import type { Category, Expense } from "../lib/types";
import { todayIso } from "../lib/format";

export type ExpensePayload = {
  amount: number;
  currency: string;
  date: string;
  merchant: string;
  description: string;
  vat_amount: number | null;
  payment_method: string;
  is_shared: boolean;
  source: string;
  category_id: number | null;
  invoice_number: string;
  cui: string;
};

export default function ExpenseForm({
  categories,
  initial,
  submitLabel,
  onSubmit,
  error,
}: {
  categories: Category[];
  initial?: Partial<Expense>;
  submitLabel: string;
  onSubmit: (payload: ExpensePayload) => Promise<void>;
  error?: string;
}) {
  const [amount, setAmount] = useState(initial?.amount != null ? String(initial.amount) : "");
  const [vat, setVat] = useState(initial?.vat_amount != null ? String(initial.vat_amount) : "");
  const [date, setDate] = useState(initial?.date || todayIso());
  const [merchant, setMerchant] = useState(initial?.merchant || "");
  const [description, setDescription] = useState(initial?.description || "");
  const [categoryId, setCategoryId] = useState(initial?.category_id ? String(initial.category_id) : "");
  const [payment, setPayment] = useState(initial?.payment_method || "card");
  const [shared, setShared] = useState(Boolean(initial?.is_shared));
  const [invoice, setInvoice] = useState(initial?.invoice_number || "");
  const [cui, setCui] = useState(initial?.cui || "");
  const [busy, setBusy] = useState(false);

  return (
    <form
      className="space-y-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          await onSubmit({
            amount: Number(amount.replace(",", ".")),
            currency: "RON",
            date,
            merchant,
            description,
            vat_amount: vat ? Number(vat.replace(",", ".")) : null,
            payment_method: payment,
            is_shared: shared,
            source: initial?.source || "manual",
            category_id: categoryId ? Number(categoryId) : null,
            invoice_number: invoice,
            cui,
          });
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label="Sumă (RON)">
          <input className={inputClass} inputMode="decimal" required value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
        <Field label="Data">
          <input className={inputClass} type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
      </div>
      <Field label="Comerciant">
        <input className={inputClass} value={merchant} onChange={(e) => setMerchant(e.target.value)} placeholder="ex. Mega Image" />
      </Field>
      <Field label="Categorie">
        <select className={inputClass} value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Fără categorie</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon} {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Descriere">
        <input className={inputClass} value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="TVA (opțional)">
          <input className={inputClass} inputMode="decimal" value={vat} onChange={(e) => setVat(e.target.value)} />
        </Field>
        <Field label="Plată">
          <select className={inputClass} value={payment} onChange={(e) => setPayment(e.target.value)}>
            <option value="card">Card</option>
            <option value="numerar">Numerar</option>
          </select>
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Nr. factură">
          <input className={inputClass} value={invoice} onChange={(e) => setInvoice(e.target.value)} />
        </Field>
        <Field label="CUI">
          <input className={inputClass} value={cui} onChange={(e) => setCui(e.target.value)} />
        </Field>
      </div>
      <label className="flex min-h-11 items-center gap-3 rounded-xl bg-sand px-3 py-2">
        <input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} className="size-5 accent-forest" />
        <span className="text-sm">Cheltuială comună</span>
      </label>
      {error ? <p className="text-sm text-clay">{error}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="min-h-12 w-full rounded-2xl bg-forest text-sand font-semibold disabled:opacity-60"
      >
        {busy ? "Se salvează…" : submitLabel}
      </button>
    </form>
  );
}
