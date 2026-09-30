"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { learningMessages } from "../../../../lib/learning-messages";

type Locale = "en" | "ta";
type Catalog = components["schemas"]["LearningCatalogView"];
type Course = components["schemas"]["AdminCourseView"];
type ProgramCatalog = components["schemas"]["CatalogView"];

const empty: Catalog = { courses: [], assignments: [], progress_summaries: [] };
const emptyPrograms: ProgramCatalog = {
  programs: [],
  centers: [],
  cohorts: [],
  cycles: [],
  enrollment_candidates: [],
  participants: [],
  enrollments: [],
  sessions: [],
  staff_assignments: [],
};

export default function LearningWorkspace({
  org,
  locale,
  permissions,
}: {
  org: string;
  locale: Locale;
  permissions: string[];
}) {
  const text = learningMessages[locale];
  const root = `/api/courses/organizations/${org}`;
  const [catalog, setCatalog] = useState<Catalog>(empty);
  const [programs, setPrograms] = useState<ProgramCatalog>(emptyPrograms);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const canManage = permissions.includes("lms.course.manage");
  const canPublish = permissions.includes("lms.course.publish");
  const canAssign = permissions.includes("lms.course.assign");
  const canAssess = permissions.includes("lms.assessment.manage");

  const request = useCallback(async <T,>(
    path: string,
    method = "GET",
    data?: unknown,
  ): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const response = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!response.ok) throw new Error("service_unavailable");
      headers["x-csrf-token"] = (await response.json()).csrf_token;
    }
    const response = await fetch(path, {
      method,
      headers,
      body: data === undefined ? undefined : JSON.stringify(data),
      cache: "no-store",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.error?.code ?? "request_failed");
    return body as T;
  }, []);

  const load = useCallback(async () => {
    const [learning, programCatalog] = await Promise.all([
      request<Catalog>(root + "/catalog"),
      request<ProgramCatalog>(`/api/programs/organizations/${org}/catalog`),
    ]);
    setCatalog(learning);
    setPrograms(programCatalog);
  }, [org, request, root]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await load();
        if (active) setMessage("");
      } catch {
        if (active) setMessage(text.error);
      } finally {
        if (active) setBusy(false);
      }
    })();
    return () => { active = false; };
  }, [load, text.error]);

  async function run(action: () => Promise<unknown>, form?: HTMLFormElement) {
    setBusy(true);
    try {
      await action();
      await load();
      form?.reset();
      setMessage(text.saved);
    } catch {
      setMessage(text.error);
    } finally {
      setBusy(false);
    }
  }

  function submit(
    event: FormEvent<HTMLFormElement>,
    path: string,
    transform: (data: Record<string, FormDataEntryValue>) => object,
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    void run(() => request(root + path, "POST", transform(data)), form);
  }

  function publish(course: Course) {
    const reason = window.prompt(text.reason);
    if (!reason || reason.trim().length < 3) return;
    void run(() => request(
      root + `/${course.id}/publish`,
      "POST",
      { expected_version: course.version, reason: reason.trim() },
    ));
  }

  const title = (item: { title_en: string; title_ta: string }) =>
    locale === "ta" ? item.title_ta : item.title_en;
  const draftCourses = catalog.courses.filter((course) => course.state === "draft");
  const draftModules = draftCourses.flatMap((course) => course.modules.map((module) => ({
    course,
    module,
  })));
  const draftLessons = draftModules.flatMap(({ course, module }) =>
    module.lessons.map((lesson) => ({ course, module, lesson })));

  const draftQuizzes = draftLessons.flatMap(({ course, module, lesson }) =>
    lesson.quizzes.map((quiz) => ({ course, module, lesson, quiz })));
  const draftQuestions = draftQuizzes.flatMap(({ course, module, lesson, quiz }) =>
    quiz.questions.map((question) => ({ course, module, lesson, quiz, question })));

  return <div aria-busy={busy}>
    <p className="learning-message" role="status">{busy ? text.loading : message}</p>
    {canManage && <section className="learning-authoring" aria-label={text.structure}>
      <form onSubmit={(event) => submit(event, "", (data) => ({
        ...data,
        completion_rule: data.completion_rule,
        minimum_lessons: data.completion_rule === "minimum_lessons" ? Number(data.minimum_lessons) : null,
      }))}>
        <h2>{text.createCourse}</h2>
        <Field label={text.code} name="code" />
        <Field label={text.englishTitle} name="title_en" />
        <Field label={text.tamilTitle} name="title_ta" />
        <Area label={text.englishDescription} name="description_en" />
        <Area label={text.tamilDescription} name="description_ta" />
        <label>{text.completionRule}<select name="completion_rule">
          <option value="all_lessons">{text.allLessons}</option>
          <option value="minimum_lessons">{text.minimumLessons}</option>
        </select></label>
        <Field label={text.minimumLessons} name="minimum_lessons" type="number" required={false} />
        <button disabled={busy}>{text.create}</button>
      </form>
      <form onSubmit={(event) => submit(event, "/modules", (data) => ({
        ...data,
        position: Number(data.position),
      }))}>
        <h2>{text.addModule}</h2>
        <Select
          label={text.course}
          name="course_id"
          choose={text.choose}
          options={draftCourses.map((course) => [course.id, title(course)])}
        />
        <Field label={text.position} name="position" type="number" />
        <Field label={text.englishTitle} name="title_en" />
        <Field label={text.tamilTitle} name="title_ta" />
        <button disabled={busy}>{text.create}</button>
      </form>
      <form onSubmit={(event) => submit(event, "/lessons", (data) => {
        const key = String(data.module_key).split(":");
        return {
          course_id: key[0],
          module_id: key[1],
          position: Number(data.position),
          duration_minutes: data.duration_minutes
            ? Number(data.duration_minutes)
            : null,
          title_en: data.title_en,
          title_ta: data.title_ta,
          body_en: data.body_en,
          body_ta: data.body_ta,
        };
      })}>
        <h2>{text.addLesson}</h2>
        <Select
          label={text.module}
          name="module_key"
          choose={text.choose}
          options={draftModules.map(({ course, module }) => [
            `${course.id}:${module.id}`,
            `${title(course)} / ${title(module)}`,
          ])}
        />
        <Field label={text.position} name="position" type="number" />
        <Field label={text.duration} name="duration_minutes" type="number" required={false} />
        <Field label={text.englishTitle} name="title_en" />
        <Field label={text.tamilTitle} name="title_ta" />
        <Area label={text.englishBody} name="body_en" />
        <Area label={text.tamilBody} name="body_ta" />
        <button disabled={busy}>{text.create}</button>
      </form>
      <form onSubmit={(event) => submit(event, "/prerequisites", (data) => {
        const target = String(data.lesson_key).split(":");
        const required = String(data.prerequisite_key).split(":");
        return { course_id: target[0], lesson_id: target[1],
          prerequisite_lesson_id: required[1], reason: data.reason };
      })}>
        <h2>{text.addPrerequisite}</h2>
        <Select label={text.lesson} name="lesson_key" choose={text.choose}
          options={draftLessons.map(({ course, module, lesson }) => [
            `${course.id}:${lesson.id}`, `${title(course)} / ${title(module)} / ${title(lesson)}`,
          ])} />
        <Select label={text.prerequisite} name="prerequisite_key" choose={text.choose}
          options={draftLessons.map(({ course, module, lesson }) => [
            `${course.id}:${lesson.id}`, `${title(course)} / ${title(module)} / ${title(lesson)}`,
          ])} />
        <Field label={text.reason} name="reason" />
        <button disabled={busy}>{text.create}</button>
      </form>
      <form onSubmit={(event) => submit(event,
        `/${String(new FormData(event.currentTarget).get("course_id"))}/completion-rule`,
        (data) => {
          const course = draftCourses.find((item) => item.id === data.course_id);
          return { completion_rule: data.completion_rule,
            minimum_lessons: data.completion_rule === "minimum_lessons" ? Number(data.minimum_lessons) : null,
            expected_version: course?.version ?? 1, reason: data.reason };
        })}>
        <h2>{text.completionRule}</h2>
        <Select label={text.course} name="course_id" choose={text.choose}
          options={draftCourses.map((course) => [course.id, title(course)])} />
        <label>{text.completionRule}<select name="completion_rule">
          <option value="all_lessons">{text.allLessons}</option>
          <option value="minimum_lessons">{text.minimumLessons}</option>
        </select></label>
        <Field label={text.minimumLessons} name="minimum_lessons" type="number" required={false} />
        <Field label={text.reason} name="reason" />
        <button disabled={busy}>{text.saveRule}</button>
      </form>
      {canAssess && <form onSubmit={(event) => submit(event, "/quizzes", (data) => {
        const key = String(data.lesson_key).split(":");
        return {
          course_id: key[0],
          lesson_id: key[1],
          position: Number(data.position),
          title_en: data.title_en,
          title_ta: data.title_ta,
          instructions_en: data.instructions_en,
          instructions_ta: data.instructions_ta,
          passing_percent: Number(data.passing_percent),
          max_attempts: Number(data.max_attempts),
        };
      })}>
        <h2>{text.addQuiz}</h2>
        <Select label={text.lesson} name="lesson_key" choose={text.choose}
          options={draftLessons.map(({ course, module, lesson }) => [
            `${course.id}:${lesson.id}`, `${title(course)} / ${title(module)} / ${title(lesson)}`,
          ])} />
        <Field label={text.position} name="position" type="number" />
        <Field label={text.englishTitle} name="title_en" />
        <Field label={text.tamilTitle} name="title_ta" />
        <Area label={text.englishInstructions} name="instructions_en" />
        <Area label={text.tamilInstructions} name="instructions_ta" />
        <label>{text.passingPercent}<input name="passing_percent" type="number" min="0" max="100" required /></label>
        <label>{text.maxAttempts}<input name="max_attempts" type="number" min="1" max="10" required /></label>
        <button disabled={busy}>{text.create}</button>
      </form>}
      {canAssess && <form onSubmit={(event) => submit(event, "/quiz-questions", (data) => {
        const key = String(data.quiz_key).split(":");
        return {
          course_id: key[0],
          quiz_id: key[1],
          position: Number(data.position),
          prompt_en: data.prompt_en,
          prompt_ta: data.prompt_ta,
          points: Number(data.points),
        };
      })}>
        <h2>{text.addQuestion}</h2>
        <Select label={text.quiz} name="quiz_key" choose={text.choose}
          options={draftQuizzes.map(({ course, lesson, quiz }) => [
            `${course.id}:${quiz.id}`, `${title(course)} / ${title(lesson)} / ${title(quiz)}`,
          ])} />
        <Field label={text.position} name="position" type="number" />
        <Area label={text.englishQuestion} name="prompt_en" />
        <Area label={text.tamilQuestion} name="prompt_ta" />
        <Field label={text.points} name="points" type="number" />
        <button disabled={busy}>{text.create}</button>
      </form>}
      {canAssess && <form onSubmit={(event) => submit(event, "/quiz-choices", (data) => {
        const key = String(data.question_key).split(":");
        return {
          course_id: key[0],
          quiz_id: key[1],
          question_id: key[2],
          position: Number(data.position),
          label_en: data.label_en,
          label_ta: data.label_ta,
          is_correct: data.is_correct === "on",
        };
      })}>
        <h2>{text.addChoice}</h2>
        <Select label={text.question} name="question_key" choose={text.choose}
          options={draftQuestions.map(({ course, quiz, question }) => [
            `${course.id}:${quiz.id}:${question.id}`,
            `${title(course)} / ${title(quiz)} / ${locale === "ta" ? question.prompt_ta : question.prompt_en}`,
          ])} />
        <Field label={text.position} name="position" type="number" />
        <Field label={text.englishChoice} name="label_en" />
        <Field label={text.tamilChoice} name="label_ta" />
        <label><input name="is_correct" type="checkbox" /> {text.correctChoice}</label>
        <button disabled={busy}>{text.create}</button>
      </form>}
      <form onSubmit={(event) => submit(event, "/materials", (data) => {
        const key = String(data.lesson_key).split(":");
        return {
          course_id: key[0],
          lesson_id: key[1],
          position: Number(data.position),
          kind: data.kind,
          label_en: data.label_en,
          label_ta: data.label_ta,
          provider_key: data.provider_key,
        };
      })}>
        <h2>{text.addMaterial}</h2>
        <Select
          label={text.lesson}
          name="lesson_key"
          choose={text.choose}
          options={draftLessons.map(({ course, module, lesson }) => [
            `${course.id}:${lesson.id}`,
            `${title(course)} / ${title(module)} / ${title(lesson)}`,
          ])}
        />
        <Field label={text.position} name="position" type="number" />
        <label>{text.kind}<select name="kind">
          <option value="document">Document</option>
          <option value="video">Video</option>
          <option value="link">Link</option>
        </select></label>
        <Field label={text.englishTitle} name="label_en" />
        <Field label={text.tamilTitle} name="label_ta" />
        <Field label={text.providerKey} name="provider_key" />
        <button disabled={busy}>{text.create}</button>
      </form>
    </section>}

    <section className="learning-catalog">
      <h2>{text.courses}</h2>
      {catalog.courses.length === 0 && <p>{text.empty}</p>}
      <ol className="learning-spine">
        {catalog.courses.map((course) => <li key={course.id}>
          <article className="learning-course">
            <header><div><small>{course.code}</small><h3>{title(course)}</h3></div>
              <span className={`program-state program-state-${course.state}`}>
                {course.state === "draft" ? text.draft : text.published}
              </span></header>
            <p>{locale === "ta" ? course.description_ta : course.description_en}</p>
            <p className="learning-rule"><strong>{text.completionRule}:</strong> {
              course.completion_rule === "all_lessons" ? text.allLessons
                : `${text.minimumLessons}: ${course.minimum_lessons}`
            }</p>
            {course.modules.length > 0 && <ol className="learning-modules">
              {course.modules.map((module) => <li key={module.id}>
                <strong>{module.position}. {title(module)}</strong>
                <ol>{module.lessons.map((lesson) => <li key={lesson.id}>
                  <span>{lesson.position}. {title(lesson)}</span>
                  {lesson.duration_minutes && <small>{lesson.duration_minutes} min</small>}
                  {lesson.prerequisite_lesson_ids.length > 0 &&
                    <small>{text.prerequisite}: {lesson.prerequisite_lesson_ids.length}</small>}
                  {lesson.materials.map((material) =>
                    <small key={material.id}>{material.kind}: {locale === "ta" ? material.label_ta : material.label_en}</small>)}
                  {lesson.quizzes.map((quiz) => <small key={quiz.id}>
                    {text.quiz}: {title(quiz)} - {quiz.questions.length} {text.questions} - {quiz.passing_percent}%
                  </small>)}
                </li>)}</ol>
              </li>)}
            </ol>}
            {canPublish && course.state === "draft" &&
              <button disabled={busy} onClick={() => publish(course)}>{text.publish}</button>}
          </article>
        </li>)}
      </ol>
    </section>

    {canAssign && <section className="learning-assignment">
      <h2>{text.assignments}</h2>
      <form onSubmit={(event) => submit(event, "/cohort-assignments", (data) => ({
        course_id: data.course_id,
        cohort_id: data.cohort_id,
        position: Number(data.position),
        reason: data.reason,
      }))}>
        <Select
          label={text.course}
          name="course_id"
          choose={text.choose}
          options={catalog.courses
            .filter((course) => course.state === "published")
            .map((course) => [course.id, title(course)])}
        />
        <Select
          label={text.cohort}
          name="cohort_id"
          choose={text.choose}
          options={programs.cohorts
            .filter((cohort) => ["planned", "active"].includes(cohort.state))
            .map((cohort) => [
              cohort.id,
              locale === "ta" ? cohort.name_ta : cohort.name_en,
            ])}
        />
        <Field label={text.position} name="position" type="number" />
        <Field label={text.reason} name="reason" />
        <button disabled={busy}>{text.assign}</button>
      </form>
      <ul>{catalog.assignments.map((assignment) => {
        const course = catalog.courses.find((item) => item.id === assignment.course_id);
        const cohort = programs.cohorts.find((item) => item.id === assignment.cohort_id);
        return <li key={assignment.id}>
          <strong>{course ? title(course) : assignment.course_id}</strong>
          <span>{assignment.position}. {cohort
            ? (locale === "ta" ? cohort.name_ta : cohort.name_en)
            : assignment.cohort_id}</span>
        </li>;
      })}</ul>
      <h3>{text.progress}</h3>
      <ul>{catalog.progress_summaries.map((summary) => <li
        key={`${summary.cohort_id}:${summary.course_id}`}
      ><strong>{summary.completed_learners} / {summary.assigned_learners} {text.completed}</strong>
        <span>{summary.started_learners} {text.started} | {summary.average_percent}% {text.average}</span>
      </li>)}</ul>
    </section>}
  </div>;
}

function Field({
  label,
  name,
  type = "text",
  required = true,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
}) {
  return <label>{label}<input name={name} type={type} required={required} min={type === "number" ? 1 : undefined} /></label>;
}

function Area({ label, name }: { label: string; name: string }) {
  return <label>{label}<textarea name={name} required /></label>;
}

function Select({
  label,
  name,
  options,
  choose,
}: {
  label: string;
  name: string;
  options: [string, string][];
  choose: string;
  onSplit?: boolean;
}) {
  return <label>{label}<select name={name} required>
    <option value="">{choose}</option>
    {options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
  </select></label>;
}
