"use client";
import { useState } from "react";
import { Download, RotateCcw } from "lucide-react";
import type { Locale } from "../lib/messages";

const copy = {
  en: {
    labels: [
      "What is your idea?",
      "Who would it help?",
      "What problem does it solve?",
      "How do people handle this today?",
      "What is one small test you could try?",
      "What is your next action?",
    ],
    hints: [
      "Describe it in one or two sentences.",
      "Be specific about the people you want to help.",
      "Describe the need in the customer’s own words.",
      "Think about existing solutions and workarounds.",
      "Choose one assumption and a way to learn about it.",
      "Write something you can do, and when you will do it.",
    ],
    download: "Download your plan",
    reset: "Clear answers",
    confirm: "Clear all your answers?",
    privacy:
      "Your answers stay in this tab. Nothing is sent to the server or saved automatically. Download your plan before refreshing or leaving.",
    empty: "Add an answer to start your plan.",
    downloaded: "Your plan is ready to download.",
    title: "My idea plan",
    count: "questions answered",
  },
  ta: {
    labels: [
      "உங்கள் யோசனை என்ன?",
      "யாருக்கு உதவும்?",
      "எந்தப் பிரச்சினையைத் தீர்க்கிறது?",
      "இப்போது மக்கள் அதை எப்படிச் சமாளிக்கிறார்கள்?",
      "முயலக்கூடிய சிறிய சோதனை என்ன?",
      "உங்கள் அடுத்த நடவடிக்கை என்ன?",
    ],
    hints: [
      "ஒன்று அல்லது இரண்டு வாக்கியங்களில் எழுதுங்கள்.",
      "உதவ விரும்பும் மக்களைக் குறிப்பாக விவரியுங்கள்.",
      "வாடிக்கையாளரின் சொற்களில் தேவையை விளக்குங்கள்.",
      "இப்போதைய தீர்வுகளையும் மாற்று வழிகளையும் சிந்தியுங்கள்.",
      "ஒரு ஊகத்தையும் அதைப் பற்றிக் கற்கும் வழியையும் தேர்ந்தெடுங்கள்.",
      "செய்யக்கூடிய ஒன்றையும் அதைச் செய்யும் நேரத்தையும் எழுதுங்கள்.",
    ],
    download: "திட்டத்தைப் பதிவிறக்கவும்",
    reset: "பதில்களை அழிக்கவும்",
    confirm: "அனைத்துப் பதில்களையும் அழிக்கவா?",
    privacy:
      "பதில்கள் இந்தத் தாவலில் இருக்கும். சேவையகத்துக்கு அனுப்பப்படாது; தானாகச் சேமிக்கப்படாது. பக்கத்தைப் புதுப்பிக்கும் முன் அல்லது வெளியேறும் முன் திட்டத்தைப் பதிவிறக்குங்கள்.",
    empty: "திட்டத்தைத் தொடங்க ஒரு பதில் எழுதுங்கள்.",
    downloaded: "திட்டம் பதிவிறக்கத் தயாராக உள்ளது.",
    title: "என் யோசனைத் திட்டம்",
    count: "கேள்விகளுக்குப் பதில்",
  },
};

export function IdeaPlanner({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const [answers, setAnswers] = useState<string[]>(Array(6).fill(""));
  const [message, setMessage] = useState("");
  const completed = answers.filter((answer) => answer.trim()).length;
  function download() {
    if (!completed) {
      setMessage(t.empty);
      return;
    }
    const body =
      t.title +
      "\n\n" +
      t.labels
        .map(
          (label, index) =>
            `${index + 1}. ${label}\n${answers[index].trim()}\n`,
        )
        .join("\n");
    const url = URL.createObjectURL(
      new Blob(["\uFEFF" + body], { type: "text/plain;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `csje-idea-plan-${locale}.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMessage(t.downloaded);
  }
  return (
    <section className="planner-workspace">
      <p className="planner-privacy">{t.privacy}</p>
      <div className="planner-progress">
        <span>
          {completed} / 6 {t.count}
        </span>
        <progress value={completed} max={6} aria-label={t.count} />
      </div>
      <form
        className="planner-grid"
        onSubmit={(event) => {
          event.preventDefault();
          download();
        }}
      >
        {t.labels.map((label, index) => (
          <label key={label}>
            <span className="planner-number">0{index + 1}</span>
            <strong>{label}</strong>
            <small id={`planner-hint-${index}`}>{t.hints[index]}</small>
            <textarea
              rows={4}
              maxLength={2000}
              value={answers[index]}
              aria-describedby={`planner-hint-${index}`}
              onChange={(event) =>
                setAnswers((current) =>
                  current.map((answer, position) =>
                    position === index ? event.target.value : answer,
                  ),
                )
              }
            />
          </label>
        ))}
        <div className="planner-actions">
          <button className="public-button public-button-primary" type="submit">
            <Download size={18} aria-hidden="true" />
            {t.download}
          </button>
          <button
            className="public-button public-button-outline"
            type="button"
            onClick={() => {
              if (completed && window.confirm(t.confirm)) {
                setAnswers(Array(6).fill(""));
                setMessage("");
              }
            }}
          >
            <RotateCcw size={17} aria-hidden="true" />
            {t.reset}
          </button>
          <p role="status">{message}</p>
        </div>
      </form>
    </section>
  );
}
