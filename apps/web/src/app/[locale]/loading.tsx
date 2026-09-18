"use client";
import { useParams } from "next/navigation";
import { isLocale, messages } from "../../lib/messages";
export default function Loading() {
  const params = useParams<{locale: string}>();
  const locale = isLocale(params.locale) ? params.locale : "en";
  return <main id="main" aria-busy="true"><p role="status">{messages[locale].loading}</p></main>;
}
