"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  Compass,
  FileText,
  RotateCcw,
  Sprout,
  Users,
} from "lucide-react";
import type { Locale } from "../lib/messages";
import { demoCopy } from "../lib/demo-copy";

type Step = "intro" | "profile" | "application" | "receipt" | "dashboard";
const example = {
  en: {
    name: "Ananya",
    city: "Madurai",
    idea: "Reusable gift packaging for local makers and small businesses.",
    goals: "Understand customer needs and test a small first offer.",
  },
  ta: {
    name: "அனன்யா",
    city: "மதுரை",
    idea: "உள்ளூர் தயாரிப்பாளர்கள் மற்றும் சிறு தொழில்களுக்கான மீண்டும் பயன்படுத்தக்கூடிய பரிசுப் பொதி.",
    goals: "வாடிக்கையாளர் தேவைகளை அறிந்து சிறிய முதல் சேவையைச் சோதிப்பது.",
  },
};

export function DemoExperience({ locale }: { locale: Locale }) {
  const t = demoCopy[locale];
  const [step, setStep] = useState<Step>("intro");
  const [name, setName] = useState(example[locale].name);
  const [draft, setDraft] = useState({
    city: example[locale].city,
    stage: "0",
    idea: example[locale].idea,
    goals: example[locale].goals,
  });
  const [consent, setConsent] = useState(false);
  const [message, setMessage] = useState("");
  const [reference, setReference] = useState("");
  const [tab, setTab] = useState(0);
  const [lesson, setLesson] = useState(0);
  const [completed, setCompleted] = useState<number[]>([]);
  const [slot, setSlot] = useState("0");
  const [booking, setBooking] = useState<number | null>(null);
  const activeStep =
    step === "intro" || step === "profile" ? 0 : step === "dashboard" ? 2 : 1;

  function navigate(next: Step) {
    setStep(next);
    setMessage("");
    requestAnimationFrame(() => {
      document.getElementById("demo-heading")?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "instant" });
    });
  }
  function restart() {
    setName(example[locale].name);
    setDraft({
      city: example[locale].city,
      stage: "0",
      idea: example[locale].idea,
      goals: example[locale].goals,
    });
    setConsent(false);
    setReference("");
    setCompleted([]);
    setBooking(null);
    setTab(0);
    setLesson(0);
    setSlot("0");
    navigate("intro");
  }
  const receipt = (
    <div className="demo-receipt">
      <CheckCircle2 size={36} aria-hidden="true" />
      <dl>
        <div>
          <dt>{t.receipt}</dt>
          <dd>{reference}</dd>
        </div>
        <div>
          <dt>{t.status}</dt>
          <dd>{t.submitted}</dd>
        </div>
      </dl>
      <p>{t.applicationNote}</p>
    </div>
  );

  return (
    <div className="demo-shell">
      <div className="demo-topline">
        <span className="demo-badge">
          <span />
          {t.badge}
        </span>
        {step !== "intro" && (
          <button className="demo-reset" onClick={restart}>
            <RotateCcw size={15} aria-hidden="true" />
            {t.reset}
          </button>
        )}
      </div>
      <p className="demo-notice">{t.notice}</p>
      {step !== "intro" && (
        <ol
          className="demo-stepper"
          aria-label={
            locale === "en" ? "Demo progress" : "செயல்விளக்க முன்னேற்றம்"
          }
        >
          {t.steps.map((label, index) => (
            <li
              key={label}
              aria-current={activeStep === index ? "step" : undefined}
              className={index <= activeStep ? "is-active" : ""}
            >
              <span>
                {index < activeStep ? (
                  <Check size={16} aria-hidden="true" />
                ) : (
                  index + 1
                )}
              </span>
              {label}
            </li>
          ))}
        </ol>
      )}
      {step === "intro" ? (
        <>
          <div className="demo-intro">
            <div>
              <p className="public-kicker">CSJE / EDP</p>
              <h1 id="demo-heading" tabIndex={-1}>
                {t.title}
              </h1>
              <p>{t.intro}</p>
              <button
                className="public-button public-button-primary"
                onClick={() => navigate("profile")}
              >
                {t.start}
                <ArrowRight size={18} aria-hidden="true" />
              </button>
            </div>
            <div className="demo-preview" aria-hidden="true">
              <span className="demo-preview-icon">
                <Sprout size={32} />
              </span>
              <strong>{t.program}</strong>
              <small>{t.sample}</small>
              <div className="demo-preview-row">
                <CheckCircle2 />
                {t.steps[0]}
              </div>
              <div className="demo-preview-row">
                <FileText />
                {t.steps[1]}
              </div>
              <div className="demo-preview-row">
                <BookOpen />
                {t.steps[2]}
              </div>
            </div>
          </div>
          <div className="demo-feature-grid">
            {t.featureTitles.map((title, index) => {
              const Icon = [Compass, FileText, BookOpen][index];
              return (
                <article key={title}>
                  <Icon size={25} aria-hidden="true" />
                  <h2>{title}</h2>
                  <p>{t.featureBodies[index]}</p>
                </article>
              );
            })}
          </div>
        </>
      ) : step === "profile" ? (
        <div className="demo-form-layout">
          <div>
            <p className="public-kicker">01 / {t.steps[0]}</p>
            <h1 id="demo-heading" tabIndex={-1}>
              {t.accountTitle}
            </h1>
            <p>{t.accountIntro}</p>
            <div className="demo-program-card">
              <Sprout size={25} aria-hidden="true" />
              <strong>{t.program}</strong>
              <span>{t.intake}</span>
              <small>{t.sample}</small>
            </div>
          </div>
          <form
            className="launch-form"
            onSubmit={(event) => {
              event.preventDefault();
              if (name.trim()) {
                navigate("application");
                setMessage(t.accountDone);
              }
            }}
          >
            <label>
              {t.name}
              <input
                required
                value={name}
                maxLength={80}
                onChange={(event) => setName(event.target.value)}
                autoComplete="off"
              />
            </label>
            <label>
              {t.email}
              <input
                value="ananya@example.com"
                readOnly
                type="email"
                tabIndex={0}
              />
            </label>
            <p className="launch-form-hint">{t.accountIntro}</p>
            <button
              type="submit"
              className="public-button public-button-primary"
            >
              {t.accountAction}
              <ArrowRight size={18} aria-hidden="true" />
            </button>
          </form>
        </div>
      ) : step === "application" ? (
        <div className="demo-form-layout">
          <div>
            <p className="public-kicker">02 / {t.steps[1]}</p>
            <h1 id="demo-heading" tabIndex={-1}>
              {t.applicationTitle}
            </h1>
            <p>{t.applicationIntro}</p>
            <div className="demo-program-card">
              <strong>{t.program}</strong>
              <span>{t.intake}</span>
              <small>{t.sample}</small>
            </div>
          </div>
          <form
            className="launch-form"
            onSubmit={(event) => {
              event.preventDefault();
              if (
                !draft.city.trim() ||
                !draft.idea.trim() ||
                !draft.goals.trim() ||
                !consent
              ) {
                setMessage(t.incomplete);
                return;
              }
              setReference(
                "DEMO-" + crypto.randomUUID().slice(0, 8).toUpperCase(),
              );
              navigate("receipt");
            }}
          >
            {message && (
              <p className="demo-status" role="status">
                {message}
              </p>
            )}
            <label>
              {t.city}
              <input
                required
                value={draft.city}
                maxLength={120}
                autoComplete="off"
                onChange={(event) =>
                  setDraft({ ...draft, city: event.target.value })
                }
              />
            </label>
            <label>
              {t.stage}
              <select
                value={draft.stage}
                onChange={(event) =>
                  setDraft({ ...draft, stage: event.target.value })
                }
              >
                {t.stages.map((label, index) => (
                  <option key={label} value={String(index)}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t.idea}
              <textarea
                required
                rows={4}
                maxLength={1200}
                value={draft.idea}
                onChange={(event) =>
                  setDraft({ ...draft, idea: event.target.value })
                }
              />
            </label>
            <label>
              {t.goals}
              <textarea
                required
                rows={3}
                maxLength={1200}
                value={draft.goals}
                onChange={(event) =>
                  setDraft({ ...draft, goals: event.target.value })
                }
              />
            </label>
            <label className="launch-checkbox">
              <input
                type="checkbox"
                required
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
              />
              <span>{t.consent}</span>
            </label>
            <div className="public-actions">
              <button
                type="button"
                className="public-button public-button-outline"
                onClick={() => setMessage(t.saved)}
              >
                {t.save}
              </button>
              <button
                type="submit"
                className="public-button public-button-primary"
              >
                {t.submit}
                <ArrowRight size={18} aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
      ) : step === "receipt" ? (
        <div className="demo-confirmation">
          <p className="public-kicker">02 / {t.steps[1]}</p>
          <h1 id="demo-heading" tabIndex={-1}>
            {t.receiptTitle}
          </h1>
          <p>{t.receiptIntro}</p>
          {receipt}
          <button
            className="public-button public-button-primary"
            onClick={() => navigate("dashboard")}
          >
            {t.next}
            <ArrowRight size={18} aria-hidden="true" />
          </button>
        </div>
      ) : (
        <div className="demo-dashboard">
          <div className="demo-dashboard-heading">
            <p className="public-kicker">
              {t.hello}, {name}
            </p>
            <h1 id="demo-heading" tabIndex={-1}>
              {t.dashboardTitle}
            </h1>
            <p>{t.dashboardIntro}</p>
          </div>
          <nav
            className="demo-tabs"
            aria-label={
              locale === "en" ? "Demo workspace" : "செயல்விளக்கப் பகுதி"
            }
          >
            {t.tabs.map((label, index) => (
              <button
                key={label}
                aria-pressed={tab === index}
                onClick={() => {
                  setTab(index);
                  setMessage("");
                }}
              >
                {label}
              </button>
            ))}
          </nav>
          {tab === 0 ? (
            <div className="demo-dashboard-grid">
              <article className="demo-panel">
                <BookOpen size={26} aria-hidden="true" />
                <h2>{t.learning}</h2>
                <p>
                  {t.progress}: {completed.length} / 3
                </p>
                <progress
                  value={completed.length}
                  max={3}
                  aria-label={t.progress}
                />
                <button className="public-text-link" onClick={() => setTab(1)}>
                  {t.continue}
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
              </article>
              <article className="demo-panel demo-panel-dark">
                <h2>{t.nextAction}</h2>
                <p>{t.nextActionBody}</p>
                <button
                  className="public-button public-button-light"
                  onClick={() => setTab(1)}
                >
                  {t.lessons[0]}
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
              </article>
              <article className="demo-panel">
                <Users size={26} aria-hidden="true" />
                <h2>{t.booking}</h2>
                <p>{booking === null ? t.mentoringIntro : t.slots[booking]}</p>
                <button className="public-text-link" onClick={() => setTab(2)}>
                  {t.mentoring}
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
              </article>
              <article className="demo-panel">
                <FileText size={26} aria-hidden="true" />
                <h2>{t.worksheet}</h2>
                <p>{t.worksheetBody}</p>
                <Link
                  className="public-text-link"
                  href={`/${locale}/tools/idea-planner`}
                >
                  {t.worksheet}
                  <ArrowRight size={18} aria-hidden="true" />
                </Link>
              </article>
            </div>
          ) : tab === 1 ? (
            <div className="demo-learning-layout">
              <div className="demo-lesson-list">
                {t.lessons.map((title, index) => (
                  <button
                    key={title}
                    aria-pressed={lesson === index}
                    onClick={() => setLesson(index)}
                  >
                    <span>
                      {completed.includes(index) ? (
                        <Check size={18} aria-label={t.completed} />
                      ) : (
                        String(index + 1).padStart(2, "0")
                      )}
                    </span>
                    {title}
                  </button>
                ))}
              </div>
              <article className="demo-panel">
                <p className="public-kicker">
                  {t.progress} · {lesson + 1} / 3
                </p>
                <h2>{t.lessons[lesson]}</h2>
                <p>{t.lessonBodies[lesson]}</p>
                <button
                  className="public-button public-button-primary"
                  disabled={completed.includes(lesson)}
                  onClick={() =>
                    setCompleted((current) => [...current, lesson])
                  }
                >
                  {completed.includes(lesson) ? t.completed : t.complete}
                  <Check size={17} aria-hidden="true" />
                </button>
              </article>
            </div>
          ) : tab === 2 ? (
            <div className="demo-form-layout">
              <div>
                <h2>{t.mentoring}</h2>
                <p>{t.mentoringIntro}</p>
              </div>
              <form
                className="launch-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  setBooking(Number(slot));
                  setMessage(t.booked);
                }}
              >
                <strong>{t.mentor}</strong>
                <p className="launch-form-hint">{t.format}</p>
                <label>
                  {t.booking}
                  <select
                    value={slot}
                    onChange={(event) => setSlot(event.target.value)}
                  >
                    {t.slots.map((label, index) => (
                      <option key={label} value={String(index)}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="public-button public-button-primary"
                  type="submit"
                >
                  {t.book}
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
                {message && (
                  <p className="demo-status" role="status">
                    {message}
                  </p>
                )}
              </form>
            </div>
          ) : (
            <div className="demo-application-summary">
              <h2>{t.review}</h2>
              {receipt}
              <dl>
                <div>
                  <dt>{t.name}</dt>
                  <dd>{name}</dd>
                </div>
                <div>
                  <dt>{t.city}</dt>
                  <dd>{draft.city}</dd>
                </div>
                <div>
                  <dt>{t.stage}</dt>
                  <dd>{t.stages[Number(draft.stage)]}</dd>
                </div>
                <div>
                  <dt>{t.idea}</dt>
                  <dd>{draft.idea}</dd>
                </div>
                <div>
                  <dt>{t.goals}</dt>
                  <dd>{draft.goals}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      )}
      <Link className="demo-back" href={`/${locale}`}>
        {t.back}
      </Link>
    </div>
  );
}
