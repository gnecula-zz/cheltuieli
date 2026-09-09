import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../App";
import { api, ApiError } from "../lib/api";
import Modal, { Field, inputClass } from "../components/Modal";
import type { AiSettings, Budget, Category, User } from "../lib/types";

const CATEGORY_EMOJIS = [
  "🛒",
  "🚌",
  "💡",
  "🏠",
  "💊",
  "🍽️",
  "🎬",
  "📚",
  "👕",
  "📱",
  "🏛️",
  "📦",
  "⛽",
  "🐶",
  "👶",
  "🎁",
  "✈️",
  "🏦",
  "🧹",
  "🔧",
];

function EmojiField({
  value,
  onChange,
}: {
  value: string;
  onChange: (icon: string) => void;
}) {
  return (
    <div className="space-y-2">
      <input
        className={inputClass}
        value={value}
        maxLength={8}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Iconiță"
      />
      <div className="flex flex-wrap gap-1.5">
        {CATEGORY_EMOJIS.map((icon) => (
          <button
            key={icon}
            type="button"
            className={`size-10 rounded-xl text-lg ${value === icon ? "bg-forest/15 ring-2 ring-forest" : "bg-sand"}`}
            onClick={() => onChange(icon)}
          >
            {icon}
          </button>
        ))}
      </div>
      <p className="text-xs text-ink/50">
        Copiază și alte emoji de pe{" "}
        <a className="text-forest underline" href="https://getemoji.com/" target="_blank" rel="noreferrer">
          getemoji.com
        </a>{" "}
        sau caută pe{" "}
        <a className="text-forest underline" href="https://emojipedia.org/" target="_blank" rel="noreferrer">
          Emojipedia
        </a>
        .
      </p>
    </div>
  );
}

