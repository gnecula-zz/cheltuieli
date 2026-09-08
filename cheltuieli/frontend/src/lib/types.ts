export type Role = "admin" | "membru";

export type User = {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  ha_user_id?: string | null;
};

export type Category = {
  id: number;
  name: string;
  icon: string;
  color: string;
  sort_order: number;
  is_system: boolean;
};

export type Expense = {
  id: number;
  user_id: number;
  category_id: number | null;
  document_id: number | null;
  amount: number | string;
  currency: string;
  date: string;
  merchant: string;
  description: string;
  vat_amount: number | string | null;
  payment_method: "card" | "numerar" | string;
  is_shared: boolean;
  source: "manual" | "bon" | "extras" | "factura" | string;
  invoice_number: string;
  cui: string;
  user_name: string;
  category_name: string | null;
  category_color: string | null;
  category_icon: string | null;
};

export type ExtractedItem = {
  date: string | null;
  merchant: string;
  description: string;
  amount: number | string | null;
  currency: string;
  vat_amount: number | string | null;
  payment_method: string;
  is_shared: boolean;
  source: string;
  category_id: number | null;
  invoice_number: string;
  cui: string;
  selected: boolean;
};

export type ExtractResponse = {
  document_id: number;
  filename: string;
  doc_type: string;
  method: string;
  warning: string;
  openai_configured: boolean;
  items: ExtractedItem[];
};

export type ReportSummary = {
  year: number;
  month: number | null;
  count: number;
  total: number;
  shared: number;
  personal: number;
  by_category: { name: string; color: string; icon: string; total: number }[];
  by_person: { name: string; total: number }[];
  by_merchant: { name: string; total: number }[];
  budgets: { category_id: number; category_name: string; amount: number; spent: number }[];
};

export type Budget = {
  id: number;
  category_id: number;
  year: number;
  month: number;
  amount: number | string;
  category_name: string;
  spent: number | string;
};

export type AuthStatus = {
  registration_open: boolean;
  openai_configured: boolean;
  ai_configured?: boolean;
  ai_provider?: string;
  ai_model?: string;
  auth_mode?: "local" | "homeassistant" | string;
};

export type AiProvider = {
  id: string;
  label: string;
  models: { id: string; label: string }[];
};

export type AiSettings = {
  provider: string;
  model: string;
  api_key_set: boolean;
  api_key_hint: string;
  providers: AiProvider[];
};
