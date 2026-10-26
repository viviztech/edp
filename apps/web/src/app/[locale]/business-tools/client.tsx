"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { toolsCopy, type ToolsLocale } from "../../../lib/business-tools-copy";

const guardedClicks = new WeakSet<MouseEvent>();

type Schemas = components["schemas"];
export type CardFields = Omit<Schemas["CardView"], "id" | "version" | "published" | "share_id" | "updated_at">;
export type Card = CardFields & Pick<Schemas["CardView"], "version" | "published" | "share_id">;
export type ItemFields = Omit<Schemas["CatalogueItemView"], "id" | "version" | "updated_at" | "price"> & { price: string | null };
export type Item = ItemFields & { id: string; version: number };
export type Catalogue = { settings: { version: number; published: boolean; share_id: string } | null; items: Item[]; limit: number; offset: number };
export type Line = Required<Omit<Schemas["QuotationLineView"], "line_total">>;
export type QuoteFields = Pick<Schemas["QuotationView"], "customer_name" | "customer_address" | "issued_on" | "valid_until" | "currency" | "notes" | "discount"> & { lines: Line[] };
export type Quote = QuoteFields & { id: string; version: number; status: "draft" | "issued"; subtotal: string; total: string; issued_at: string | null; lines: (Line & { line_total: string })[] };
export type ContactFields = Omit<Schemas["CustomerContactView"], "id" | "version" | "updated_at">;
export type Contact = ContactFields & { id: string; version: number };
export type TaskFields = Pick<Schemas["CustomerTaskView"], "title" | "notes" | "due_at" | "status">;
export type Task = TaskFields & { id: string; contact_id: string; version: number };
export type History = Schemas["ToolHistoryView"];
export type Page<T> = { items: T[]; limit: number; offset: number };
export type Text = typeof toolsCopy[ToolsLocale];

export async function read<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error("read_failed");
  return response.json() as Promise<T>;
}

type Pending = { url: string; body: string; accept: (value: unknown) => void };
export function useCommand(t: Text) {
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [stale, setStale] = useState(false);
  const [message, setMessage] = useState("");
  const lock = useRef(false);
  async function send(command: Pending) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setMessage("");
    try {
      const { csrf_token } = await read<{ csrf_token: string }>("/api/session/csrf");
      const response = await fetch(command.url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token }, body: command.body });
      if (response.status >= 400 && response.status < 500) {
        const error = await response.json().catch(() => ({})) as { error?: { code?: string } };
        const code = error.error?.code;
        setPending(null); setStale(response.status === 409);
        setMessage(code === "catalogue_conflict" ? t.catalogueConflict : code === "contact_archived" ? t.contactArchived
          : code === "task_settled" ? t.taskSettled : code === "discount_exceeds_subtotal" ? t.discountError : response.status === 409 ? t.stale : t.error);
        return;
      }
      if (!response.ok) throw new Error("unknown_result");
      const result: unknown = await response.json();
      command.accept(result); setPending(null); setStale(false); setMessage(t.saved);
    } catch { setPending(command); setMessage(t.uncertain); }
    finally { lock.current = false; setBusy(false); }
  }
  function run<T>(url: string, fields: object, accept: (value: T) => void) {
    if (busy || pending || stale || lock.current) return;
    const command: Pending = { url, body: JSON.stringify({ ...fields, request_id: crypto.randomUUID() }), accept: value => accept(value as T) };
    setPending(command); void send(command);
  }
  return { busy, pending: !!pending, stale, blocked: busy || !!pending || stale, message, run,
    retry: () => { if (pending) void send(pending); }, reconcile: () => { setStale(false); setMessage(""); } };
}
export type Command = ReturnType<typeof useCommand>;

export function CommandState({ command, t }: { command: Command; t: Text }) {
  return <div aria-live="polite"><p role="status">{command.busy ? t.loading : command.message}</p>
    {command.pending && !command.busy && <button type="button" onClick={command.retry}>{t.retry}</button>}</div>;
}

export function useDirtyGuard(dirty: boolean) {
  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    // Preserve unsaved and uncertain commands when a normal navigation link is used.
    const click = (event: MouseEvent) => {
      if (event.defaultPrevented || guardedClicks.has(event)) return;
      const target = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (target && !target.hasAttribute("download") && target.getAttribute("target") !== "_blank") {
        guardedClicks.add(event);
        if (!window.confirm(document.documentElement.lang === "ta" ? "சேமிக்காத திருத்தங்கள் உள்ளன. வெளியேறவா?" : "You have unsaved changes. Leave this page?")) event.preventDefault();
      }
    };
    if (dirty) { window.addEventListener("beforeunload", before); document.addEventListener("click", click, true); }
    return () => { window.removeEventListener("beforeunload", before); document.removeEventListener("click", click, true); };
  }, [dirty]);
}

export function Pager({ offset, count, busy, onChange, t }: { offset: number; count: number; busy: boolean; onChange: (offset: number) => void; t: Text }) {
  return <div className="actions"><button type="button" disabled={busy || offset === 0} onClick={() => onChange(Math.max(0, offset - 25))}>{t.previous}</button>
    <button type="button" disabled={busy || count < 25} onClick={() => onChange(offset + 25)}>{t.next}</button></div>;
}

export function localInput(iso: string): string {
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
