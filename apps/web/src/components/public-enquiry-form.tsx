"use client";
import { useState } from "react";
import { enquiryWords, type EnquiryPolicy } from "../lib/enquiry-content";
import "./enquiries.css";

const empty = { name: "", email: "", phone: "", message: "", website: "" };
export function PublicEnquiryForm({ locale, policy }: { locale: "en" | "ta"; policy: EnquiryPolicy | null }) {
  const t = enquiryWords[locale];
  const [form, setForm] = useState(empty), [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(""), [reference, setReference] = useState("");
  const [policyStale, setPolicyStale] = useState(false);
  if (!policy?.enabled) return <section className="enquiry-public" aria-labelledby="enquiry-title"><h2 id="enquiry-title">{t.title}</h2><p>{t.unavailable}</p></section>;
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!consent || busy || policyStale || !policy) return;
    setBusy(true); setMessage("");
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error();
      const token = (await csrf.json()).csrf_token;
      const response = await fetch("/api/enquiries/public", {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json", "x-csrf-token": token },
        body: JSON.stringify({ ...form, locale, consent, consent_version: policy.consent_version }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        if (data.error?.code === "consent_required") { setPolicyStale(true); setConsent(false); }
        setMessage(response.status === 429 ? t.limited : data.error?.code === "consent_required" ? t.changed : response.status === 400 || response.status === 422 ? t.invalid : t.error);
        return;
      }
      const data = await response.json();
      if (data.accepted !== true || typeof data.reference !== "string") throw new Error();
      setReference(data.reference); setForm(empty); setConsent(false);
    } catch { setMessage(t.error); }
    finally { setBusy(false); }
  }
  return <section className="enquiry-public" aria-labelledby="enquiry-title" aria-busy={busy}>
    <h2 id="enquiry-title">{t.title}</h2>
    {reference ? <div role="status"><p>{t.accepted}</p><p>{t.reference}: <span className="enquiry-reference">{reference}</span></p></div> : <>
      <form aria-label={t.title} className="account-form enquiry-form" onSubmit={submit}>
        <fieldset disabled={busy}>
          <label>{t.name}<input name="name" autoComplete="name" required maxLength={120} value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} /></label>
          <label>{t.email}<input name="email" type="email" autoComplete="email" required maxLength={320} value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} /></label>
          <label>{t.phone}<input name="phone" type="tel" autoComplete="tel" maxLength={32} value={form.phone} onChange={event => setForm({ ...form, phone: event.target.value })} /></label>
          <label>{t.message}<textarea name="message" required maxLength={5000} rows={6} value={form.message} onChange={event => setForm({ ...form, message: event.target.value })} /></label>
          <div className="enquiry-trap" aria-hidden="true"><label>{t.website}<input name="website" tabIndex={-1} autoComplete="off" value={form.website} onChange={event => setForm({ ...form, website: event.target.value })} /></label></div>
          <a href={policy.privacy_notice_url} target="_blank" rel="noopener noreferrer">{t.privacy}</a>
          <label className="enquiry-consent"><input type="checkbox" required checked={consent} onChange={event => setConsent(event.target.checked)} /><span>{policy.consent_text}</span></label>
          <button type="submit" disabled={busy || !consent || policyStale}>{busy ? t.sending : t.send}</button>
        </fieldset>
      </form>
      {message && <p role="alert">{message}</p>}
      {policyStale && <button type="button" onClick={() => window.location.reload()}>{t.reload}</button>}
    </>}
  </section>;
}
