"use client";

import { useEffect, useState } from "react";
import { Archive, Eye, FilePlus2, FileText, History, Languages, RotateCcw, Save, Send } from "lucide-react";
import { Button } from "../../../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import type { components } from "../../../../lib/api-contracts";
import { cmsMessages } from "../../../../lib/cms-messages";

type Page = components["schemas"]["PageView"];
type Draft = Pick<components["schemas"]["Edit"], "title" | "body" | "seo_title" | "seo_description">;
const empty: Draft = { title: "", body: "", seo_title: "", seo_description: "" };
const copy = {
  en: {
    library: "Page library", libraryHelp: "Select a page to edit its content.",
    emptyHelp: "Create a page to get started.", editing: "Page editor", create: "Create a new page",
    editingHelp: "Edit the content for the selected language.", createHelp: "Add the first draft of your page.",
    newBadge: "New page", addressHelp: "Use lowercase letters, numbers and hyphens. The address cannot be changed after creation.",
    details: "Page content", detailsHelp: "This is the content your visitors will read.",
    search: "Search appearance", searchHelp: "Optional information for search engines.",
    publishing: "Publishing", publishingHelp: "Preview and publish the last saved draft.",
    archiveHelp: "Archive removes this language from public view. Add a reason to continue.",
    confirmLeave: "You have unsaved changes. Discard them and continue?",
    unsaved: "Unsaved changes", savedVersion: "Saved version", noTranslation: "No saved translation yet",
    pageActions: "Page actions", archivedHelp: "Restore this translation to a draft before editing.",
    historyEmpty: "No published revisions yet.", refresh: "Refresh", saveFirst: "Save your changes before publishing or archiving.",
  },
  ta: {
    library: "பக்கங்கள்", libraryHelp: "திருத்த ஒரு பக்கத்தைத் தேர்ந்தெடுக்கவும்.",
    emptyHelp: "தொடங்க ஒரு பக்கத்தை உருவாக்கவும்.", editing: "பக்கத் திருத்தி", create: "புதிய பக்கத்தை உருவாக்கவும்",
    editingHelp: "தேர்ந்தெடுத்த மொழியின் உள்ளடக்கத்தைத் திருத்தவும்.", createHelp: "பக்கத்தின் முதல் வரைவைச் சேர்க்கவும்.",
    newBadge: "புதிய பக்கம்", addressHelp: "சிறிய எழுத்துகள், எண்கள் மற்றும் இணைப்புக்குறிகளைப் பயன்படுத்தவும். உருவாக்கிய பின் முகவரியை மாற்ற முடியாது.",
    details: "பக்க உள்ளடக்கம்", detailsHelp: "இந்த உள்ளடக்கத்தைப் பார்வையாளர்கள் படிப்பார்கள்.",
    search: "தேடல் தோற்றம்", searchHelp: "தேடுபொறிகளுக்கான விருப்பத் தகவல்.",
    publishing: "வெளியிடுதல்", publishingHelp: "கடைசியாகச் சேமித்த வரைவை முன்னோட்டமிட்டு வெளியிடவும்.",
    archiveHelp: "காப்பகப்படுத்தினால் இந்த மொழி பொதுப் பார்வையிலிருந்து நீக்கப்படும். தொடர ஒரு காரணத்தைச் சேர்க்கவும்.",
    confirmLeave: "சேமிக்காத மாற்றங்கள் உள்ளன. அவற்றைக் கைவிட்டு தொடரவா?",
    unsaved: "சேமிக்காத மாற்றங்கள்", savedVersion: "சேமித்த பதிப்பு", noTranslation: "சேமித்த மொழிபெயர்ப்பு இல்லை",
    pageActions: "பக்கச் செயல்கள்", archivedHelp: "திருத்துவதற்கு முன் இந்த மொழிபெயர்ப்பை வரைவாக மீட்டமைக்கவும்.",
    historyEmpty: "வெளியிடப்பட்ட பதிப்புகள் இன்னும் இல்லை.", refresh: "புதுப்பிக்கவும்", saveFirst: "வெளியிடுவதற்கு அல்லது காப்பகப்படுத்துவதற்கு முன் மாற்றங்களைச் சேமிக்கவும்.",
  },
} as const;

