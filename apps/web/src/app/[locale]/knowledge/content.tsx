import type { components } from "../../../lib/api-contracts";

export type Resource = components["schemas"]["KnowledgeView"];
export type Mine = components["schemas"]["KnowledgeMine"];
export type FundingCase = components["schemas"]["FundingCaseView"];
export type Locale = "en" | "ta";
export const words = {
  en: {
    title: "Schemes, funding and opportunities", intro: "Explore verified sources and prepare your next step.",
    search: "Search resources", kind: "Resource kind", all: "All", scheme: "Scheme", funding: "Funding", opportunity: "Opportunity",
    sector: "Sector", geography: "Geography", tag: "Tag", availability: "Availability", active: "Open and upcoming",
    open: "Open", upcoming: "Upcoming", closed: "Closed", filter: "Apply filters", more: "Load more", empty: "No matching resources.",
    loading: "Loading resources…", error: "Could not load or save. Your entered text is preserved. Please retry.",
    conflict: "The saved version changed. Refresh the saved data and review it before trying again. Your entered text is preserved.",
    access: "Participant access is unavailable. An active enrollment is required.", retry: "Refresh resources",
    source: "Official source", verified: "Last verified", opens: "Opens", closes: "Closes", unspecified: "Not specified",
    provider: "Provider", type: "Type", description: "Description", eligibility: "Eligibility", benefits: "Benefits",
    process: "Application process", documents: "Required documents", contact: "Contact or reference", amount: "Official funding amount",
    save: "Save resource", unsave: "Remove saved resource", saved: "Saved resources", unavailable: "This saved resource is no longer available.",
    interest: "Express interest", interested: "Interest recorded", interests: "My opportunity interests", start: "Start funding tracker",
    cases: "My funding tracker", reported: "Progress is self-reported external activity. Confirm eligibility and decisions with the official provider.",
    status: "Status", next: "Next status", reason: "Reason for change", progress: "Record progress", history: "Progress history",
    original: "Source recorded when tracking began", done: "Saved.", noSaved: "No saved resources yet.", noCases: "No funding cases yet.",
    noInterest: "No opportunity interests yet.", interestedStatus: "Interested", eligibility_check: "Eligibility check",
    document_preparation: "Document preparation", applied: "Applied", under_review: "Under review", approved: "Approved",
    rejected: "Rejected", disbursed: "Disbursed", account: "Sign in to save resources", terminal: "This case has reached its final status.",
    refreshProgress: "Refresh funding tracker", refreshed: "Latest saved data loaded. Review it and your entered text before saving.", filters: "Resource filters",
  },
  ta: {
    title: "திட்டங்கள், நிதி மற்றும் வாய்ப்புகள்", intro: "சரிபார்க்கப்பட்ட ஆதாரங்களைப் பார்த்து அடுத்த படிக்குத் தயாராகுங்கள்.",
    search: "வளங்களைத் தேடு", kind: "வள வகை", all: "அனைத்தும்", scheme: "திட்டம்", funding: "நிதி", opportunity: "வாய்ப்பு",
    sector: "துறை", geography: "பகுதி", tag: "குறிச்சொல்", availability: "கிடைக்கும் நிலை", active: "திறந்த மற்றும் வரவிருக்கும்",
    open: "திறந்துள்ளது", upcoming: "வரவிருக்கிறது", closed: "முடிந்தது", filter: "வடிகட்டிகளைப் பயன்படுத்து", more: "மேலும் ஏற்று", empty: "பொருந்தும் வளங்கள் இல்லை.",
    loading: "வளங்கள் ஏற்றப்படுகின்றன…", error: "ஏற்ற அல்லது சேமிக்க முடியவில்லை. உள்ளிட்ட உரை பாதுகாக்கப்பட்டுள்ளது. மீண்டும் முயற்சிக்கவும்.",
    conflict: "சேமித்த பதிப்பு மாறிவிட்டது. மீண்டும் முயல்வதற்கு முன் சேமித்த தரவைப் புதுப்பித்துப் பார்க்கவும். உள்ளிட்ட உரை பாதுகாக்கப்பட்டுள்ளது.",
    access: "பங்கேற்பாளர் அணுகல் இல்லை. செயலில் உள்ள சேர்க்கை தேவை.", retry: "வளங்களைப் புதுப்பி",
    source: "அதிகாரப்பூர்வ ஆதாரம்", verified: "கடைசியாகச் சரிபார்த்த தேதி", opens: "தொடங்கும் தேதி", closes: "முடியும் தேதி", unspecified: "குறிப்பிடப்படவில்லை",
    provider: "வழங்குநர்", type: "வகை", description: "விளக்கம்", eligibility: "தகுதி", benefits: "பயன்கள்",
    process: "விண்ணப்ப முறை", documents: "தேவையான ஆவணங்கள்", contact: "தொடர்பு அல்லது குறிப்பு", amount: "அதிகாரப்பூர்வ நிதித் தொகை",
    save: "வளத்தைச் சேமி", unsave: "சேமித்த வளத்தை அகற்று", saved: "சேமித்த வளங்கள்", unavailable: "இந்தச் சேமித்த வளம் தற்போது கிடைக்கவில்லை.",
    interest: "ஆர்வத்தைப் பதிவு செய்", interested: "ஆர்வம் பதிவானது", interests: "எனது வாய்ப்பு ஆர்வங்கள்", start: "நிதி முன்னேற்றத்தைத் தொடங்கு",
    cases: "எனது நிதி முன்னேற்றம்", reported: "இது பங்கேற்பாளர் தெரிவிக்கும் வெளிப்புற நடவடிக்கை. தகுதியையும் முடிவுகளையும் அதிகாரப்பூர்வ வழங்குநரிடம் உறுதிப்படுத்தவும்.",
    status: "நிலை", next: "அடுத்த நிலை", reason: "மாற்றத்திற்கான காரணம்", progress: "முன்னேற்றத்தைப் பதிவு செய்", history: "முன்னேற்ற வரலாறு",
    original: "பதிவு தொடங்கியபோது இருந்த ஆதாரம்", done: "சேமிக்கப்பட்டது.", noSaved: "சேமித்த வளங்கள் இல்லை.", noCases: "நிதிப் பதிவுகள் இல்லை.",
    noInterest: "வாய்ப்பு ஆர்வங்கள் இல்லை.", interestedStatus: "ஆர்வம்", eligibility_check: "தகுதி சரிபார்ப்பு",
    document_preparation: "ஆவணத் தயாரிப்பு", applied: "விண்ணப்பித்தது", under_review: "பரிசீலனையில்", approved: "ஒப்புதல்",
    rejected: "நிராகரிப்பு", disbursed: "நிதி வழங்கப்பட்டது", account: "வளங்களைச் சேமிக்க உள்நுழையுங்கள்", terminal: "இந்தப் பதிவு இறுதி நிலையை அடைந்துள்ளது.",
    refreshProgress: "நிதி முன்னேற்றத்தைப் புதுப்பி", refreshed: "அண்மையில் சேமித்த தரவு ஏற்றப்பட்டது. சேமிக்கும் முன் அதையும் உள்ளிட்ட உரையையும் பார்க்கவும்.", filters: "வள வடிகட்டிகள்",
  },
} as const;

