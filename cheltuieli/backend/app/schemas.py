from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    is_active: bool
    ha_user_id: str | None = None
    created_at: DateTime


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=72)
    role: str = "membru"


class UserSelfUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=72)


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=72)
    role: str | None = None
    is_active: bool | None = None


class AiModelOption(BaseModel):
    id: str
    label: str


class AiProviderOption(BaseModel):
    id: str
    label: str
    models: list[AiModelOption]


class AiSettingsPublic(BaseModel):
    provider: str
    model: str
    api_key_set: bool
    api_key_hint: str = ""
    providers: list[AiProviderOption]


class AiSettingsUpdate(BaseModel):
    provider: str
    model: str = ""
    api_key: str | None = None
    clear_api_key: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthStatus(BaseModel):
    registration_open: bool
    openai_configured: bool
    ai_configured: bool = False
    ai_provider: str = ""
    ai_model: str = ""
    auth_mode: str = "local"


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str
    color: str
    sort_order: int
    is_system: bool


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    icon: str = "•"
    color: str = "#3F6F5B"


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None


class ExpenseBase(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = "RON"
    date: Date
    merchant: str = ""
    description: str = ""
    vat_amount: Decimal | None = None
    payment_method: str = "card"
    is_shared: bool = False
    source: str = "manual"
    category_id: int | None = None
    invoice_number: str = ""
    cui: str = ""


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = None
    date: Date | None = None
    merchant: str | None = None
    description: str | None = None
    vat_amount: Decimal | None = None
    payment_method: str | None = None
    is_shared: bool | None = None
    source: str | None = None
    category_id: int | None = None
    invoice_number: str | None = None
    cui: str | None = None


class ExpensePublic(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    document_id: int | None
    user_name: str = ""
    category_name: str | None = None
    category_color: str | None = None
    category_icon: str | None = None
    created_at: DateTime


class ExtractedItem(BaseModel):
    date: Date | None = None
    merchant: str = ""
    description: str = ""
    amount: Decimal | None = None
    currency: str = "RON"
    vat_amount: Decimal | None = None
    payment_method: str = "card"
    is_shared: bool = False
    source: str = "bon"
    category_id: int | None = None
    invoice_number: str = ""
    cui: str = ""
    selected: bool = True

    @field_validator("date", mode="before")
    @classmethod
    def _date(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, Date):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return Date.fromisoformat(text[:10])
        except ValueError:
            from app.services.extract import parse_date

            return parse_date(text)

    @field_validator("amount", "vat_amount", mode="before")
    @classmethod
    def _money(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float, Decimal)):
            return value
        from app.services.extract import parse_amount

        parsed = parse_amount(str(value))
        return parsed

    @field_validator("category_id", mode="before")
    @classmethod
    def _category(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return value

    @field_validator("payment_method", mode="before")
    @classmethod
    def _payment(cls, value: object) -> str:
        text = str(value or "card").strip().lower()
        if "numerar" in text or "cash" in text:
            return "numerar"
        return "card"

    @field_validator("currency", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        text = str(value or "RON").strip().upper()
        if text in {"LEI", "RON"}:
            return "RON"
        return (text or "RON")[:8]


class DocumentExtractResponse(BaseModel):
    document_id: int
    filename: str
    doc_type: str
    method: str
    warning: str = ""
    openai_configured: bool
    items: list[ExtractedItem]
    status: str = "processed"


class ConfirmImportRequest(BaseModel):
    items: list[ExtractedItem]


class BudgetItem(BaseModel):
    category_id: int
    amount: Decimal = Field(ge=0)


class BudgetSaveRequest(BaseModel):
    year: int
    month: int
    items: list[BudgetItem]


class BudgetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    year: int
    month: int
    amount: Decimal
    category_name: str = ""
    spent: Decimal = Decimal("0")
