import { useEffect, useRef, useState } from "react";
import { Camera, FileUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { api, ApiError } from "../lib/api";
import { compressImage } from "../lib/image";
import { money, todayIso } from "../lib/format";
import type { ExtractedItem, ExtractResponse } from "../lib/types";
import { inputClass } from "../components/Modal";

function hydrateItems(data: ExtractResponse): ExtractedItem[] {
  return (data.items || []).map((item) => ({
    ...item,
    date: item.date || todayIso(),
    selected: item.selected !== false,
  }));
}

export default function ImportPage() {
  const { categories, status } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [items, setItems] = useState<ExtractedItem[]>([]);
  const [drafts, setDrafts] = useState<ExtractResponse[]>([]);
  const [drag, setDrag] = useState(false);
  const uploadGen = useRef(0);

  const loadDrafts = () => {
    api<ExtractResponse[]>("/documents")
      .then(setDrafts)
      .catch(() => setDrafts([]));
  };

  useEffect(() => {
    loadDrafts();
  }, []);

  const showExtract = (data: ExtractResponse) => {
    setResult(data);
    setItems(hydrateItems(data));
  };

  const upload = async (file: File) => {
    const gen = ++uploadGen.current;
    setBusy(true);
    setError("");
    setResult(null);
    setItems([]);
    try {
      const ready = file.type.startsWith("image/") ? await compressImage(file) : file;
      if (gen !== uploadGen.current) return;
      const body = new FormData();
      body.append("file", ready);
      let data = await api<ExtractResponse>("/documents/upload", { method: "POST", body });
      const started = Date.now();
      while (data.status === "processing") {
        if (gen !== uploadGen.current) return;
        if (Date.now() - started > 180_000) {
          throw new ApiError(504, "Extragerea durează prea mult. Reîncearcă.");
        }
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        data = await api<ExtractResponse>(`/documents/${data.document_id}`);
      }
      if (gen !== uploadGen.current) return;
      if (data.status === "error") {
        throw new ApiError(502, data.warning || "Extragerea a eșuat");
      }
      showExtract(data);
      loadDrafts();
    } catch (err) {
      if (gen !== uploadGen.current) return;
      setError(err instanceof ApiError ? err.message : "Încărcarea a eșuat");
    } finally {
      if (gen === uploadGen.current) setBusy(false);
    }
  };

  const discardDraft = async (documentId: number) => {
    setError("");
    try {
      await api(`/documents/${documentId}`, { method: "DELETE" });
      if (result?.document_id === documentId) {
        setResult(null);
        setItems([]);
      }
      loadDrafts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nu am șters extrasul");
    }
  };

  const confirm = async () => {
    if (!result) return;
    const documentId = result.document_id;
    const payloadItems = items;
    setBusy(true);
    setError("");
    try {
      const payload = {
        items: payloadItems.map((item) => ({
          ...item,
          amount: item.amount == null || item.amount === "" ? null : Number(String(item.amount).replace(",", ".")),
          vat_amount:
            item.vat_amount == null || item.vat_amount === ""
              ? null
              : Number(String(item.vat_amount).replace(",", ".")),
        })),
      };
      const saved = await api<unknown[]>(`/documents/${documentId}/confirm`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!Array.isArray(saved) || saved.length === 0) {
        throw new ApiError(400, "Nu s-a salvat nicio cheltuială. Verifică suma de pe bon.");
      }
      navigate("/cheltuieli");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Confirmarea a eșuat");
    } finally {
      setBusy(false);
    }
  };

  const update = (index: number, patch: Partial<ExtractedItem>) => {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  };

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-ink/55">Import</p>
        <h1 className="font-display text-3xl">Bonuri și PDF-uri</h1>
        <p className="mt-1 text-sm text-ink/60">
          PDF-urile cu text se citesc local. Pozele de bonuri și scanurile folosesc agentul AI din Setări, dacă e cheia configurată.
        </p>
      </div>

      {!(status?.ai_configured ?? status?.openai_configured) ? (
        <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Nu e configurat un agent AI. Pozele și PDF-urile scanate trebuie completate manual — poți adăuga cheia din Setări.
        </p>
      ) : null}

      <div
        className={`rounded-3xl border-2 border-dashed p-6 text-center ${drag ? "border-forest bg-forest/5" : "border-black/15 bg-paper"}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          if (busy) return;
          const file = e.dataTransfer.files[0];
          if (file) void upload(file);
        }}
      >
        <FileUp className="mx-auto text-forest" />
        <p className="mt-2 font-medium">Trage un fișier aici</p>
        <p className="text-sm text-ink/50">PDF, JPG, PNG — max. 20 MB</p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <label className={`min-h-12 cursor-pointer rounded-2xl bg-forest px-5 py-3 font-semibold text-sand ${busy ? "pointer-events-none opacity-60" : ""}`}>
            Alege fișier
            <input
              type="file"
              accept="application/pdf,image/*"
              className="hidden"
              disabled={busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void upload(file);
                e.target.value = "";
              }}
            />
          </label>
          <label className={`flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl bg-white px-5 py-3 font-semibold text-forest shadow-card ${busy ? "pointer-events-none opacity-60" : ""}`}>
            <Camera size={18} /> Fă o poză
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              disabled={busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void upload(file);
                e.target.value = "";
              }}
            />
          </label>
        </div>
        {busy ? <p className="mt-3 text-sm text-forest">Se extrage…</p> : null}
      </div>

      {error ? <p className="text-sm text-clay">{error}</p> : null}

      {drafts.length > 0 && !result ? (
        <section className="rounded-3xl bg-paper p-5 shadow-card">
          <h2 className="font-display text-xl">Extrase nesalvate</h2>
          <p className="mt-1 text-sm text-ink/60">Bonuri citite pe care nu le-ai salvat încă. Poți relua adăugarea sau le poți șterge.</p>
          <ul className="mt-3 space-y-2">
            {drafts.map((doc) => {
              const hint = doc.items.find((item) => item.merchant)?.merchant || doc.filename;
              const amount = doc.items.find((item) => item.amount != null && item.amount !== "")?.amount;
              return (
                <li key={doc.document_id} className="flex items-stretch gap-2">
                  <button
                    type="button"
                    className="flex min-h-11 min-w-0 flex-1 items-center justify-between gap-3 rounded-2xl bg-sand px-4 py-3 text-left"
                    onClick={() => {
                      setError("");
                      showExtract(doc);
                    }}
                  >
                    <span className="truncate font-medium">{hint}</span>
                    <span className="shrink-0 text-sm text-ink/55">{amount ? money(amount) : `${doc.items.length} rânduri`}</span>
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded-2xl px-3 font-medium text-clay"
                    onClick={() => void discardDraft(doc.document_id)}
                  >
                    Șterge
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {result ? (
        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="font-display text-xl">Verifică extrasul</h2>
              <p className="text-xs text-ink/50">
                {result.filename} · {result.doc_type} · {result.method === "local_text" ? "parsare locală" : result.method === "ai_vision" || result.method === "openai_vision" ? "extragere AI" : "completare manuală"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="min-h-11 rounded-2xl bg-white px-4 font-semibold text-forest shadow-card"
                onClick={() => {
                  setResult(null);
                  setItems([]);
                  loadDrafts();
                }}
              >
                Înapoi
              </button>
              <button
                type="button"
                className="min-h-11 rounded-2xl px-4 font-semibold text-clay"
                onClick={() => void discardDraft(result.document_id)}
              >
                Șterge extrasul
              </button>
              <button type="button" disabled={busy} onClick={confirm} className="min-h-11 rounded-2xl bg-forest px-4 font-semibold text-sand">
                Salvează selectate
              </button>
            </div>
          </div>
          {result.warning ? <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">{result.warning}</p> : null}

          <div className="hidden overflow-x-auto rounded-2xl bg-paper shadow-card md:block">
            <table className="min-w-full text-left text-sm">
              <thead className="text-ink/50">
                <tr>
                  <th className="p-3"> </th>
                  <th className="p-3">Dată</th>
                  <th className="p-3">Comerciant</th>
                  <th className="p-3">Sumă</th>
                  <th className="p-3">Categorie</th>
                  <th className="p-3">Comună</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={index} className="border-t border-black/5">
                    <td className="p-3">
                      <input type="checkbox" className="size-5 accent-forest" checked={item.selected} onChange={(e) => update(index, { selected: e.target.checked })} />
                    </td>
                    <td className="p-2">
                      <input type="date" className={inputClass} value={item.date || ""} onChange={(e) => update(index, { date: e.target.value })} />
                    </td>
                    <td className="p-2">
                      <input className={inputClass} value={item.merchant} onChange={(e) => update(index, { merchant: e.target.value })} />
                    </td>
                    <td className="p-2">
                      <input className={inputClass} inputMode="decimal" value={item.amount ?? ""} onChange={(e) => update(index, { amount: e.target.value })} />
                    </td>
                    <td className="p-2">
                      <select className={inputClass} value={item.category_id ?? ""} onChange={(e) => update(index, { category_id: e.target.value ? Number(e.target.value) : null })}>
                        <option value="">—</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-3">
                      <input type="checkbox" className="size-5 accent-forest" checked={item.is_shared} onChange={(e) => update(index, { is_shared: e.target.checked })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="space-y-3 md:hidden">
            {items.map((item, index) => (
              <li key={index} className="rounded-2xl bg-paper p-4 shadow-card">
                <label className="flex items-center gap-2 text-sm font-medium">
                  <input type="checkbox" className="size-5 accent-forest" checked={item.selected} onChange={(e) => update(index, { selected: e.target.checked })} />
                  Include
                </label>
                <div className="mt-3 space-y-2">
                  <input type="date" className={inputClass} value={item.date || ""} onChange={(e) => update(index, { date: e.target.value })} />
                  <input className={inputClass} placeholder="Comerciant" value={item.merchant} onChange={(e) => update(index, { merchant: e.target.value })} />
                  <input className={inputClass} inputMode="decimal" placeholder="Sumă" value={item.amount ?? ""} onChange={(e) => update(index, { amount: e.target.value })} />
                  <select className={inputClass} value={item.category_id ?? ""} onChange={(e) => update(index, { category_id: e.target.value ? Number(e.target.value) : null })}>
                    <option value="">Categorie</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" className="size-5 accent-forest" checked={item.is_shared} onChange={(e) => update(index, { is_shared: e.target.checked })} />
                    Comună
                  </label>
                  {item.amount ? <p className="text-xs text-ink/45">{money(item.amount, item.currency)}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
