"use client";
import { useParams } from "next/navigation";
import { isLocale, messages } from "../../lib/messages";
export default function ErrorPage({ reset }: { reset: () => void }) {
  const params = useParams<{locale: string}>();
  const text = messages[isLocale(params.locale) ? params.locale : "en"];
  return <main id="main"><p role="alert">{text.error}</p><button onClick={reset}>{text.retry}</button></main>;
}
