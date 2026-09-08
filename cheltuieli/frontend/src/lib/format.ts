export function money(value: number | string | null | undefined, currency = "RON"): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("ro-RO", { style: "currency", currency }).format(n);
}

export function monthLabel(year: number, month: intLike): string {
  const date = new Date(year, month - 1, 1);
  return new Intl.DateTimeFormat("ro-RO", { month: "long", year: "numeric" }).format(date);
}

type intLike = number;

export function todayIso(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function sourceLabel(source: string): string {
  switch (source) {
    case "bon":
      return "Bon";
    case "extras":
      return "Extras";
    case "factura":
      return "Factură";
    default:
      return "Manual";
  }
}

export function monthStart(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}-01`;
}

export function monthEnd(year: number, month: number): string {
  const end = new Date(year, month, 0);
  return `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
}
