"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  Compass,
  FilePenLine,
  Sprout,
} from "lucide-react";

type Stage = {
  title: string;
  short: string;
  tag: string;
  heading: string;
  body: string;
  items: readonly string[];
  action: string;
  path: string;
};
const icons = [Compass, FilePenLine, BookOpen, Sprout];

export function JourneyExplorer({
  locale,
  label,
  stages,
}: {
  locale: "en" | "ta";
  label: string;
  stages: readonly Stage[];
}) {
  const [active, setActive] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const stage = stages[active];
  const Icon = icons[active];

  function navigate(key: string) {
    let next = active;
    if (key === "ArrowDown" || key === "ArrowRight")
      next = (active + 1) % stages.length;
    else if (key === "ArrowUp" || key === "ArrowLeft")
      next = (active - 1 + stages.length) % stages.length;
    else if (key === "Home") next = 0;
    else if (key === "End") next = stages.length - 1;
    else return false;
    setActive(next);
    tabs.current[next]?.focus();
    return true;
  }

  return (
    <div className="journey-explorer">
      <div
        className="journey-tabs"
        role="tablist"
        aria-label={label}
        aria-orientation="vertical"
      >
        {stages.map((item, index) => (
          <button
            key={item.title}
            ref={(element) => {
              tabs.current[index] = element;
            }}
            type="button"
            role="tab"
            id={`journey-tab-${index}`}
            aria-controls="journey-panel"
            aria-selected={active === index}
            tabIndex={active === index ? 0 : -1}
            onClick={() => setActive(index)}
            onKeyDown={(event) => {
              if (navigate(event.key)) event.preventDefault();
            }}
          >
            <span className="journey-number" aria-hidden="true">
              0{index + 1}
            </span>
            <span>
              <strong>{item.title}</strong>
              <small>{item.short}</small>
            </span>
            <ArrowRight size={19} aria-hidden="true" />
          </button>
        ))}
      </div>
      <div
        id="journey-panel"
        className="journey-panel"
        role="tabpanel"
        aria-labelledby={`journey-tab-${active}`}
        tabIndex={0}
      >
        <div className="journey-panel-top">
          <span>{stage.tag}</span>
          <span aria-hidden="true">
            0{active + 1} / 0{stages.length}
          </span>
        </div>
        <div className="journey-symbol" aria-hidden="true">
          <Icon size={36} strokeWidth={1.4} />
        </div>
        <h3>{stage.heading}</h3>
        <p>{stage.body}</p>
        <ul>
          {stage.items.map((item) => (
            <li key={item}>
              <Check size={17} aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
        <Link
          className="public-button public-button-light"
          href={`/${locale}${stage.path}`}
        >
          {stage.action}
          <ArrowRight size={18} aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}
