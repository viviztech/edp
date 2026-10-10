"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type MenuId = "program" | "support" | "updates";
type Item = { title: string; href: string };
type Props = {
  locale: "en" | "ta";
  navigationLabel: string;
  labels: {
    home: string; program: string; support: string; updates: string;
    contact: string; apply: string; account: string; language: string;
    news: string; events: string; faq: string;
  };
  program: Item[];
  support: Item[];
};

export function PublicNavigation({ locale, navigationLabel, labels, program, support }: Props) {
  const [openMenu, setOpenMenu] = useState<MenuId | null>(null);
  const lastPointerType = useRef<string | null>(null);
  const updates: Item[] = [
    { title: labels.news, href: "/" + locale + "/content/news" },
    { title: labels.events, href: "/" + locale + "/content/event" },
    { title: labels.faq, href: "/" + locale + "/content/faq" },
  ];

  function menu(id: MenuId, title: string, items: Item[]) {
    const expanded = openMenu === id;
    return <div
      className="site-nav-group"
      key={id}
      onMouseEnter={() => {
        if (lastPointerType.current !== "touch") setOpenMenu(id);
      }}
      onMouseLeave={() => setOpenMenu(null)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpenMenu(null);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          setOpenMenu(null);
          (event.currentTarget.querySelector("button") as HTMLButtonElement | null)?.focus();
        }
      }}
    >
      <button
        id={"nav-trigger-" + id}
        type="button"
        className="site-nav-trigger"
        aria-expanded={expanded}
        aria-controls={"nav-panel-" + id}
        onPointerDown={(event) => { lastPointerType.current = event.pointerType; }}
        onTouchStart={() => { lastPointerType.current = "touch"; }}
        onClick={(event) => {
          if (event.detail === 0 || lastPointerType.current === "touch") {
            setOpenMenu((current) => current === id ? null : id);
          } else {
            setOpenMenu(id);
          }
          lastPointerType.current = null;
        }}
      >{title}</button>
      <div
        id={"nav-panel-" + id}
        className="site-nav-panel"
        aria-labelledby={"nav-trigger-" + id}
        hidden={!expanded}
      >
        {items.map((item) => <Link key={item.href} href={item.href} onClick={() => setOpenMenu(null)}>{item.title}</Link>)}
      </div>
    </div>;
  }

  return <nav className="site-nav" aria-label={navigationLabel}>
    <Link href={"/" + locale}>{labels.home}</Link>
    {menu("program", labels.program, program)}
    {menu("support", labels.support, support)}
    {menu("updates", labels.updates, updates)}
    <Link href={"/" + locale + "/pages/contact"}>{labels.contact}</Link>
    <Link href={"/" + locale + "/pages/apply"}>{labels.apply}</Link>
    <Link className="site-account" href={"/" + locale + "/account"}>{labels.account}</Link>
    <Link className="site-language" href={"/" + (locale === "en" ? "ta" : "en")} lang={locale === "en" ? "ta" : "en"}>{labels.language}</Link>
  </nav>;
}
