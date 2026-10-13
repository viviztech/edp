"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useState } from "react";
import { ArrowUpRight, ChevronDown, Menu, X } from "lucide-react";

type MenuId = "program" | "support" | "updates";
type Item = { title: string; href: string };
type Props = {
  locale: "en" | "ta";
  navigationLabel: string;
  labels: {
    home: string;
    program: string;
    support: string;
    updates: string;
    contact: string;
    apply: string;
    account: string;
    language: string;
    news: string;
    events: string;
    faq: string;
  };
  program: Item[];
  support: Item[];
};

export function PublicNavigation({
  locale,
  navigationLabel,
  labels,
  program,
  support,
}: Props) {
  const [openMenu, setOpenMenu] = useState<MenuId | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileTrigger = useRef<HTMLButtonElement | null>(null);
  const pathname = usePathname() || "/" + locale;
  const otherLocale = locale === "en" ? "ta" : "en";
  const languagePath = pathname.replace(
    /^\/(en|ta)(?=\/|$)/,
    "/" + otherLocale,
  );
  const lastPointerType = useRef<string | null>(null);
  const updates: Item[] = [
    { title: labels.news, href: "/" + locale + "/content/news" },
    { title: labels.events, href: "/" + locale + "/content/event" },
    { title: labels.faq, href: "/" + locale + "/content/faq" },
  ];

  function closeNavigation() {
    setOpenMenu(null);
    setMobileOpen(false);
  }

  function menu(id: MenuId, title: string, items: Item[]) {
    const expanded = openMenu === id;
    return (
      <div
        className="site-nav-group"
        key={id}
        onMouseEnter={() => {
          if (lastPointerType.current !== "touch") setOpenMenu(id);
        }}
        onMouseLeave={() => setOpenMenu(null)}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget))
            setOpenMenu(null);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpenMenu(null);
            (
              event.currentTarget.querySelector(
                "button",
              ) as HTMLButtonElement | null
            )?.focus();
          }
        }}
      >
        <button
          id={"nav-trigger-" + id}
          type="button"
          className="site-nav-trigger"
          aria-expanded={expanded}
          aria-controls={"nav-panel-" + id}
          onPointerDown={(event) => {
            lastPointerType.current = event.pointerType;
          }}
          onTouchStart={() => {
            lastPointerType.current = "touch";
          }}
          onClick={(event) => {
            if (event.detail === 0 || lastPointerType.current === "touch") {
              setOpenMenu((current) => (current === id ? null : id));
            } else {
              setOpenMenu(id);
            }
            lastPointerType.current = null;
          }}
        >
          {title}
          <ChevronDown size={13} aria-hidden="true" />
        </button>
        <div
          id={"nav-panel-" + id}
          className="site-nav-panel"
          aria-labelledby={"nav-trigger-" + id}
          hidden={!expanded}
        >
          <p className="site-nav-panel-label">{title}</p>
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={closeNavigation}
              aria-current={pathname === item.href ? "page" : undefined}
            >
              <span>{item.title}</span>
              <ArrowUpRight size={15} aria-hidden="true" />
            </Link>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="site-navigation"
      onKeyDown={(event) => {
        if (event.key === "Escape" && mobileOpen) {
          closeNavigation();
          mobileTrigger.current?.focus();
        }
      }}
    >
      <button
        ref={mobileTrigger}
        className="site-menu-toggle"
        type="button"
        aria-expanded={mobileOpen}
        aria-controls="public-navigation"
        onClick={() => {
          setMobileOpen((open) => !open);
          setOpenMenu(null);
        }}
      >
        <span>{locale === "en" ? "Menu" : "மெனு"}</span>
        {mobileOpen ? (
          <X size={20} aria-hidden="true" />
        ) : (
          <Menu size={20} aria-hidden="true" />
        )}
      </button>
      <nav
        id="public-navigation"
        className={"site-nav" + (mobileOpen ? " is-mobile-open" : "")}
        aria-label={navigationLabel}
      >
        <div className="site-nav-links">
          <Link
            href={"/" + locale}
            aria-current={pathname === "/" + locale ? "page" : undefined}
            onClick={closeNavigation}
          >
            {labels.home}
          </Link>
          {menu("program", labels.program, program)}
          {menu("support", labels.support, support)}
          {menu("updates", labels.updates, updates)}
          <Link
            href={"/" + locale + "/pages/contact"}
            onClick={closeNavigation}
          >
            {labels.contact}
          </Link>
        </div>
        <div className="site-nav-actions">
          <Link
            className="site-language"
            href={languagePath}
            lang={otherLocale}
            aria-label={labels.language}
            onClick={closeNavigation}
          >
            {locale === "en" ? "தமிழ்" : "EN"}
          </Link>
          <Link
            className="site-apply"
            href={"/" + locale + "/pages/apply"}
            onClick={closeNavigation}
          >
            {labels.apply}
          </Link>
          <Link
            className="site-account"
            href={"/" + locale + "/account"}
            onClick={closeNavigation}
          >
            {labels.account}
            <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </nav>
    </div>
  );
}
