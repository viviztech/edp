from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Locale = Literal["en", "ta"]


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=50000)
    seo_title: str = Field(default="", max_length=70)
    seo_description: str = Field(default="", max_length=200)


class NewTranslation(Draft):
    locale: Locale


class CreatePage(NewTranslation):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Edit(Draft):
    expected_version: int = Field(ge=1)


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=500)


class TranslationView(Draft):
    id: UUID
    locale: Locale
    state: Literal["draft", "published", "archived"]
    version: int
    published_revision_id: UUID | None


class PageView(BaseModel):
    id: UUID
    slug: str
    translations: list[TranslationView]


class PageList(BaseModel):
    items: list[PageView]
    next_cursor: UUID | None


class PublicPage(Draft):
    id: UUID
    slug: str
    locale: Locale
    revision_id: UUID
    published_at: datetime


class PublicList(BaseModel):
    items: list[PublicPage]
    next_cursor: UUID | None


class History(BaseModel):
    items: list[PublicPage]
    next_cursor: UUID | None
