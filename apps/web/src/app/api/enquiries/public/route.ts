import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { enquiryBody, EnquiryTransportError } from "../../../../lib/enquiry-transport";
import { isEnquiryId } from "../../../../lib/enquiry-security";
import { publicEnquiryPolicy, publicEnquirySettings } from "../../../../lib/public-enquiries";
import { csrfName, settings } from "../../../../lib/server-api";

const headers = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "X-Content-Type-Options": "nosniff" };
const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, { status, headers });

export async function POST(request: NextRequest) {
  try {
    if (request.nextUrl.search) return fail("invalid_request", 400);
    const config = settings(); const jar = await cookies();
    if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
    const body = await enquiryBody(request);
    const allowed = ["name", "email", "phone", "message", "consent_version", "consent", "locale", "website"];
    if (Object.keys(body).some(key => !allowed.includes(key)) || body.consent !== true || (body.locale !== "en" && body.locale !== "ta")
      || (body.website !== undefined && body.website !== "")) return fail("invalid_request", 400);
    const limits = { name: [1, 120], email: [3, 320], phone: [0, 32], message: [1, 5000], consent_version: [1, 40] };
    const payload: Record<string, string> = {};
    for (const [key, [min, max]] of Object.entries(limits)) {
      const value = body[key] ?? (key === "phone" ? "" : undefined);
      if (typeof value !== "string" || [...value.trim()].length < min || [...value.trim()].length > max) return fail("invalid_request", 400);
      payload[key] = value.trim();
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payload.email)) return fail("invalid_request", 400);
    const publicConfig = publicEnquirySettings(); const policy = await publicEnquiryPolicy(body.locale);
    if (!publicConfig || !policy) return fail("enquiries_unavailable", 503);
    if (payload.consent_version !== policy.consent_version) return fail("consent_required", 422);
    const upstream = await fetch(`${config.api}/api/v1/public/organizations/${publicConfig.organization}/enquiries`, {
      method: "POST", body: JSON.stringify(payload), cache: "no-store", signal: AbortSignal.timeout(10000),
      headers: { "Content-Type": "application/json", "X-BFF-Key": config.key },
    });
    if (!upstream.ok) {
      if (upstream.status === 429) return NextResponse.json({ error: { code: "rate_limited" } }, { status: 429, headers: { ...headers, "Retry-After": "900" } });
      if (upstream.status === 422) {
        const data = await upstream.json().catch(() => ({}));
        return fail(data.error?.code === "consent_required" ? "consent_required" : "invalid_request", 422);
      }
      return fail("enquiries_unavailable", 503);
    }
    const receipt = await upstream.json();
    if (receipt.accepted !== true || typeof receipt.reference !== "string" || !isEnquiryId(receipt.reference)) return fail("invalid_response", 502);
    return NextResponse.json({ accepted: true, reference: receipt.reference }, { status: 202, headers });
  } catch (error) {
    return error instanceof EnquiryTransportError ? fail(error.code, error.status) : fail("service_unavailable", 503);
  }
}
