import { afterEach, describe, expect, it, vi } from "vitest";
import { publicLaunch, launchCopy } from "./public-launch";
import { siteUrl } from "./site-url";
afterEach(() => vi.unstubAllEnvs());
describe("public launch boundary", () => {
  it("separates the explicitly enabled demo from real registration", () => {
    vi.stubEnv("PUBLIC_SELF_SERVICE_ENABLED", "false");
    expect(publicLaunch().selfService).toBe(false);
    vi.stubEnv("PUBLIC_DEMO_ENABLED", "true");
    expect(publicLaunch().demo).toBe(true);
  });
  it("rejects invalid contact channels and preserves bilingual labels", () => {
    vi.stubEnv("PUBLIC_CONTACT_EMAIL", "not an email");
    vi.stubEnv("PUBLIC_CONTACT_PHONE", "javascript:alert(1)");
    vi.stubEnv("PUBLIC_CONTACT_WHATSAPP", "bad");
    expect(publicLaunch().email).toBe("");
    expect(publicLaunch().phone).toBe("");
    expect(publicLaunch().whatsapp).toBe("");
    expect(Object.keys(launchCopy.en).sort()).toEqual(
      Object.keys(launchCopy.ta).sort(),
    );
  });
  it("uses the runtime deployed origin when a separate SEO origin is absent", () => {
    vi.stubEnv("PUBLIC_SITE_URL", undefined);
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", undefined);
    vi.stubEnv("WEB_ORIGIN", "https://launch.example");
    expect(siteUrl().href).toBe("https://launch.example/");
  });
});
