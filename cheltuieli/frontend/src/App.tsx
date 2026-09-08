import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api, ApiError } from "./lib/api";
import type { AuthStatus, Category, User } from "./lib/types";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Expenses from "./pages/Expenses";
import ImportPage from "./pages/Import";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";

type AuthContextValue = {
  user: User | null;
  status: AuthStatus | null;
  categories: Category[];
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth trebuie folosit în App");
  return ctx;
}

function Guard({ children }: { children: ReactNode }) {
  const { user, status, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-forest">
        Se încarcă…
      </div>
    );
  }
  if (!user) {
    if (status?.auth_mode === "homeassistant") {
      return (
        <div className="flex min-h-dvh items-center justify-center px-6 text-center">
          <div className="max-w-md rounded-3xl bg-paper p-6 shadow-card">
            <p className="font-display text-2xl text-forest">Cheltuieli</p>
            <p className="mt-4 text-sm text-ink/70">
              Deschide aplicația din bara laterală Home Assistant. Accesul direct, fără Ingress, nu
              este permis — inclusiv prin domeniul Cloudflare.
            </p>
          </div>
        </div>
      );
    }
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const st = await api<AuthStatus>("/auth/status");
    setStatus(st);
    try {
      const me = await api<User>("/auth/me");
      setUser(me);
      const cats = await api<Category[]>("/categories");
      setCategories(cats);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
        setCategories([]);
      } else {
        throw err;
      }
    }
  };

  useEffect(() => {
    refresh()
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const logout = async () => {
    await api("/auth/logout", { method: "POST" });
    setUser(null);
    setCategories([]);
  };

  const value = useMemo(
    () => ({ user, status, categories, loading, refresh, logout }),
    [user, status, categories, loading],
  );

  return (
    <AuthContext.Provider value={value}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          element={
            <Guard>
              <Layout />
            </Guard>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/cheltuieli" element={<Expenses />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/rapoarte" element={<Reports />} />
          <Route path="/setari" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthContext.Provider>
  );
}
