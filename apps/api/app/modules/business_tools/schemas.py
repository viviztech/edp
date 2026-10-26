from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Currency = Literal["INR", "USD", "EUR", "GBP"]
Money = Annotated[
    Decimal, Field(ge=0, le=Decimal("999999999999.99"), max_digits=14, decimal_places=2)
]
Quantity = Annotated[Decimal, Field(gt=0, le=1000000, max_digits=12, decimal_places=3)]
HistoryKind = Literal["card", "catalogue", "catalogue_item", "quote", "contact", "task"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("*", mode="before")
    @classmethod
    def trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class Command(StrictModel):
    request_id: UUID


class VersionCommand(Command):
    expected_version: int = Field(ge=1)


class Sharing(Command):
    expected_version: int = Field(ge=0)
    published: bool


class ContactDetails(StrictModel):
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=254)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if value:
            try:
                return str(validate_email(value, check_deliverability=False).normalized)
            except EmailNotValidError as exc:
                raise ValueError("Invalid email") from exc
        return value


class CardFields(ContactDetails):
    name_en: str = Field(min_length=1, max_length=160)
    name_ta: str = Field(default="", max_length=160)
    tagline_en: str = Field(default="", max_length=240)
    tagline_ta: str = Field(default="", max_length=240)
    description_en: str = Field(default="", max_length=4000)
    description_ta: str = Field(default="", max_length=4000)
    website: str = Field(default="", max_length=500)
    address_en: str = Field(default="", max_length=500)
    address_ta: str = Field(default="", max_length=500)

    @field_validator("website")
    @classmethod
    def safe_website(cls, value: str) -> str:
        if value:
            try:
                parsed = urlsplit(value)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or any(ord(c) < 33 for c in value)
                ):
                    raise ValueError("Use an HTTPS business website")
                _ = parsed.port
            except ValueError as exc:
                raise ValueError("Use an HTTPS business website") from exc
        return value


class SaveCard(CardFields, Command):
    expected_version: int = Field(ge=0)


class CardView(CardFields):
    id: UUID
    version: int
    published: bool
    share_id: UUID
    updated_at: datetime


class PublicCard(CardFields):
    share_id: UUID


class CatalogueItemFields(StrictModel):
    kind: Literal["product", "service"]
    name_en: str = Field(min_length=1, max_length=160)
    name_ta: str = Field(default="", max_length=160)
    description_en: str = Field(default="", max_length=4000)
    description_ta: str = Field(default="", max_length=4000)
    available: bool = True
    price: Money | None = None
    currency: Currency = "INR"


class CreateCatalogueItem(CatalogueItemFields, Command):
    pass


class UpdateCatalogueItem(CatalogueItemFields, VersionCommand):
    pass


class CatalogueItemView(CatalogueItemFields):
    id: UUID
    version: int
    updated_at: datetime


class CatalogueView(StrictModel):
    version: int
    published: bool
    share_id: UUID


class CataloguePage(StrictModel):
    settings: CatalogueView | None
    items: list[CatalogueItemView]
    limit: int
    offset: int


class PublicCatalogueItem(CatalogueItemFields):
    pass


class PublicCatalogue(StrictModel):
    share_id: UUID
    items: list[PublicCatalogueItem]
    limit: int
    offset: int


class QuotationLineInput(StrictModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Quantity
    unit_price: Money
    catalogue_item_id: UUID | None = None
    catalogue_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def reference_pair(self) -> "QuotationLineInput":
        if (self.catalogue_item_id is None) != (self.catalogue_version is None):
            raise ValueError("Catalogue ID and expected version must be supplied together")
        return self


class QuotationFields(StrictModel):
    customer_name: str = Field(min_length=1, max_length=160)
    customer_address: str = Field(default="", max_length=1000)
    issued_on: date
    valid_until: date | None = None
    currency: Currency = "INR"
    notes: str = Field(default="", max_length=4000)
    discount: Money = Decimal("0.00")
    lines: list[QuotationLineInput] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def dates(self) -> "QuotationFields":
        if self.valid_until and self.valid_until < self.issued_on:
            raise ValueError("Validity must not precede issue date")
        return self


class CreateQuotation(QuotationFields, Command):
    pass


class UpdateQuotation(QuotationFields, VersionCommand):
    pass


class QuotationLineView(QuotationLineInput):
    line_total: Money


class QuotationView(StrictModel):
    id: UUID
    business_name: str
    version: int
    status: Literal["draft", "issued"]
    customer_name: str
    customer_address: str
    issued_on: date
    valid_until: date | None
    currency: Currency
    notes: str
    lines: list[QuotationLineView]
    subtotal: Money
    discount: Money
    total: Money
    issued_at: datetime | None
    updated_at: datetime


class QuotationPage(StrictModel):
    items: list[QuotationView]
    limit: int
    offset: int


class CustomerContactFields(ContactDetails):
    name: str = Field(min_length=1, max_length=160)
    notes: str = Field(default="", max_length=4000)
    status: Literal["lead", "customer", "archived"] = "lead"


class CreateContact(CustomerContactFields, Command):
    pass


class UpdateContact(CustomerContactFields, VersionCommand):
    pass


class CustomerContactView(CustomerContactFields):
    id: UUID
    version: int
    updated_at: datetime


class CustomerContactPage(StrictModel):
    items: list[CustomerContactView]
    limit: int
    offset: int


class TaskFields(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    notes: str = Field(default="", max_length=4000)
    due_at: datetime

    @field_validator("due_at")
    @classmethod
    def aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("An explicit UTC offset is required")
        value = value.astimezone(UTC)
        if not 2000 <= value.year <= 2100:
            raise ValueError("Due time is out of range")
        return value


class CreateTask(TaskFields, Command):
    contact_id: UUID


class UpdateTask(TaskFields, VersionCommand):
    status: Literal["pending", "completed", "cancelled"]


class CustomerTaskView(TaskFields):
    id: UUID
    contact_id: UUID
    version: int
    status: Literal["pending", "completed", "cancelled"]
    completed_at: datetime | None
    updated_at: datetime


class CustomerTaskPage(StrictModel):
    items: list[CustomerTaskView]
    limit: int
    offset: int


class ToolHistoryView(StrictModel):
    id: UUID
    kind: HistoryKind
    resource_id: UUID
    version: int
    action: str
    created_at: datetime
    changed_fields: list[str]


class ToolHistoryPage(StrictModel):
    items: list[ToolHistoryView]
    limit: int
    offset: int
