"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { authMessages } from "../lib/auth-messages";
import type { Locale } from "../lib/messages";

export const challengeMessages = {
  en: {
    introduction: "Enter the code from your account message. This action applies to that code, even if another account is signed in.",
    failed: "The code could not be confirmed. Check the code and try again, or request a new account message.",
    uncertain: "The result could not be confirmed. Check your account before submitting again.",
    limited: "Too many attempts. Please wait before trying again.",
  },
  ta: {
    introduction: "உங்கள் கணக்குச் செய்தியில் உள்ள குறியீட்டை உள்ளிடவும். வேறு கணக்கில் உள்நுழைந்திருந்தாலும், இந்தக் குறியீட்டிற்கான செயல் நடைபெறும்.",
    failed: "குறியீட்டை உறுதிப்படுத்த முடியவில்லை. குறியீட்டைச் சரிபார்த்து மீண்டும் முயலவும் அல்லது புதிய கணக்குச் செய்தியைக் கோரவும்.",
    uncertain: "முடிவை உறுதிப்படுத்த முடியவில்லை. மீண்டும் சமர்ப்பிக்கும் முன் உங்கள் கணக்கைச் சரிபார்க்கவும்.",
    limited: "அதிக முயற்சிகள். மீண்டும் முயலும் முன் காத்திருக்கவும்.",
  },
} as const;

export default function AccountChallenge({ locale, purpose }: { locale: Locale; purpose: "verify" | "reset" }) {
  const t = authMessages[locale], copy = challengeMessages[locale];
  const [token, setToken] = useState(""), [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false), [done, setDone] = useState(false), [message, setMessage] = useState("");
  const lock = useRef(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current || done) return;
    lock.current = true; setBusy(true); setMessage("");
    let posted = false;
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error();
      const value: unknown = (await csrf.json()).csrf_token;
      if (typeof value !== "string" || !value || value.length > 128) throw new Error();
      posted = true;
      const response = await fetch(`/api/session/${purpose}`, {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json", "x-csrf-token": value },
        body: JSON.stringify({ token, ...(purpose === "reset" ? { password } : {}) }),
      });
      if (!response.ok) {
        setMessage(response.status === 429 ? copy.limited : response.status >= 500 ? copy.uncertain : copy.failed);
        return;
      }
      setToken(""); setPassword(""); setDone(true); setMessage(t.completed);
    } catch { setMessage(posted ? copy.uncertain : t.unavailable); }
    finally { lock.current = false; setBusy(false); }
  }
  return <section aria-busy={busy}>
    <h1>{t[purpose]}</h1><p>{copy.introduction}</p>
    <p role="status">{message}</p>
    {!done && <form className="account-form" onSubmit={submit}>
      <label>{t.token}<input name="token" value={token} onChange={event => setToken(event.target.value)} autoComplete="one-time-code" autoCapitalize="none" spellCheck={false} required minLength={32} maxLength={256} disabled={busy} /></label>
      {purpose === "reset" && <div><label>{t.password}<input name="password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" required minLength={12} maxLength={128} disabled={busy} aria-describedby="challenge-password-help" /></label><small id="challenge-password-help">{t.passwordHelp}</small></div>}
      <button type="submit" disabled={busy}>{busy ? t.loading : t[purpose]}</button>
    </form>}
    <p><Link href={`/${locale}/account`}>{t.back}</Link></p>
  </section>;
}
