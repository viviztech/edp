import "server-only";
import { isEnquiryId, safePrivacyUrl } from "./enquiry-security";
import type { EnquiryPolicy } from "./enquiry-content";

export function publicEnquirySettings() {
  const organization = process.env.PUBLIC_ORGANIZATION_ID;
  const api = process.env.API_INTERNAL_URL;
  if (!organization || !isEnquiryId(organization) || !api) return null;
  return { organization, api: api.replace(/\/$/, "") };
}

export async function publicEnquiryPolicy(locale: "en" | "ta"): Promise<EnquiryPolicy | null> {
  const config = publicEnquirySettings();
  if (!config) return null;
  try {
    const response = await fetch(`${config.api}/api/v1/public/organizations/${config.organization}/enquiry-policy?locale=${locale}`, {
      cache: "no-store", signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) return null;
    const data = await response.json() as EnquiryPolicy;
    if (data.enabled !== true || typeof data.consent_version !== "string" || !data.consent_version.trim() || data.consent_version.length > 40
      || typeof data.consent_text !== "string" || !data.consent_text.trim() || data.consent_text.length > 2000
      || typeof data.privacy_notice_url !== "string" || !safePrivacyUrl(data.privacy_notice_url)) return null;
    return data;
  } catch { return null; }
}
