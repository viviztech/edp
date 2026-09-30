from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CourseState = Literal["draft", "published", "archived"]
MaterialKind = Literal["video", "document", "link"]
CourseEnrollmentState = Literal["in_progress", "completed"]
CompletionRule = Literal["all_lessons", "minimum_lessons"]
ProgressState = Literal["not_started", "in_progress", "completed"]


class CourseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_-]*$")
    title_en: str = Field(min_length=1, max_length=200)
    title_ta: str = Field(min_length=1, max_length=200)
    description_en: str = Field(min_length=1, max_length=5000)
    description_ta: str = Field(min_length=1, max_length=5000)
    completion_rule: CompletionRule = "all_lessons"
    minimum_lessons: int | None = Field(default=None, ge=1)

    @field_validator("code", "title_en", "title_ta", "description_en", "description_ta")
    @classmethod
    def strip_course_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def valid_completion_rule(self) -> "CourseCreate":
        if self.completion_rule == "all_lessons" and self.minimum_lessons is not None:
            raise ValueError("minimum_lessons must be empty for all_lessons")
        if self.completion_rule == "minimum_lessons" and self.minimum_lessons is None:
            raise ValueError("minimum_lessons is required")
        return self


class CourseView(CourseCreate):
    id: UUID
    organization_id: UUID
    state: CourseState
    version: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CompletionRuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completion_rule: CompletionRule
    minimum_lessons: int | None = Field(default=None, ge=1)
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def valid_completion_rule(self) -> "CompletionRuleUpdate":
        if self.completion_rule == "all_lessons" and self.minimum_lessons is not None:
            raise ValueError("minimum_lessons must be empty for all_lessons")
        if self.completion_rule == "minimum_lessons" and self.minimum_lessons is None:
            raise ValueError("minimum_lessons is required")
        return self


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


class LessonPrerequisiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_id: UUID
    lesson_id: UUID
    prerequisite_lesson_id: UUID
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class LessonPrerequisiteView(BaseModel):
    id: UUID
    organization_id: UUID
    course_id: UUID
    lesson_id: UUID
    prerequisite_lesson_id: UUID
    created_at: datetime


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
    prerequisite_lesson_ids: list[UUID]


class AdminModuleView(ModuleView):
    lessons: list[AdminLessonView]


class AdminCourseView(CourseView):
    modules: list[AdminModuleView]


class CourseProgressSummary(BaseModel):
    course_id: UUID
    cohort_id: UUID
    assigned_learners: int
    started_learners: int
    completed_learners: int
    average_percent: int


class LearningCatalogView(BaseModel):
    courses: list[AdminCourseView]
    assignments: list[CohortCourseView]
    progress_summaries: list[CourseProgressSummary]


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


class CourseProgressView(BaseModel):
    total_lessons: int
    required_lessons: int
    completed_lessons: int
    percent: int
    status: ProgressState


class LessonCompletionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_course_enrollment_version: int = Field(ge=1)


class LessonProgressView(BaseModel):
    id: UUID
    course_enrollment_id: UUID
    course_id: UUID
    lesson_id: UUID
    completed_at: datetime
    course_enrollment: CourseEnrollmentView
    progress: CourseProgressView


class LearnerLessonView(BaseModel):
    id: UUID
    position: int
    title_en: str
    title_ta: str
    body_en: str
    body_ta: str
    duration_minutes: int | None
    prerequisite_lesson_ids: list[UUID]
    locked: bool
    completed: bool
    completed_at: datetime | None
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
    completion_rule: CompletionRule
    minimum_lessons: int | None
    cohort_id: UUID
    enrollment_id: UUID
    position: int
    course_enrollment: CourseEnrollmentView | None
    progress: CourseProgressView
    modules: list[LearnerModuleView]


class MyLearningView(BaseModel):
    courses: list[LearnerCourseView]


class MaterialAccessView(BaseModel):
    url: str
    expires_at: datetime


class TrainerLessonView(BaseModel):
    id: UUID
    position: int
    title_en: str
    title_ta: str
    duration_minutes: int | None
    materials: list[LearnerMaterialView]


class TrainerModuleView(BaseModel):
    id: UUID
    position: int
    title_en: str
    title_ta: str
    lessons: list[TrainerLessonView]


class TrainerLearnerProgressView(BaseModel):
    participant_id: UUID
    display_name: str
    course_enrollment: CourseEnrollmentView | None
    progress: CourseProgressView


class TrainerCourseDeliveryView(BaseModel):
    course_id: UUID
    cohort_id: UUID
    course_code: str
    title_en: str
    title_ta: str
    cohort_name_en: str
    cohort_name_ta: str
    modules: list[TrainerModuleView]
    learners: list[TrainerLearnerProgressView]


class TrainerDeliveryView(BaseModel):
    courses: list[TrainerCourseDeliveryView]
