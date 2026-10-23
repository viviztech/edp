import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { authMessages } from "../../../lib/auth-messages";
import Account from "./view";

const organization = "11111111-1111-4111-8111-111111111111";
const cycle = "22222222-2222-4222-8222-222222222222";
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function api(grants: { organization_id: string; organization_name: string; permissions: string[] }[] = [], initiallyAuthenticated = true) {
  let authenticated = initiallyAuthenticated;
  const writes: { path: string; body: Record<string, string> }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/session/me") return authenticated ? json({ id: "person", display_name: "Synthetic applicant", grants }) : json({}, 401);
    if (path === "/api/session/sessions") return json([{ id: "device", device_name: "Web browser", current: true }]);
    if (path === "/api/session/csrf") return json({ csrf_token: "test-csrf" });
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("x-csrf-token")).toBe("test-csrf");
    writes.push({ path, body: JSON.parse(String(init?.body)) });
    if (path === "/api/session/login") authenticated = true;
    return json({});
  });
  vi.stubGlobal("fetch", fetcher);
  return { writes, fetcher };
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const click = async (name: string) => { await act(async () => { fireEvent.click(screen.getByRole("button", { name })); }); };

describe("account entry and destinations", () => {
  it("offers an application destination without any organization grants", async () => {
    api();
    await act(async () => { render(<Account locale="en" text={authMessages.en} intake={{ organization, cycle }} />); });
    expect(screen.getByRole("link", { name: "Continue application" }).getAttribute("href")).toBe(`/en/applications?organization=${organization}&cycle=${cycle}`);
    expect(screen.queryByRole("link", { name: "Staff workspace" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Active devices" })).toBeTruthy();
  });

  it("keeps the chosen intake through registration, verification and login while retaining account session controls", async () => {
    const mock = api([], false);
    await act(async () => { render(<Account locale="ta" text={authMessages.ta} intake={{ organization, cycle }} />); });
    await click(authMessages.ta.register);
    fireEvent.change(screen.getByLabelText(authMessages.ta.name), { target: { value: "Synthetic applicant" } });
    fireEvent.change(screen.getByLabelText(authMessages.ta.email), { target: { value: "applicant@example.test" } });
    fireEvent.change(screen.getByLabelText(authMessages.ta.password), { target: { value: "Synthetic-passphrase-1" } });
    await act(async () => { fireEvent.submit(screen.getByLabelText(authMessages.ta.name).closest("form")!); });
    expect(mock.writes[0].body.locale).toBe("ta");
    await click(authMessages.ta.verify);
    fireEvent.change(screen.getByLabelText(authMessages.ta.token), { target: { value: "synthetic-token-12345678901234567890" } });
    await act(async () => { fireEvent.submit(screen.getByLabelText(authMessages.ta.token).closest("form")!); });
    await click(authMessages.ta.login);
    fireEvent.change(screen.getByLabelText(authMessages.ta.email), { target: { value: "applicant@example.test" } });
    fireEvent.change(screen.getByLabelText(authMessages.ta.password), { target: { value: "Synthetic-passphrase-1" } });
    await act(async () => { fireEvent.submit(screen.getByLabelText(authMessages.ta.email).closest("form")!); });
    expect(mock.writes.map(write => write.path)).toEqual(["/api/session/register", "/api/session/verify", "/api/session/login"]);
    expect(screen.getByRole("link", { name: authMessages.ta.application }).getAttribute("href")).toBe(`/ta/applications?organization=${organization}&cycle=${cycle}`);
    expect(screen.getByRole("heading", { name: authMessages.ta.sessions })).toBeTruthy();
    expect(screen.getByRole("button", { name: authMessages.ta.logout })).toBeTruthy();
  });

  it("routes participants to their portal and only offers staff access for actual staff capabilities", async () => {
    api([
      { organization_id: organization, organization_name: "Participant organization", permissions: ["system.access", "participant.self", "lms.learn"] },
      { organization_id: cycle, organization_name: "Staff organization", permissions: ["system.access", "enquiry.view"] },
    ]);
    await act(async () => { render(<Account locale="en" text={authMessages.en} />); });
    expect(screen.getByRole("link", { name: "Participant portal" }).getAttribute("href")).toBe(`/en/participant?organization=${organization}`);
    expect(screen.getByRole("link", { name: "My learning" }).getAttribute("href")).toBe(`/en/learning?organization=${organization}`);
    expect(screen.getAllByRole("link", { name: "Staff workspace" })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Staff workspace" }).getAttribute("href")).toBe(`/en/admin?organization=${cycle}`);
    expect(screen.getByRole("link", { name: "Continue application" }).getAttribute("href")).toBe("/en/applications");
  });
});