export function statusLabel(status: FundingCase["status"], locale: Locale) {
  return status === "interested" ? words[locale].interestedStatus : words[locale][status];
}
export const nextStatuses: Record<FundingCase["status"], FundingCase["status"][]> = {
  interested: ["eligibility_check"], eligibility_check: ["document_preparation"], document_preparation: ["applied"],
  applied: ["under_review"], under_review: ["approved", "rejected"], approved: ["disbursed"], rejected: [], disbursed: [],
};

export function ResourceFilters({ locale, onSubmit, disabled = false, initial = {} }: {
  locale: Locale; onSubmit?: React.FormEventHandler<HTMLFormElement>; disabled?: boolean;
  initial?: Record<string, string>;
}) {
  const t = words[locale];
  return <form onSubmit={onSubmit} method="get" className="program-panel" aria-label={t.filters}>
    <div className="program-grid"><label>{t.search}<input name="q" type="search" maxLength={120} defaultValue={initial.q ?? ""} /></label>
      <label>{t.kind}<select name="kind" defaultValue={initial.kind ?? ""}><option value="">{t.all}</option>
        {(["scheme", "funding", "opportunity"] as const).map((kind) => <option key={kind} value={kind}>{t[kind]}</option>)}
      </select></label>
      <label>{t.sector}<input name="sector" maxLength={120} defaultValue={initial.sector ?? ""} /></label>
      <label>{t.geography}<input name="geography" maxLength={120} defaultValue={initial.geography ?? ""} /></label>
      <label>{t.tag}<input name="tag" maxLength={200} defaultValue={initial.tag ?? ""} /></label>
      <label>{t.availability}<select name="availability" defaultValue={initial.availability ?? "active"}>
        {(["active", "open", "upcoming", "closed", "all"] as const).map((value) => <option key={value} value={value}>{t[value]}</option>)}
      </select></label></div>
    <button type="submit" disabled={disabled}>{t.filter}</button>
  </form>;
}

