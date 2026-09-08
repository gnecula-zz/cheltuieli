import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { FileUp, LayoutDashboard, LogOut, PieChart, Settings, Wallet } from "lucide-react";
import { useAuth } from "../App";

const links = [
  { to: "/", label: "Panou", icon: LayoutDashboard, end: true },
  { to: "/cheltuieli", label: "Cheltuieli", icon: Wallet },
  { to: "/import", label: "Import", icon: FileUp },
  { to: "/rapoarte", label: "Rapoarte", icon: PieChart },
  { to: "/setari", label: "Setări", icon: Settings },
];

export default function Layout() {
  const { user, status, logout } = useAuth();
  const navigate = useNavigate();
  const haMode = status?.auth_mode === "homeassistant";

  return (
    <div className="min-h-dvh bg-sand text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-black/5 bg-forest text-sand md:flex">
        <div className="px-6 pb-4 pt-8">
          <p className="font-display text-2xl tracking-tight">Cheltuieli</p>
          <p className="mt-1 text-sm text-sand/70">Gospodăria, lună de lună</p>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? "bg-white/15 text-white" : "text-sand/80 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <link.icon size={18} />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 p-4">
          <p className="truncate text-sm font-medium">{user?.name}</p>
          <p className="truncate text-xs text-sand/60">{user?.role === "admin" ? "Administrator" : "Membru"}</p>
          {haMode ? (
            <p className="mt-3 text-xs text-sand/55">Autentificat prin Home Assistant</p>
          ) : (
            <button
              type="button"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              className="mt-3 flex items-center gap-2 text-sm text-sand/80 hover:text-white"
            >
              <LogOut size={16} /> Ieșire
            </button>
          )}
        </div>
      </aside>

      <div className="md:pl-60">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-black/5 bg-sand/90 px-4 py-3 backdrop-blur md:hidden">
          <p className="font-display text-lg">Cheltuieli</p>
          {haMode ? (
            <span className="text-xs text-ink/50">HA</span>
          ) : (
            <button
              type="button"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              className="rounded-full p-2 text-forest"
              aria-label="Ieșire"
            >
              <LogOut size={18} />
            </button>
          )}
        </header>
        <main className="mx-auto max-w-5xl px-4 pb-28 pt-4 md:px-8 md:pb-10 md:pt-8">
          <Outlet />
        </main>
      </div>

      <nav className="safe-bottom fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-black/10 bg-paper/95 px-1 pt-1 backdrop-blur md:hidden">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-xl text-[11px] ${
                isActive ? "text-forest font-semibold" : "text-ink/55"
              }`
            }
          >
            <link.icon size={20} />
            {link.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
