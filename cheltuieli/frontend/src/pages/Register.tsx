import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { api, ApiError } from "../lib/api";
import type { User } from "../lib/types";
import { Field, inputClass } from "../components/Modal";
import { AuthShell } from "./Login";

export default function Register() {
  const { user, status, refresh } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;
  if (status?.auth_mode === "homeassistant") return <Navigate to="/" replace />;
  if (status && !status.registration_open) return <Navigate to="/login" replace />;

  return (
    <AuthShell title="Creează primul cont" subtitle="Devii administratorul gospodăriei. Apoi poți adăuga membri din Setări.">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await api<User>("/auth/register", {
              method: "POST",
              body: JSON.stringify({ name, email, password }),
            });
            await refresh();
            navigate("/");
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Nu am putut crea contul");
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Nume">
          <input className={inputClass} required value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Email">
          <input className={inputClass} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Parolă (minim 6 caractere)">
          <input className={inputClass} type="password" minLength={6} required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error ? <p className="text-sm text-clay">{error}</p> : null}
        <button type="submit" disabled={busy} className="min-h-12 w-full rounded-2xl bg-forest font-semibold text-sand">
          {busy ? "Se creează…" : "Creează contul"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-ink/60">
        Ai deja cont? <Link className="text-forest underline" to="/login">Intră</Link>
      </p>
    </AuthShell>
  );
}
