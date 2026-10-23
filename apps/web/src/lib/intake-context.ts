import type { Locale } from "./messages";

export type IntakeContext = { organization?: string; cycle?: string };
export type IntakeSearch = Record<string, string | string[] | undefined>;

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function intakeId(value: unknown): string | undefined {
  return typeof value === "string" && uuid.test(value) ? value.toLowerCase() : undefined;
}

// Only these two identifiers cross the sign-in boundary. URLs and returnTo are
// deliberately not accepted; destinations are always known application routes.
export function readIntakeContext(input: IntakeSearch, fallbackOrganization?: string): IntakeContext {
  const organization = intakeId(input.organization ?? fallbackOrganization);
  if (!organization) return {};
  const cycle = intakeId(input.cycle);
  return { organization, ...(cycle ? { cycle } : {}) };
}

function intakeHref(locale: Locale, route: "account" | "applications", context: IntakeContext): string {
  const safe = readIntakeContext(context);
  const query = new URLSearchParams();
  if (safe.organization) query.set("organization", safe.organization);
  if (safe.cycle) query.set("cycle", safe.cycle);
  return `/${locale}/${route}${query.size ? `?${query}` : ""}`;
}

export function applicationHref(locale: Locale, context: IntakeContext = {}): string {
  return intakeHref(locale, "applications", context);
}

export function accountHref(locale: Locale, context: IntakeContext = {}): string {
  return intakeHref(locale, "account", context);
}
