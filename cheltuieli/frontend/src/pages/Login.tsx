import { useEffect, useState, type ReactNode } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { api, ApiError } from "../lib/api";
import type { User } from "../lib/types";
import { Field, inputClass } from "../components/Modal";

export default function Login() {
  const { user, status, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && status?.auth_mode === "homeassistant") return;
    if (!loading && status?.registration_open && !user) {
      navigate("/register", { replace: true });
    }
  }, [loading, status, user, navigate]);

  if (user) return <Navigate to="/" replace />;
  if (status?.auth_mode === "homeassistant") {
    return (
      <AuthShell title="Home Assistant" subtitle="Autentificarea se face din Home Assistant, nu cu email și parolă.">
        <p className="text-sm text-ink/70">
          Deschide Cheltuieli din bara laterală. Tunelul Cloudflare trebuie să ducă doar la Home
          Assistant (port 8123), nu separat la acest add-on.
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Intră în cont" subtitle="Cheltuielile gospodăriei, într-un singur loc.">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await api<User>("/auth/login", {
              method: "POST",
              body: JSON.stringify({ email, password }),
            });
            await refresh();
            navigate("/");
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Nu am putut intra");
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Email">
          <input className={inputClass} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Parolă">
          <input
            className={inputClass}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {error ? <p className="text-sm text-clay">{error}</p> : null}
        <button type="submit" disabled={busy} className="min-h-12 w-full rounded-2xl bg-forest font-semibold text-sand">
          {busy ? "Se conectează…" : "Intră"}
        </button>
      </form>
      {status?.registration_open ? (
        <p className="mt-4 text-center text-sm text-ink/60">
          Primul cont? <Link className="text-forest underline" to="/register">Creează-l aici</Link>
        </p>
      ) : (
        <p className="mt-4 text-center text-sm text-ink/50">Conturile noi sunt create de administrator.</p>
      )}
    </AuthShell>
  );
}

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-3xl bg-paper p-6 shadow-card md:p-8">
        <p className="font-display text-3xl text-forest">Cheltuieli</p>
        <h1 className="mt-6 font-display text-2xl">{title}</h1>
        <p className="mt-1 text-sm text-ink/60">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}
