"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { learningMessages } from "../../../../lib/learning-messages";

type Locale = "en" | "ta";
type Delivery = components["schemas"]["TrainerDeliveryView"];
type Access = components["schemas"]["MaterialAccessView"];

export default function TrainerLearningWorkspace({
  org,
  locale,
}: {
  org: string;
  locale: Locale;
}) {
  const text = learningMessages[locale];
  const root = `/api/courses/organizations/${org}`;
  const [delivery, setDelivery] = useState<Delivery>({ courses: [] });
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const value = (en: string, ta: string) => locale === "ta" ? ta : en;

  const load = useCallback(async () => {
    const response = await fetch(root + "/trainer-delivery", { cache: "no-store" });
    if (!response.ok) throw new Error("request_failed");
    setDelivery(await response.json() as Delivery);
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

  async function openMaterial(courseId: string, materialId: string) {
    setBusy(true);
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const response = await fetch(
        root + `/trainer-delivery/${courseId}/materials/${materialId}/access`,
        {
          method: "POST",
          headers: { "x-csrf-token": (await csrf.json()).csrf_token },
        },
      );
      if (!response.ok) throw new Error("request_failed");
      const access = await response.json() as Access;
      window.location.assign(access.url);
    } catch {
      setMessage(text.error);
    } finally {
      setBusy(false);
    }
  }

  return <section aria-busy={busy} aria-label={text.trainerTitle}>
    <p>{text.trainerIntro}</p>
    <p className="learning-message" role="status">{busy ? text.loading : message}</p>
    {!busy && delivery.courses.length === 0 && <p className="learning-empty">{text.noAssignments}</p>}
    <ol className="learner-path">
      {delivery.courses.map((course) => <li key={course.cohort_id + course.course_id}>
        <article>
          <header>
            <span className="learner-order">{course.course_code}</span>
            <div>
              <small>{text.cohort}: {value(course.cohort_name_en, course.cohort_name_ta)}</small>
              <h2>{value(course.title_en, course.title_ta)}</h2>
            </div>
          </header>
          <ol className="learner-modules">
            {course.modules.map((module) => <li key={module.id}>
              <h3><span>{module.position}</span>{value(module.title_en, module.title_ta)}</h3>
              <ol>{module.lessons.map((lesson) => <li key={lesson.id}>
                <div>
                  <strong>{value(lesson.title_en, lesson.title_ta)}</strong>
                  {lesson.duration_minutes && <small>{lesson.duration_minutes} min</small>}
                </div>
                {lesson.materials.map((material) => <p className="learning-private" key={material.id}>
                  <strong>{value(material.label_en, material.label_ta)}</strong>
                  <button
                    disabled={busy || !material.available}
                    onClick={() => void openMaterial(course.course_id, material.id)}
                  >
                    {text.openMaterial}
                  </button>
                </p>)}
              </li>)}</ol>
            </li>)}
          </ol>
          <section aria-label={text.learners}>
            <h3>{text.learners}</h3>
            {course.learners.map((learner) => <div key={learner.participant_id}>
              <div className="course-meter">
                <div>
                  <strong>{learner.display_name}</strong>
                  <span>{learner.course_enrollment
                    ? `${learner.progress.completed_lessons} / ${learner.progress.required_lessons} ${text.lessons}`
                    : text.notStarted}</span>
                </div>
                <progress max="100" value={learner.progress.percent}>
                  {learner.progress.percent}%
                </progress>
              </div>
              <ul>{learner.quiz_results.map((result) => <li key={result.quiz_id}>
                <strong>{value(result.title_en, result.title_ta)}</strong>{" "}
                <span>{result.attempt_count} {text.attempts} - {
                  result.best_percent === null ? text.notAttempted : `${text.bestScore}: ${result.best_percent}%`
                } - {result.passed ? text.passed : text.notPassed}</span>
              </li>)}</ul>
            </div>)}
          </section>
        </article>
      </li>)}
    </ol>
  </section>;
}