export default function Editor({ org, permissions, locale }: { org: string; permissions: string[]; locale: "en" | "ta" }) {
  const t = cmsMessages[locale], c = copy[locale], base = `/api/cms/organizations/${org}/pages`;
  const [items, setItems] = useState<Page[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Page | null>(null);
  const [language, setLanguage] = useState<"en" | "ta">(locale);
  const [form, setForm] = useState<Draft>(empty);
  const [slug, setSlug] = useState("");
  const [busy, setBusy] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [listFailed, setListFailed] = useState(false);
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState<Draft | null>(null);
  const [history, setHistory] = useState<components["schemas"]["History"] | null>(null);
  const current = selected?.translations.find((x) => x.locale === language);
  const allowed = (action: string) => permissions.includes("cms.page." + action);
  const initial = current ?? empty;
  const dirty = slug !== (selected?.slug ?? "") ||
    (["title", "body", "seo_title", "seo_description"] as const).some((key) => (form[key] ?? "") !== (initial[key] ?? ""));

  async function api(path: string, method = "GET", data?: unknown) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const r = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!r.ok) throw new Error(t.error);
      headers["x-csrf-token"] = (await r.json()).csrf_token;
    }
    const response = await fetch(path, { method, headers, body: data ? JSON.stringify(data) : undefined, cache: "no-store" });
    if (!response.ok) throw new Error(response.status === 409 ? t.conflict : t.error);
    return response.json();
  }
  useEffect(() => {
    let active = true;
    fetch(base, { cache: "no-store" }).then(async (r) => {
      if (!r.ok) throw new Error();
      return r.json();
    }).then((data) => {
      if (active) { setItems(data.items); setCursor(data.next_cursor); }
    }).catch(() => { if (active) { setListFailed(true); setMessage(t.error); } })
      .finally(() => { if (active) setInitialLoading(false); });
    return () => { active = false; };
  }, [base, t.error]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  async function run(work: () => Promise<void>) {
    setBusy(true); setMessage("");
    try { await work(); } catch (e) { setMessage(e instanceof Error ? e.message : t.error); }
    finally { setBusy(false); }
  }
  function choose(page: Page | null, lang = language) {
    setSelected(page); setLanguage(lang);
    const value = page?.translations.find((x) => x.locale === lang);
    setForm(value ?? empty); setSlug(page?.slug ?? "");
    setPreview(null); setHistory(null); setReason(""); setMessage("");
  }
  function canLeave() { return !dirty || window.confirm(c.confirmLeave); }
  function saved(page: Page) {
    choose(page); setItems((old) => [page, ...old.filter((x) => x.id !== page.id)]); setMessage(t.saved);
  }
  const path = selected ? `${base}/${selected.id}/translations/${language}` : "";
  async function load(more = false) {
    const data = await api(base + (more && cursor ? `?cursor=${cursor}` : ""));
    setItems((old) => more ? [...old, ...data.items] : data.items);
    setCursor(data.next_cursor); setListFailed(false);
  }
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(async () => {
      const data = !selected
        ? await api(base, "POST", { ...form, slug, locale: language })
        : !current
          ? await api(`${base}/${selected.id}/translations`, "POST", { ...form, locale: language })
          : await api(path, "PATCH", { title: form.title, body: form.body, seo_title: form.seo_title, seo_description: form.seo_description, expected_version: current.version });
      saved(data);
    });
  }

  return <div className="cms-workspace" aria-busy={busy || initialLoading}>
    <div className="cms-grid cms-editor-layout">
      <aside className="cms-library" aria-label={c.library}>
        <div className="cms-library-top">
          <div><h2>{c.library}</h2><p>{c.libraryHelp}</p></div>
          <Button type="button" size="sm" disabled={busy || !allowed("create")} onClick={() => { if (canLeave()) choose(null); }}>
            <FilePlus2 aria-hidden="true" />{t.newPage}
          </Button>
        </div>
        {initialLoading ? <p role="status" className="cms-library-empty">{t.loading}…</p>
          : listFailed ? <div className="cms-library-empty">{t.error}</div>
          : items.length === 0 ? <div className="cms-library-empty"><FileText aria-hidden="true" /><strong>{t.empty}</strong><span>{allowed("create") ? c.emptyHelp : t.unavailable}</span></div>
          : <ul className="cms-page-list">{items.map((page) => {
            const translation = page.translations.find((item) => item.locale === language) ?? page.translations[0];
            return <li key={page.id}><button type="button" disabled={busy} aria-pressed={page.id === selected?.id}
              onClick={() => { if (canLeave()) void run(async () => choose(await api(`${base}/${page.id}`))); }}>
              <FileText aria-hidden="true" /><span><strong>{translation?.title || page.slug}</strong><small>/{page.slug}</small></span>
            </button></li>;
          })}</ul>}
        <div className="cms-library-actions">
          {cursor && <Button type="button" variant="outline" disabled={busy} onClick={() => void run(() => load(true))}>{t.more}</Button>}
          <Button type="button" variant="ghost" disabled={busy} onClick={() => void run(() => load())}><RotateCcw aria-hidden="true" />{listFailed ? t.retry : c.refresh}</Button>
        </div>
      </aside>
      <section className="cms-editor" aria-label={c.editing}>
        <div className="cms-editor-heading">
          <div><p className="cms-editor-kicker">{selected ? c.editing : c.newBadge}</p><h2>{selected ? (current?.title || selected.slug) : c.create}</h2><p>{selected ? c.editingHelp : c.createHelp}</p></div>
          <label className="cms-language"><span><Languages size={16} aria-hidden="true" />{t.locale}</span>
            <select value={language} disabled={busy} onChange={(e) => { if (canLeave()) choose(selected, e.target.value as "en" | "ta"); }}>
              <option value="en">English</option><option value="ta">Tamil</option>
            </select>
          </label>
        </div>
        <div className="cms-editor-meta">
          {current ? <span className={`cms-state cms-state-${current.state}`}>{t[current.state]} <span>· v{current.version}</span></span>
            : <span className="cms-state cms-state-new">{selected ? c.noTranslation : c.newBadge}</span>}
          {dirty && <span className="cms-unsaved">{c.unsaved}</span>}
        </div>
        {(busy || message) && <p role="status" className="cms-feedback">{busy ? t.loading + "…" : message}</p>}
        {current?.state === "archived" && <p className="cms-archive-notice">{c.archivedHelp}</p>}
        <form className="cms-editor-form" onSubmit={submit}>
          <fieldset disabled={busy || current?.state === "archived" || !allowed(selected ? "update" : "create")}>
            <Card className="cms-content-card">
              <CardHeader><CardTitle role="heading" aria-level={3}>{c.details}</CardTitle><CardDescription>{c.detailsHelp}</CardDescription></CardHeader>
              <CardContent className="cms-fields">
                <div className="cms-address-field"><label htmlFor="cms-address"><span>{t.slug}</span></label><Input id="cms-address" required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxLength={120} value={slug} disabled={!!selected} onChange={(e) => setSlug(e.target.value)} aria-describedby="cms-address-help" /><small id="cms-address-help">{c.addressHelp}</small></div>
                <label><span>{t.title}</span><Input required maxLength={200} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
                <label><span>{t.body}</span><Textarea aria-label={t.body} required rows={12} maxLength={50000} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></label>
              </CardContent>
            </Card>
            <Card className="cms-content-card cms-search-card">
              <CardHeader><CardTitle role="heading" aria-level={3}>{c.search}</CardTitle><CardDescription>{c.searchHelp}</CardDescription></CardHeader>
              <CardContent className="cms-fields">
                <label><span>{t.seo_title}</span><Input maxLength={70} value={form.seo_title ?? ""} onChange={(e) => setForm({ ...form, seo_title: e.target.value })} /></label>
                <label><span>{t.seo_description}</span><Input maxLength={200} value={form.seo_description ?? ""} onChange={(e) => setForm({ ...form, seo_description: e.target.value })} /></label>
              </CardContent>
            </Card>
            <div className="cms-save-bar"><p>{t.note}</p><Button type="submit"><Save aria-hidden="true" />{selected && !current ? t.addLocale : t.save}</Button></div>
          </fieldset>
        </form>
        {current && <Card className="cms-content-card cms-publish-card">
          <CardHeader><CardTitle role="heading" aria-level={3}>{c.publishing}</CardTitle><CardDescription>{c.publishingHelp}</CardDescription></CardHeader>
          <CardContent>
            {dirty && <p className="cms-publish-warning">{c.saveFirst}</p>}
            <div className="cms-publish-actions" aria-label={c.pageActions}>
              <Button type="button" variant="outline" className="cms-secondary" disabled={busy} onClick={() => void run(async () => { const page: Page = await api(path + "/preview"); setPreview(page.translations.find((x) => x.locale === language) ?? null); })}><Eye aria-hidden="true" />{t.preview}</Button>
              <Button type="button" variant="outline" className="cms-secondary" disabled={busy} onClick={() => void run(async () => setHistory(await api(path + "/revisions")))}><History aria-hidden="true" />{t.history}</Button>
              {current.state === "archived"
                ? <Button type="button" disabled={busy || dirty || !allowed("update")} onClick={() => void run(async () => saved(await api(path + "/restore", "POST", { expected_version: current.version })))}><RotateCcw aria-hidden="true" />{t.restore}</Button>
                : <Button type="button" disabled={busy || dirty || !allowed("publish")} onClick={() => void run(async () => saved(await api(path + "/publish", "POST", { expected_version: current.version })))}><Send aria-hidden="true" />{t.publish}</Button>}
            </div>
            {current.state !== "archived" && allowed("archive") && <details className="cms-archive">
              <summary><Archive size={16} aria-hidden="true" />{t.archive}</summary>
              <p>{c.archiveHelp}</p><div className="cms-archive-controls"><label>{t.reason}<Input maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
              <Button type="button" variant="destructive" disabled={busy || dirty || !reason.trim()} onClick={() => void run(async () => saved(await api(path + "/archive", "POST", { expected_version: current.version, reason })))}>{t.archive}</Button></div>
            </details>}
          </CardContent>
        </Card>}
        {preview && <article className="cms-preview"><div className="cms-result-heading"><div><p className="cms-editor-kicker">{t.preview}</p><h2>{preview.title}</h2></div><Button type="button" variant="ghost" onClick={() => setPreview(null)}>{t.close}</Button></div><div className="cms-body">{preview.body}</div></article>}
        {history && <section className="cms-history"><div className="cms-result-heading"><h2>{t.history}</h2><Button type="button" variant="ghost" onClick={() => setHistory(null)}>{t.close}</Button></div>
          {history.items.length === 0 && <p>{c.historyEmpty}</p>}
          {history.items.map((item) => <article key={item.revision_id}><time>{item.published_at}</time><h3>{item.title}</h3><div className="cms-body">{item.body}</div></article>)}
          {history.next_cursor && <Button type="button" variant="outline" disabled={busy} onClick={() => void run(async () => { const next = await api(path + "/revisions?cursor=" + history.next_cursor); setHistory({ items: [...history.items, ...next.items], next_cursor: next.next_cursor }); })}>{t.more}</Button>}
        </section>}
      </section>
    </div>
  </div>;
}
