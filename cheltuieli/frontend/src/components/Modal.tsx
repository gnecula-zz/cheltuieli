import { useEffect, type ReactNode } from "react";

export default function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/40 p-0 md:items-center md:p-6">
      <button type="button" className="absolute inset-0" aria-label="Închide" onClick={onClose} />
      <div className="relative z-10 max-h-[92dvh] w-full overflow-y-auto rounded-t-3xl bg-paper p-5 shadow-card md:max-w-lg md:rounded-3xl">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-display text-xl">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-full px-3 py-1 text-sm text-ink/60 hover:bg-sand">
            Închide
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-ink/70">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-black/10 bg-white px-3 py-3 text-base outline-none ring-forest/30 focus:ring-2";