export function ResourceCard({ item, locale, children }: { item: Resource; locale: Locale; children?: React.ReactNode }) {
  const t = words[locale];
  let official: string | null = null;
  try { const url = new URL(item.official_url); if (["https:", "http:"].includes(url.protocol) && !url.username && !url.password) official = url.href; } catch {}
  return <article className="program-panel" aria-label={item.title} style={{ overflowWrap: "anywhere" }}>
    <p>{t[item.kind]} · <strong>{t[item.availability]}</strong></p><h2>{item.title}</h2>
    <p>{t.provider}: {item.provider} · {t.type}: {item.type}</p>
    <p>{t.sector}: {item.sector} · {t.geography}: {item.geography}</p>
    <p>{t.opens}: {item.opens_on ?? t.unspecified} · {t.closes}: {item.closes_on ?? t.unspecified}</p>
    <p>{t.verified}: <time dateTime={item.last_verified_at}>{item.last_verified_at}</time></p>
    {official && <p><a href={official} target="_blank" rel="noopener noreferrer">{t.source}</a></p>}
    <p style={{ whiteSpace: "pre-wrap" }}>{item.description}</p>
    <details><summary>{t.eligibility}</summary>
      <p style={{ whiteSpace: "pre-wrap" }}>{item.eligibility}</p>
      {item.benefits && <><h3>{t.benefits}</h3><p style={{ whiteSpace: "pre-wrap" }}>{item.benefits}</p></>}
      <h3>{t.process}</h3><p style={{ whiteSpace: "pre-wrap" }}>{item.application_process}</p>
      <h3>{t.documents}</h3>{item.documents?.length ? <ul>{item.documents.map((document) => <li key={document}>{document}</li>)}</ul> : <p>{t.unspecified}</p>}
      {item.contact && <p>{t.contact}: {item.contact}</p>}
      {(item.funding_amount_min != null || item.funding_amount_max != null) && <p>{t.amount}: {item.currency} {item.funding_amount_min ?? "—"} – {item.funding_amount_max ?? "—"}</p>}
      {!!item.tags?.length && <p>{item.tags.join(", ")}</p>}
    </details>{children}
  </article>;
}

export function FundingHistory({ item, locale }: { item: FundingCase; locale: Locale }) {
  const t = words[locale];
  return <><details><summary>{t.history}</summary><ol>{item.history.map((event) => <li key={event.id}>
    <strong>{statusLabel(event.status, locale)}</strong> · <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString(locale)}</time>
    <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{event.reason}</p>
  </li>)}</ol></details><details><summary>{t.original}</summary><ResourceCard item={item.source} locale={locale} /></details></>;
}
