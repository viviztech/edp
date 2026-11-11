"use client";
import { Card } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Textarea } from "../../../components/ui/textarea";


import Image from "next/image";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
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
  function submitQuiz(
    event: FormEvent<HTMLFormElement>,
    courseId: string,
    quizId: string,
  ) {
    event.preventDefault();
    const answers = Array.from(new FormData(event.currentTarget).entries()).map(
      ([question_id, choice_id]) => ({ question_id, choice_id }),
    );
    void mutate(`/my-learning/${courseId}/quizzes/${quizId}/attempts`, { answers });
  }

  function submitAssignment(
    event: FormEvent<HTMLFormElement>,
    courseId: string,
    assignmentId: string,
  ) {
    event.preventDefault();
    const responseText = String(new FormData(event.currentTarget).get("response_text") ?? "");
    void mutate(
      "/my-learning/" + courseId + "/assignments/" + assignmentId + "/submissions",
      { response_text: responseText },
    );
  }

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
      <Link href={`/${locale}/participant?organization=${org}`}>{locale === "ta" ? "\u0b85\u0b9f\u0bcd\u0b9f\u0bb5\u0ba3\u0bc8" : "Schedule"}</Link>
    </header>
    <p className="learning-message" role="status">{busy ? text.loading : message}</p>
    {learning.courses.length === 0 && !busy && !message && <p className="learning-empty">{text.empty}</p>}
    <ol className="learner-path">
      {learning.courses.map((course) => <li key={course.id}>
        <Card className="learner-course-card" role="article">
          <header>
            <span className="learner-order">{String(course.position).padStart(2, "0")}</span>
            <div><small>{course.code}</small><h2>{value(course.title_en, course.title_ta)}</h2></div>
            {!course.course_enrollment
              ? <Button type="button" disabled={busy} onClick={() => void start(course.id)}>{text.start}</Button>
              : <span className="learning-progress">{course.progress.status === "completed"
                ? text.completed : text.continue}</span>}
          </header>
          <div className="course-meter" aria-label={text.progress}>
            <div><strong>{course.progress.percent}%</strong>
              <span>{course.progress.completed_lessons} / {course.progress.required_lessons} {text.lessons}</span></div>
            <progress max="100" value={course.progress.percent}>{course.progress.percent}%</progress>
          </div>
          <section className="learning-private" aria-label={text.certificateEligibility}>
            <strong>{text.certificateEligibility}</strong>
            <p>{course.certificate_eligibility.eligible ? text.eligible : text.notEligible}</p>
            <small>{text.quiz}: {course.certificate_eligibility.passed_quizzes}/
              {course.certificate_eligibility.required_quizzes} | {text.assignment}: {
                course.certificate_eligibility.passed_assignments}/
              {course.certificate_eligibility.required_assignments}</small>
            {course.certificate && <article className="certificate-card">
              <Image
                alt={text.certificateQr}
                height="120"
                src={`/api/certificates/verify/${course.certificate.verification_code}/qr`}
                unoptimized
                width="120"
              />
              <div>
                <strong>{value(
                  course.certificate.certificate_title_en,
                  course.certificate.certificate_title_ta,
                )}</strong>
                <p>{text.certificateStatus}: {course.certificate.status}</p>
                <Link href={`/${locale}/certificates/${course.certificate.verification_code}`}>
                  {text.verifyCertificate}
                </Link>
              </div>
            </article>}
          </section>
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
                  <Button type="button" disabled={busy} onClick={() => void complete(course, lesson.id)}>
                    {text.markComplete}
                  </Button>}
                {lesson.materials.map((material) => <p className="learning-private" key={material.id}>
                  <strong>{value(material.label_en, material.label_ta)}</strong>
                  {material.available
                    ? <Button
                        type="button"
                        disabled={busy}
                        onClick={() => void openMaterial(course.id, material.id)}
                      >
                        {text.openMaterial}
                      </Button>
                    : <small>{text.materialUnavailable}</small>}
                </p>)}
                {lesson.quizzes.map((quiz) => <form
                  className="learning-private"
                  key={quiz.id}
                  onSubmit={(event) => submitQuiz(event, course.id, quiz.id)}
                >
                  <strong>{value(quiz.title_en, quiz.title_ta)}</strong>
                  <p>{value(quiz.instructions_en, quiz.instructions_ta)}</p>
                  <small>
                    {text.passMark}: {quiz.passing_percent}% - {text.attempts}: {quiz.attempt_count}/{quiz.max_attempts}
                    {quiz.best_percent !== null && ` - ${text.bestScore}: ${quiz.best_percent}%`}
                  </small>
                  {quiz.questions.map((question) => <fieldset key={question.id}>
                    <legend>{question.position}. {value(question.prompt_en, question.prompt_ta)} ({question.points} {text.points})</legend>
                    {question.choices.map((choice) => <label key={choice.id}>
                      <input
                        disabled={busy || !quiz.available || quiz.passed || quiz.remaining_attempts === 0}
                        name={question.id}
                        type="radio"
                        value={choice.id}
                        required
                      />
                      {value(choice.label_en, choice.label_ta)}
                    </label>)}
                  </fieldset>)}
                  {quiz.passed
                    ? <strong>{text.passed}</strong>
                    : quiz.available && quiz.remaining_attempts > 0
                      ? <Button disabled={busy} type="submit">{text.submitQuiz}</Button>
                      : <small>{text.quizUnavailable}</small>}
                </form>)}
                {lesson.assignments.map((assignment) => <form
                  className="learning-private"
                  key={assignment.id}
                  onSubmit={(event) => submitAssignment(event, course.id, assignment.id)}
                >
                  <strong>{value(assignment.title_en, assignment.title_ta)}</strong>
                  <p>{value(assignment.instructions_en, assignment.instructions_ta)}</p>
                  <small>
                    {text.passMark}: {assignment.passing_points}/{assignment.maximum_points} - {text.remainingSubmissions}: {assignment.remaining_submissions}
                  </small>
                  {assignment.submissions.map((submission) => <article key={submission.id}>
                    <small>{text.revision} {submission.revision}</small>
                    <p>{submission.response_text}</p>
                    {submission.grade
                      ? <p><strong>{submission.grade.score_points}/{assignment.maximum_points}</strong> - {
                        submission.grade.passed ? text.passed : text.notPassed
                      }<br />{text.feedback}: {submission.grade.feedback}</p>
                      : <small>{text.awaitingReview}</small>}
                  </article>)}
                  {assignment.available && assignment.remaining_submissions > 0
                    && (assignment.submissions.length === 0
                      || assignment.submissions.at(-1)?.grade)
                    ? <>
                      <label>{text.assignmentResponse}<Textarea name="response_text" required /></label>
                      <Button disabled={busy} type="submit">{text.submitAssignment}</Button>
                    </>
                    : assignment.remaining_submissions === 0
                      ? <small>{text.submissionLimitReached}</small>
                      : <small>{text.assignmentUnavailable}</small>}
                </form>)}
              </li>)}</ol>
            </li>)}
          </ol>
        </Card>
      </li>)}
    </ol>
  </>;
}
