"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { learningMessages } from "../../../lib/learning-messages";

type Locale = "en" | "ta";
type Learning = components["schemas"]["MyLearningView"];
type Course = components["schemas"]["LearnerCourseView"];
type Access = components["schemas"]["MaterialAccessView"];

export default function LearnerWorkspace({ org, locale }: { org: string; locale: Locale }) {
  const text = learningMessages[locale];
  const root = `/api/courses/organizations/${org}`;
  const [learning, setLearning] = useState<Learning>({ courses: [] });
  const [message, setMessage] = useState<string>(text.loading);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async () => {
    const response = await fetch(root + "/my-learning", { cache: "no-store" });
    if (!response.ok) throw new Error("request_failed");
    setLearning(await response.json() as Learning);
  }, [root]);

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

  async function mutate(path: string, data?: object) {
    setBusy(true);
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error();
      const response = await fetch(root + path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-csrf-token": (await csrf.json()).csrf_token,
        },
        body: data ? JSON.stringify(data) : undefined,
      });
      if (!response.ok) throw new Error();
      await load();
      setMessage(text.saved);
    } catch {
      setMessage(text.error);
    } finally {
      setBusy(false);
    }
  }

  const start = (courseId: string) => mutate(`/my-learning/${courseId}/start`);
  const complete = (course: Course, lessonId: string) => {
    if (!course.course_enrollment) return Promise.resolve();
    return mutate(`/my-learning/${course.id}/lessons/${lessonId}/complete`, {
      expected_course_enrollment_version: course.course_enrollment.version,
    });
  };
  async function openMaterial(courseId: string, materialId: string) {
    setBusy(true);
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error();
      const response = await fetch(
        root + `/my-learning/${courseId}/materials/${materialId}/access`,
        {
          method: "POST",
          headers: { "x-csrf-token": (await csrf.json()).csrf_token },
        },
      );
      if (!response.ok) throw new Error();
      const access = await response.json() as Access;
      window.location.assign(access.url);
    } catch {
      setMessage(text.error);
    } finally {
      setBusy(false);
    }
  }

  const value = (en: string, ta: string) => locale === "ta" ? ta : en;

  return <>
    <header className="learning-heading">
      <div><p className="eyebrow">{text.eyebrow}</p><h1>{text.learnerTitle}</h1>
        <p>{text.learnerIntro}</p></div>
      <Link href={`/${locale}/participant?organization=${org}`}>Schedule</Link>
    </header>
    <p className="learning-message" role="status">{busy ? text.loading : message}</p>
    {learning.courses.length === 0 && !busy && <p className="learning-empty">{text.empty}</p>}
    <ol className="learner-path">
      {learning.courses.map((course) => <li key={course.id}>
        <article>
          <header>
            <span className="learner-order">{String(course.position).padStart(2, "0")}</span>
            <div><small>{course.code}</small><h2>{value(course.title_en, course.title_ta)}</h2></div>
            {!course.course_enrollment
              ? <button disabled={busy} onClick={() => void start(course.id)}>{text.start}</button>
              : <span className="learning-progress">{course.progress.status === "completed"
                ? text.completed : text.continue}</span>}
          </header>
          <div className="course-meter" aria-label={text.progress}>
            <div><strong>{course.progress.percent}%</strong>
              <span>{course.progress.completed_lessons} / {course.progress.required_lessons} {text.lessons}</span></div>
            <progress max="100" value={course.progress.percent}>{course.progress.percent}%</progress>
          </div>
          <p>{value(course.description_en, course.description_ta)}</p>
          <ol className="learner-modules">
            {course.modules.map((module) => <li key={module.id}>
              <h3><span>{module.position}</span>{value(module.title_en, module.title_ta)}</h3>
              <ol>{module.lessons.map((lesson) => <li
                className={lesson.locked ? "lesson-locked" : lesson.completed ? "lesson-completed" : ""}
                key={lesson.id}
              >
                <div><strong>{value(lesson.title_en, lesson.title_ta)}</strong>
                  {lesson.duration_minutes && <small>{lesson.duration_minutes} min</small>}</div>
                <p>{value(lesson.body_en, lesson.body_ta)}</p>
                {lesson.locked && <small className="lesson-state">{text.locked}</small>}
                {lesson.completed && <small className="lesson-state">{text.completed}</small>}
                {course.course_enrollment && !lesson.locked && !lesson.completed &&
                  <button disabled={busy} onClick={() => void complete(course, lesson.id)}>
                    {text.markComplete}
                  </button>}
                {lesson.materials.map((material) => <p className="learning-private" key={material.id}>
                  <strong>{value(material.label_en, material.label_ta)}</strong>
                  {material.available
                    ? <button
                        disabled={busy}
                        onClick={() => void openMaterial(course.id, material.id)}
                      >
                        {text.openMaterial}
                      </button>
                    : <small>{text.materialUnavailable}</small>}
                </p>)}
              </li>)}</ol>
            </li>)}
          </ol>
        </article>
      </li>)}
    </ol>
  </>;
}
