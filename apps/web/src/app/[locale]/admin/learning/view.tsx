"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { learningMessages } from "../../../../lib/learning-messages";

type Locale = "en" | "ta";
type Catalog = components["schemas"]["LearningCatalogView"];
type Course = components["schemas"]["AdminCourseView"];
type ProgramCatalog = components["schemas"]["CatalogView"];

const empty: Catalog = { courses: [], assignments: [] };
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

  return <div aria-busy={busy}>
    <p className="learning-message" role="status">{busy ? text.loading : message}</p>
    {canManage && <section className="learning-authoring" aria-label={text.structure}>
      <form onSubmit={(event) => submit(event, "", (data) => data)}>
        <h2>{text.createCourse}</h2>
        <Field label={text.code} name="code" />
        <Field label={text.englishTitle} name="title_en" />
        <Field label={text.tamilTitle} name="title_ta" />
        <Area label={text.englishDescription} name="description_en" />
        <Area label={text.tamilDescription} name="description_ta" />
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
            {course.modules.length > 0 && <ol className="learning-modules">
              {course.modules.map((module) => <li key={module.id}>
                <strong>{module.position}. {title(module)}</strong>
                <ol>{module.lessons.map((lesson) => <li key={lesson.id}>
                  <span>{lesson.position}. {title(lesson)}</span>
                  {lesson.duration_minutes && <small>{lesson.duration_minutes} min</small>}
                  {lesson.materials.map((material) =>
                    <small key={material.id}>{material.kind}: {locale === "ta" ? material.label_ta : material.label_en}</small>)}
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

