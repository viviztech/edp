from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CourseState = Literal["draft", "published", "archived"]
MaterialKind = Literal["video", "document", "link"]
CourseEnrollmentState = Literal["in_progress", "completed"]


class CourseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_-]*$")
    title_en: str = Field(min_length=1, max_length=200)
    title_ta: str = Field(min_length=1, max_length=200)
    description_en: str = Field(min_length=1, max_length=5000)
    description_ta: str = Field(min_length=1, max_length=5000)

    @field_validator("code", "title_en", "title_ta", "description_en", "description_ta")
    @classmethod
    def strip_course_text(cls, value: str) -> str:
        return value.strip()


class CourseView(CourseCreate):
    id: UUID
    organization_id: UUID
    state: CourseState
    version: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_id: UUID
    position: int = Field(ge=1)
    title_en: str = Field(min_length=1, max_length=200)
    title_ta: str = Field(min_length=1, max_length=200)

    @field_validator("title_en", "title_ta")
    @classmethod
    def strip_module_text(cls, value: str) -> str:
        return value.strip()


class ModuleView(ModuleCreate):
    id: UUID
    organization_id: UUID
    created_at: datetime


class LessonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_id: UUID
    module_id: UUID
    position: int = Field(ge=1)
    title_en: str = Field(min_length=1, max_length=200)
    title_ta: str = Field(min_length=1, max_length=200)
    body_en: str = Field(min_length=1, max_length=20000)
    body_ta: str = Field(min_length=1, max_length=20000)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @field_validator("title_en", "title_ta", "body_en", "body_ta")
    @classmethod
    def strip_lesson_text(cls, value: str) -> str:
        return value.strip()


class LessonView(LessonCreate):
    id: UUID
    organization_id: UUID
    created_at: datetime


class MaterialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_id: UUID
    lesson_id: UUID
    position: int = Field(ge=1)
    kind: MaterialKind
    label_en: str = Field(min_length=1, max_length=200)
    label_ta: str = Field(min_length=1, max_length=200)
    provider_key: str = Field(min_length=1, max_length=500)

    @field_validator("label_en", "label_ta", "provider_key")
    @classmethod
    def strip_material_text(cls, value: str) -> str:
        return value.strip()


class MaterialAdminView(MaterialCreate):
    id: UUID
    organization_id: UUID
    is_private: bool
    created_at: datetime


class LearnerMaterialView(BaseModel):
    id: UUID
    position: int
    kind: MaterialKind
    label_en: str
    label_ta: str
    available: bool = False


class PublishCourse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class CohortCourseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_id: UUID
    cohort_id: UUID
    position: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_assignment_reason(cls, value: str) -> str:
        return value.strip()


class CohortCourseView(BaseModel):
    id: UUID
    organization_id: UUID
    course_id: UUID
    cohort_id: UUID
    position: int
    created_at: datetime


class AdminLessonView(LessonView):
    materials: list[MaterialAdminView]


class AdminModuleView(ModuleView):
    lessons: list[AdminLessonView]


class AdminCourseView(CourseView):
    modules: list[AdminModuleView]


class LearningCatalogView(BaseModel):
    courses: list[AdminCourseView]
    assignments: list[CohortCourseView]


class CourseEnrollmentView(BaseModel):
    id: UUID
    organization_id: UUID
    enrollment_id: UUID
    course_id: UUID
    status: CourseEnrollmentState
    version: int
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LearnerLessonView(BaseModel):
    id: UUID
    position: int
    title_en: str
    title_ta: str
    body_en: str
    body_ta: str
    duration_minutes: int | None
    materials: list[LearnerMaterialView]


class LearnerModuleView(BaseModel):
    id: UUID
    position: int
    title_en: str
    title_ta: str
    lessons: list[LearnerLessonView]


class LearnerCourseView(BaseModel):
    id: UUID
    code: str
    title_en: str
    title_ta: str
    description_en: str
    description_ta: str
    cohort_id: UUID
    enrollment_id: UUID
    position: int
    course_enrollment: CourseEnrollmentView | None
    modules: list[LearnerModuleView]


class MyLearningView(BaseModel):
    courses: list[LearnerCourseView]
