"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { learningMessages } from "../../../lib/learning-messages";

type Locale = "en" | "ta";
type Learning = components["schemas"]["MyLearningView"];

export default function LearnerWorkspace({
  org,
  locale,
}: {
  org: string;
  locale: Locale;
}) {
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

  async function start(courseId: string) {
    setBusy(true);
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error();
      const response = await fetch(root + `/my-learning/${courseId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-csrf-token": (await csrf.json()).csrf_token,
        },
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
            <div><small>{course.code}</small>
              <h2>{value(course.title_en, course.title_ta)}</h2></div>
            {course.course_enrollment
              ? <span className="learning-progress">{text.continue}</span>
              : <button disabled={busy} onClick={() => void start(course.id)}>{text.start}</button>}
          </header>
          <p>{value(course.description_en, course.description_ta)}</p>
          <ol className="learner-modules">
            {course.modules.map((module) => <li key={module.id}>
              <h3><span>{module.position}</span>{value(module.title_en, module.title_ta)}</h3>
              <ol>{module.lessons.map((lesson) => <li key={lesson.id}>
                <div><strong>{value(lesson.title_en, lesson.title_ta)}</strong>
                  {lesson.duration_minutes && <small>{lesson.duration_minutes} min</small>}</div>
                <p>{value(lesson.body_en, lesson.body_ta)}</p>
                {lesson.materials.map((material) => <p
                  className="learning-private"
                  key={material.id}
                ><strong>{value(material.label_en, material.label_ta)}</strong>
                  <small>{text.privatePending}</small></p>)}
              </li>)}</ol>
            </li>)}
          </ol>
        </article>
      </li>)}
    </ol>
  </>;
}
