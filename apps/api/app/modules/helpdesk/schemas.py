import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Category = Literal[
    "funding",
    "registration",
    "tax_compliance",
    "marketing",
    "technology",
    "business_planning",
    "banking",
    "mentoring",
    "general",
]
TicketStatus = Literal["open", "assigned", "in_progress", "waiting_for_user", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "urgent"]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def valid_text(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("Use valid UTF-8 text") from exc
            if any(
                (ord(char) < 32 and char not in "\n\r\t") or 127 <= ord(char) <= 159
                for char in value
            ):
                raise ValueError("Control characters are not accepted")
        return value


class AttachmentInput(Strict):
    filename: str = Field(min_length=5, max_length=120)
    content: str = Field(min_length=1, max_length=32768)

    @field_validator("filename")
    @classmethod
    def text_filename(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,115}\.txt", value):
            raise ValueError("Use a simple .txt filename")
        return value

    @field_validator("content")
    @classmethod
    def plain_text(cls, value: str) -> str:
        if (
            len(value.encode("utf-8")) > 32768
            or any(
                (ord(char) < 32 and char not in "\n\r\t") or 127 <= ord(char) <= 159
                for char in value
            )
            or re.search(r"<\s*[!/?a-zA-Z]|javascript\s*:", value, re.I)
        ):
            raise ValueError("Only UTF-8 plain text is accepted")
        return value


class TicketCreate(Strict):
    request_id: UUID
    category: Category
    subject: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    body: Body
    priority: Literal["low", "normal", "high"] = "normal"
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=3)


class TicketCommand(Strict):
    expected_version: int = Field(ge=1)
    reason: Reason


class MessageCreate(Strict):
    expected_version: int = Field(ge=1)
    body: Body
    internal: bool = False
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=3)


class AssignmentChange(TicketCommand):
    assignee_user_id: UUID


class PriorityChange(TicketCommand):
    priority: Priority


class StatusChange(TicketCommand):
    status: Literal["in_progress", "waiting_for_user", "resolved", "closed"]


class TicketOwnerView(BaseModel):
    id: UUID
    number: str
    category: Category
    subject: str
    status: TicketStatus
    priority: Priority
    version: int
    created_at: datetime
    updated_at: datetime
    access: Literal["owner"] = "owner"


class TicketStaffView(BaseModel):
    id: UUID
    number: str
    category: Category
    subject: str
    status: TicketStatus
    priority: Priority
    version: int
    created_at: datetime
    updated_at: datetime
    access: Literal["staff"] = "staff"
    assignee_user_id: UUID | None
    owner_participant_id: UUID
    owner_user_id: UUID


class TicketClaimView(BaseModel):
    id: UUID
    number: str
    category: Category
    status: TicketStatus
    priority: Priority
    version: int
    created_at: datetime
    updated_at: datetime
    access: Literal["claim"] = "claim"


TicketView = TicketOwnerView | TicketStaffView | TicketClaimView


class TicketList(BaseModel):
    items: list[TicketView]
    next_cursor: UUID | None


class AttachmentView(BaseModel):
    id: UUID
    filename: str
    size_bytes: int


class MessageView(BaseModel):
    id: UUID
    body: str
    internal: bool
    author_user_id: UUID
    created_at: datetime
    attachments: list[AttachmentView]


class MessageList(BaseModel):
    items: list[MessageView]
    next_cursor: UUID | None


class HistoryView(BaseModel):
    id: UUID
    event: str
    status: TicketStatus
    priority: Priority
    version: int
    reason: str | None
    actor_user_id: UUID
    created_at: datetime


class HistoryList(BaseModel):
    items: list[HistoryView]
    next_cursor: UUID | None


class AssigneeView(BaseModel):
    id: UUID
    display_name: str


class AssigneeList(BaseModel):
    items: list[AssigneeView]
    next_cursor: UUID | None


class NoticeView(BaseModel):
    id: UUID
    ticket_id: UUID
    event: str
    ticket_version: int
    version: int
    read_at: datetime | None
    created_at: datetime


class NoticeList(BaseModel):
    items: list[NoticeView]
    next_cursor: UUID | None


class ReadNotice(Strict):
    expected_version: int = Field(ge=1)


class HelpdeskPreferenceView(BaseModel):
    enabled: bool
    version: int


class PreferenceChange(ReadNotice):
    enabled: bool