export default function Settings() {
  const { user, categories, status, refresh } = useAuth();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [budgets, setBudgets] = useState<Record<number, string>>({});
  const [members, setMembers] = useState<User[]>([]);
  const [newCat, setNewCat] = useState("");
  const [newCatIcon, setNewCatIcon] = useState("📦");
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [catForm, setCatForm] = useState({ name: "", icon: "📦", color: "#3F6F5B" });
  const [memberForm, setMemberForm] = useState({ name: "", email: "", password: "", role: "membru" });
  const [editing, setEditing] = useState<User | null>(null);
  const [editForm, setEditForm] = useState({ name: "", email: "", password: "", role: "membru", is_active: true });
  const [profile, setProfile] = useState({ name: "", email: "", password: "" });
  const [ai, setAi] = useState<AiSettings | null>(null);
  const [aiProvider, setAiProvider] = useState("openai");
  const [aiModel, setAiModel] = useState("");
  const [aiKey, setAiKey] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) setProfile({ name: user.name, email: user.email, password: "" });
  }, [user]);

  useEffect(() => {
    api<Budget[]>(`/budgets?year=${year}&month=${month}`).then((rows) => {
      const map: Record<number, string> = {};
      for (const row of rows) map[row.category_id] = String(row.amount);
      setBudgets(map);
    });
  }, [year, month]);

  const loadMembers = () => {
    if (user?.role === "admin") {
      api<User[]>("/users").then(setMembers).catch(() => setMembers([]));
    }
  };

  useEffect(() => {
    loadMembers();
    if (user?.role === "admin") {
      api<AiSettings>("/settings/ai")
        .then((data) => {
          setAi(data);
          setAiProvider(data.provider);
          setAiModel(data.model);
        })
        .catch(() => setAi(null));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const flash = (text: string) => {
    setMessage(text);
    setError("");
    window.setTimeout(() => setMessage(""), 2500);
  };

  const providerModels = useMemo(() => {
    return ai?.providers.find((p) => p.id === aiProvider)?.models || [];
  }, [ai, aiProvider]);

  const adminCount = members.filter((m) => m.role === "admin" && m.is_active).length;
  const haMode = status?.auth_mode === "homeassistant";

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-ink/55">Setări</p>
        <h1 className="font-display text-3xl">Gospodăria</h1>
      </div>
      {message ? <p className="rounded-2xl bg-forest-mist px-4 py-3 text-sm text-forest">{message}</p> : null}
      {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-clay">{error}</p> : null}

      <section className="rounded-3xl bg-paper p-5 shadow-card">
        <h2 className="font-display text-xl">Profilul meu</h2>
        <p className="mt-1 text-sm text-ink/55">{user?.role === "admin" ? "Administrator" : "Membru"}</p>
        {haMode ? (
          <p className="mt-3 text-sm text-ink/65">
            Numele și accesul vin din Home Assistant. Rolul de administrator se setează din opțiunea
            add-on-ului <span className="font-medium">admin_users</span> (username-uri HA) sau, dacă
            e goală, primul utilizator care deschide aplicația.
          </p>
        ) : (
        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const body: Record<string, string> = { name: profile.name, email: profile.email };
              if (profile.password) body.password = profile.password;
              await api("/users/me", { method: "PATCH", body: JSON.stringify(body) });
              setProfile((p) => ({ ...p, password: "" }));
              await refresh();
              loadMembers();
              flash("Profilul a fost salvat");
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Nu am salvat profilul");
            }
          }}
        >
          <Field label="Nume">
            <input className={inputClass} required value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
          </Field>
          <Field label="Email">
            <input className={inputClass} type="email" required value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} />
          </Field>
          <Field label="Parolă nouă (opțional)">
            <input className={inputClass} type="password" minLength={6} value={profile.password} onChange={(e) => setProfile({ ...profile, password: e.target.value })} />
          </Field>
          <div className="flex items-end">
            <button type="submit" className="min-h-12 w-full rounded-2xl bg-forest font-semibold text-sand">
              Salvează profilul
            </button>
          </div>
        </form>
        )}
      </section>

      {user?.role === "admin" ? (
        <section className="rounded-3xl bg-paper p-5 shadow-card">
          <h2 className="font-display text-xl">Agent AI</h2>
          <p className="mt-2 text-sm text-ink/65">
            Folosit la extragerea din poze de bonuri și PDF-uri scanate. Cheia nu se afișează integral.
            Furnizorul și modelul se salvează aici și rămân după update-ul add-on-ului.
          </p>
          <p className="mt-1 text-sm text-ink/55">
            {ai?.api_key_set ? `Cheie setată (${ai.api_key_hint})` : "Nicio cheie — doar PDF-uri cu text"}
            {status?.ai_provider ? ` · ${status.ai_provider}` : ""}
          </p>
          <form
            className="mt-4 space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const saved = await api<AiSettings>("/settings/ai", {
                  method: "PUT",
                  body: JSON.stringify({
                    provider: aiProvider,
                    model: aiModel,
                    api_key: aiKey.trim() || null,
                    clear_api_key: false,
                  }),
                });
                setAi(saved);
                setAiProvider(saved.provider);
                setAiModel(saved.model);
                setAiKey("");
                await refresh();
                flash("Setările AI au fost salvate");
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Nu am salvat agentul AI");
              }
            }}
          >
            <Field label="Furnizor">
              <select
                className={inputClass}
                value={aiProvider}
                onChange={(e) => {
                  const next = e.target.value;
                  setAiProvider(next);
                  const first = ai?.providers.find((p) => p.id === next)?.models[0]?.id || "";
                  setAiModel(first);
                }}
              >
                {(ai?.providers || [{ id: "openai", label: "OpenAI", models: [] }]).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Model">
              <select className={inputClass} value={aiModel} onChange={(e) => setAiModel(e.target.value)}>
                {providerModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Cheie API">
              <input
                className={inputClass}
                type="password"
                autoComplete="off"
                placeholder={ai?.api_key_set ? "Lasă gol ca să păstrezi cheia actuală" : "lipește cheia API"}
                value={aiKey}
                onChange={(e) => setAiKey(e.target.value)}
              />
            </Field>
            <div className="flex flex-col gap-2 sm:flex-row">
              <button type="submit" className="min-h-12 flex-1 rounded-2xl bg-forest font-semibold text-sand">
                Salvează agentul
              </button>
              {ai?.api_key_set ? (
                <button
                  type="button"
                  className="min-h-12 rounded-2xl bg-sand px-4 font-semibold text-clay"
                  onClick={async () => {
                    try {
                      const saved = await api<AiSettings>("/settings/ai", {
                        method: "PUT",
                        body: JSON.stringify({ provider: aiProvider, model: aiModel, clear_api_key: true }),
                      });
                      setAi(saved);
                      setAiKey("");
                      await refresh();
                      flash("Cheia API a fost ștearsă");
                    } catch (err) {
                      setError(err instanceof ApiError ? err.message : "Nu am șters cheia");
                    }
                  }}
                >
                  Șterge cheia
                </button>
              ) : null}
            </div>
          </form>
        </section>
      ) : null}

      <section className="rounded-3xl bg-paper p-5 shadow-card">
        <h2 className="font-display text-xl">Bugete lunare</h2>
        <div className="mt-3 flex gap-2">
          <select className={inputClass} value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>
                {new Intl.DateTimeFormat("ro-RO", { month: "long" }).format(new Date(2000, m - 1, 1))}
              </option>
            ))}
          </select>
          <select className={inputClass} value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {[year, year - 1, year + 1].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
        <ul className="mt-3 space-y-2">
          {categories.map((c) => (
            <li key={c.id} className="flex items-center gap-3">
              <span className="w-36 shrink-0 text-sm">
                {c.icon} {c.name}
              </span>
              <input
                className={inputClass}
                inputMode="decimal"
                placeholder="0"
                value={budgets[c.id] || ""}
                onChange={(e) => setBudgets((prev) => ({ ...prev, [c.id]: e.target.value }))}
              />
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="mt-4 min-h-11 rounded-2xl bg-forest px-4 font-semibold text-sand"
          onClick={async () => {
            try {
              const items = Object.entries(budgets)
                .filter(([, v]) => v && Number(v.replace(",", ".")) > 0)
                .map(([id, v]) => ({ category_id: Number(id), amount: Number(v.replace(",", ".")) }));
              await api("/budgets", { method: "PUT", body: JSON.stringify({ year, month, items }) });
              flash("Bugetele au fost salvate");
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Nu am salvat bugetele");
            }
          }}
        >
          Salvează bugetele
        </button>
      </section>

      <section className="rounded-3xl bg-paper p-5 shadow-card">
        <h2 className="font-display text-xl">Categorii</h2>
        <p className="mt-1 text-sm text-ink/55">Poți redenumi și schimba iconița la toate, inclusiv la cele implicite.</p>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {categories.map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-2 rounded-xl bg-sand px-3 py-2 text-sm">
              <span className="min-w-0 truncate">
                {c.icon} {c.name}
              </span>
              {user?.role === "admin" ? (
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    className="rounded-lg bg-white px-3 py-2 font-medium text-forest"
                    onClick={() => {
                      setEditingCategory(c);
                      setCatForm({ name: c.name, icon: c.icon, color: c.color });
                    }}
                  >
                    Editează
                  </button>
                  {!c.is_system ? (
                    <button
                      type="button"
                      className="text-clay"
                      onClick={async () => {
                        try {
                          await api(`/categories/${c.id}`, { method: "DELETE" });
                          await refresh();
                        } catch (err) {
                          setError(err instanceof ApiError ? err.message : "Nu am șters categoria");
                        }
                      }}
                    >
                      Șterge
                    </button>
                  ) : null}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
        {user?.role === "admin" ? (
          <form
            className="mt-3 grid gap-2 sm:grid-cols-[auto_1fr_auto]"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api<Category>("/categories", {
                  method: "POST",
                  body: JSON.stringify({ name: newCat, icon: newCatIcon || "📦" }),
                });
                setNewCat("");
                setNewCatIcon("📦");
                await refresh();
                flash("Categorie adăugată");
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Nu am adăugat categoria");
              }
            }}
          >
            <input
              className={`${inputClass} w-16 text-center text-lg`}
              value={newCatIcon}
              maxLength={8}
              onChange={(e) => setNewCatIcon(e.target.value)}
              aria-label="Iconiță categorie nouă"
            />
            <input className={inputClass} placeholder="Categorie nouă" value={newCat} onChange={(e) => setNewCat(e.target.value)} required />
            <button type="submit" className="rounded-xl bg-forest px-4 font-semibold text-sand">
              Adaugă
            </button>
          </form>
        ) : null}
      </section>

      {user?.role === "admin" ? (
        <section className="rounded-3xl bg-paper p-5 shadow-card">
          <h2 className="font-display text-xl">Utilizatori</h2>
          {haMode ? (
            <p className="mt-2 text-sm text-ink/65">
              Conturile apar automat la prima deschidere a aplicației din Home Assistant. Nu se
              creează manual și nu au parolă locală.
            </p>
          ) : null}
          <ul className="mt-3 space-y-2">
            {members.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-sand px-3 py-3 text-sm">
                <span>
                  {m.name} · {m.email}
                  <span className="ml-2 text-ink/50">
                    {m.role === "admin" ? "admin" : "membru"}
                    {m.is_active ? "" : " · inactiv"}
                    {m.id === user.id ? " · tu" : ""}
                  </span>
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded-lg bg-white px-3 py-2 font-medium text-forest"
                    onClick={() => {
                      setEditing(m);
                      setEditForm({
                        name: m.name,
                        email: m.email,
                        password: "",
                        role: m.role,
                        is_active: m.is_active,
                      });
                    }}
                  >
                    Editează
                  </button>
                  {m.id !== user.id && !haMode ? (
                    <button
                      type="button"
                      className="rounded-lg px-3 py-2 text-clay"
                      onClick={async () => {
                        if (!confirm(`Ștergi utilizatorul ${m.name}? Cheltuielile rămân la tine.`)) return;
                        try {
                          await api(`/users/${m.id}`, { method: "DELETE" });
                          loadMembers();
                          flash("Utilizator șters");
                        } catch (err) {
                          setError(err instanceof ApiError ? err.message : "Nu am șters utilizatorul");
                        }
                      }}
                    >
                      Șterge
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
          {haMode ? null : (
          <form
            className="mt-4 grid gap-2 sm:grid-cols-2"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api("/users", { method: "POST", body: JSON.stringify(memberForm) });
                setMemberForm({ name: "", email: "", password: "", role: "membru" });
                loadMembers();
                flash("Membru adăugat");
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Nu am creat membrul");
              }
            }}
          >
            <Field label="Nume">
              <input className={inputClass} required value={memberForm.name} onChange={(e) => setMemberForm({ ...memberForm, name: e.target.value })} />
            </Field>
            <Field label="Email">
              <input className={inputClass} type="email" required value={memberForm.email} onChange={(e) => setMemberForm({ ...memberForm, email: e.target.value })} />
            </Field>
            <Field label="Parolă">
              <input className={inputClass} type="password" minLength={6} required value={memberForm.password} onChange={(e) => setMemberForm({ ...memberForm, password: e.target.value })} />
            </Field>
            <Field label="Rol">
              <select className={inputClass} value={memberForm.role} onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}>
                <option value="membru">Membru</option>
                <option value="admin">Administrator</option>
              </select>
            </Field>
            <button type="submit" className="min-h-12 rounded-2xl bg-forest font-semibold text-sand sm:col-span-2">
              Adaugă utilizator
            </button>
          </form>
          )}
        </section>
      ) : null}

      {editingCategory ? (
        <Modal title={`Editează ${editingCategory.name}`} onClose={() => setEditingCategory(null)}>
          <form
            className="space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api(`/categories/${editingCategory.id}`, {
                  method: "PATCH",
                  body: JSON.stringify({
                    name: catForm.name.trim(),
                    icon: catForm.icon.trim() || "•",
                    color: catForm.color,
                  }),
                });
                setEditingCategory(null);
                await refresh();
                flash("Categoria a fost salvată");
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Nu am salvat categoria");
              }
            }}
          >
            <Field label="Nume">
              <input className={inputClass} required minLength={2} value={catForm.name} onChange={(e) => setCatForm({ ...catForm, name: e.target.value })} />
            </Field>
            <Field label="Iconiță">
              <EmojiField value={catForm.icon} onChange={(icon) => setCatForm({ ...catForm, icon })} />
            </Field>
            <Field label="Culoare">
              <input
                className="h-12 w-full cursor-pointer rounded-xl border border-black/10 bg-white p-1"
                type="color"
                value={catForm.color}
                onChange={(e) => setCatForm({ ...catForm, color: e.target.value })}
              />
            </Field>
            <button type="submit" className="min-h-12 w-full rounded-2xl bg-forest font-semibold text-sand">
              Salvează categoria
            </button>
          </form>
        </Modal>
      ) : null}

      {editing ? (
        <Modal title={editing.id === user?.id ? "Editează profilul de administrator" : `Editează pe ${editing.name}`} onClose={() => setEditing(null)}>
          <form
            className="space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const body: Record<string, string | boolean> = {
                  name: editForm.name,
                  email: editForm.email,
                  role: editForm.role,
                  is_active: editForm.is_active,
                };
                if (editForm.password) body.password = editForm.password;
                await api(`/users/${editing.id}`, { method: "PATCH", body: JSON.stringify(body) });
                setEditing(null);
                await refresh();
                loadMembers();
                flash("Utilizatorul a fost actualizat");
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Nu am salvat utilizatorul");
              }
            }}
          >
            {haMode ? null : (
              <>
            <Field label="Nume">
              <input className={inputClass} required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </Field>
            <Field label="Email">
              <input className={inputClass} type="email" required value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
            </Field>
            <Field label="Parolă nouă (opțional)">
              <input className={inputClass} type="password" minLength={6} value={editForm.password} onChange={(e) => setEditForm({ ...editForm, password: e.target.value })} />
            </Field>
              </>
            )}
            <Field label="Rol">
              <select
                className={inputClass}
                value={editForm.role}
                disabled={editing.role === "admin" && adminCount <= 1}
                onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
              >
                <option value="membru">Membru</option>
                <option value="admin">Administrator</option>
              </select>
            </Field>
            <label className="flex min-h-11 items-center gap-3 rounded-xl bg-sand px-3 py-2">
              <input
                type="checkbox"
                className="size-5 accent-forest"
                checked={editForm.is_active}
                disabled={editing.id === user?.id}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
              />
              <span className="text-sm">Cont activ</span>
            </label>
            <button type="submit" className="min-h-12 w-full rounded-2xl bg-forest font-semibold text-sand">
              Salvează
            </button>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}
